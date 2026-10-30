"""Solution generator (S7): the proposed approach, with coverage computed by code.

The model sees the problem statement (S6), the requirements, ambiguities and gaps (S5),
never the RFP text, and returns a ``SolutionDraft``: a summary, components that cite the
requirement IDs they satisfy, and assumptions. Three things are owned by code:

- **Citations.** The schema of each call is a per-call subclass of ``SolutionDraft``
  whose validator rejects an empty component list, a component that cites no
  requirement, a requirement ID outside the list and a chunk ID outside the evidence, so
  ``structured_call`` feeds the exact problem back and retries (the S6 pattern, D28).
- **Coverage.** ``compute_coverage`` counts the mandatory requirements (type
  ``submission`` excluded) cited by at least one component. The model never writes it.
- **The revision loop.** A small LangGraph: ``generate`` → ``check`` → (``revise`` →
  ``generate``)* while any in-scope mandatory requirement is uncovered and the round cap
  (``Settings.solution_max_iterations``) is not reached. The revision continues the same
  conversation, so the model sees its own answer and the list of what it missed. The
  draft with the fewest uncovered requirements wins, so a worse revision cannot regress
  the output. What is still uncovered is listed in ``Coverage`` for the risk assessor.

Component IDs ``C01…`` are assigned by code in reply order.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from pydantic import create_model, model_validator

from rfp_agent.config import Settings, get_settings
from rfp_agent.llm import Prompt, get_chat_model, load_prompt, structured_call
from rfp_agent.observability import current_recorder
from rfp_agent.schemas import (
    Ambiguity,
    Claim,
    ComponentDraft,
    Coverage,
    Gap,
    ProblemStatement,
    Requirement,
    RequirementsOutput,
    RequirementType,
    Solution,
    SolutionComponent,
    SolutionDraft,
    StrictModel,
    Strictness,
    validate_ids_exist,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.runnables import RunnableConfig

    from rfp_agent.observability import RunRecorder

logger = logging.getLogger(__name__)

GENERATE_NODE = "solution_generate"
REVISE_NODE = "solution_revise"
PROMPT = "solution"

COVERAGE_EXCLUDED_TYPES: frozenset[RequirementType] = frozenset({RequirementType.SUBMISSION})
STRICTNESS_ORDER = (Strictness.MANDATORY, Strictness.DESIRED, Strictness.OPTIONAL)
STRICTNESS_HEADINGS = {
    Strictness.MANDATORY: "Mandatory",
    Strictness.DESIRED: "Desired",
    Strictness.OPTIONAL: "Optional",
}
SUBMISSION_HEADING = "Submission requirements (context, do not address)"
NONE = "(none)"


class CoverageRound(StrictModel):
    """Coverage after one round, for the debug CLI and the roadmap table."""

    iteration: int
    coverage: Coverage


class SolutionResult(StrictModel):
    solution: Solution
    rounds: list[CoverageRound] = []

    @property
    def iterations(self) -> int:
        return len(self.rounds)


# --------------------------------------------------------------------------------------
# Coverage (pure)
# --------------------------------------------------------------------------------------


def in_scope(requirements: Iterable[Requirement]) -> list[Requirement]:
    """The requirements coverage is measured on: mandatory, not a submission item."""
    return [
        r
        for r in requirements
        if r.strictness is Strictness.MANDATORY and r.type not in COVERAGE_EXCLUDED_TYPES
    ]


def compute_coverage(
    components: Iterable[ComponentDraft | SolutionComponent], requirements: Iterable[Requirement]
) -> Coverage:
    """Mandatory coverage from the components' ``requirement_ids``; uncovered IDs keep
    the order of the requirement list."""
    scope = in_scope(requirements)
    cited = {rid for c in components for rid in c.requirement_ids}
    uncovered = [r.id for r in scope if r.id not in cited]
    return Coverage(
        mandatory_total=len(scope),
        mandatory_covered=len(scope) - len(uncovered),
        uncovered_requirement_ids=uncovered,
    )


# --------------------------------------------------------------------------------------
# Evidence formatting
# --------------------------------------------------------------------------------------


def _ids(ids: Sequence[str]) -> str:
    return ", ".join(ids)


def claim_line(claim: Claim) -> str:
    """``- text [S1.2] (inference)``; shared with the risk assessor (S8)."""
    mark = " (inference)" if claim.kind == "inference" else ""
    return f"- {claim.text.strip()} [{_ids(claim.chunk_ids)}]{mark}"


def format_problem(problem: ProblemStatement) -> str:
    parts: list[str] = []
    for name in ("client_situation", "goal", "success_criteria", "constraints"):
        claims = getattr(problem, name)
        lines = "\n".join(claim_line(c) for c in claims) or NONE
        parts.append(f"### {name}\n{lines}")
    return "\n\n".join(parts)


def _requirement_line(r: Requirement) -> str:
    return f"{r.id} [{r.strictness.value}, {r.type.value}] {r.text.strip()} ({_ids(r.chunk_ids)})"


def format_requirements(
    requirements: Iterable[Requirement], *, submission_heading: str = SUBMISSION_HEADING
) -> str:
    """Mandatory, desired and optional blocks in list order, then the submission items
    (whatever their strictness) under a heading that tells the model not to cite them.
    The risk assessor (S8) passes its own ``submission_heading``."""
    reqs = list(requirements)
    blocks: list[str] = []
    for strictness in STRICTNESS_ORDER:
        lines = [
            _requirement_line(r)
            for r in reqs
            if r.strictness is strictness and r.type not in COVERAGE_EXCLUDED_TYPES
        ]
        blocks.append(f"### {STRICTNESS_HEADINGS[strictness]}\n" + ("\n".join(lines) or NONE))
    submission = [_requirement_line(r) for r in reqs if r.type in COVERAGE_EXCLUDED_TYPES]
    blocks.append(f"### {submission_heading}\n" + ("\n".join(submission) or NONE))
    return "\n\n".join(blocks)


def format_ambiguities(ambiguities: Iterable[Ambiguity]) -> str:
    lines = [
        f"{a.id} ({_ids(a.chunk_ids)}; {_ids(a.requirement_ids) or 'no requirement'}) "
        f"{a.description.strip()}"
        for a in ambiguities
    ]
    return "\n".join(lines) or NONE


def format_gaps(gaps: Iterable[Gap]) -> str:
    lines = [
        f"{g.id} [{g.referenced_document or '-'}] {g.description.strip()}"
        + (f" ({_ids(g.chunk_ids)})" if g.chunk_ids else "")
        for g in gaps
    ]
    return "\n".join(lines) or NONE


def allowed_chunk_ids(requirements: RequirementsOutput, problem: ProblemStatement) -> list[str]:
    """Every chunk ID the model can see a label for, in first-seen order."""
    seen: dict[str, None] = {}
    sources: list[Sequence[str]] = [c.chunk_ids for c in problem.claims()]
    sources += [r.chunk_ids for r in requirements.requirements]
    sources += [a.chunk_ids for a in requirements.ambiguities]
    sources += [g.chunk_ids for g in requirements.gaps]
    for ids in sources:
        for i in ids:
            seen.setdefault(i, None)
    return list(seen)


def render_prompt(
    requirements: RequirementsOutput,
    problem: ProblemStatement,
    *,
    title: str,
    prompt: Prompt | None = None,
) -> str:
    prompt = prompt or load_prompt(PROMPT)
    return prompt.render(
        title=title,
        problem=format_problem(problem),
        requirements=format_requirements(requirements.requirements),
        ambiguities=format_ambiguities(requirements.ambiguities),
        gaps=format_gaps(requirements.gaps),
    )


# --------------------------------------------------------------------------------------
# Per-call schema: citations checked inside the retry loop
# --------------------------------------------------------------------------------------


def solution_schema(
    requirement_ids: Iterable[str], chunk_ids: Iterable[str]
) -> type[SolutionDraft]:
    """A ``SolutionDraft`` subclass for one call whose validator rejects an empty
    component list, a component citing no requirement, and any requirement or chunk ID
    outside the inputs. Named ``SolutionDraft`` so the tool name is unchanged."""
    allowed_reqs = list(requirement_ids)
    allowed_chunks = list(chunk_ids)

    def check(self: SolutionDraft) -> SolutionDraft:
        problems: list[str] = []
        if not self.components:
            problems.append("components is empty; return at least four components")
        for i, c in enumerate(self.components):
            if not c.requirement_ids:
                problems.append(
                    f"components[{i}] ({c.title!r}) cites no requirement; every component "
                    "must list the IDs of the requirements it satisfies"
                )
            unknown = validate_ids_exist(c.requirement_ids, allowed_reqs)
            if unknown:
                problems.append(
                    f"components[{i}].requirement_ids cites IDs that are not in the "
                    f"requirement list: {unknown}; copy IDs exactly from the list"
                )
            unknown = validate_ids_exist(
                (k for cl in c.claims for k in cl.chunk_ids), allowed_chunks
            )
            if unknown:
                problems.append(
                    f"components[{i}].claims cites chunk IDs that are not shown in the "
                    f"inputs: {unknown}; cite only the bracketed chunk IDs"
                )
        unknown = validate_ids_exist(
            (k for cl in self.assumptions for k in cl.chunk_ids), allowed_chunks
        )
        if unknown:
            problems.append(
                f"assumptions cites chunk IDs that are not shown in the inputs: {unknown}; "
                "cite only the bracketed chunk IDs"
            )
        if problems:
            raise ValueError("; ".join(problems))
        return self

    return create_model(
        "SolutionDraft",
        __base__=SolutionDraft,
        __module__=__name__,
        __validators__={"check_citations": model_validator(mode="after")(check)},
    )


# --------------------------------------------------------------------------------------
# The revision loop
# --------------------------------------------------------------------------------------


def coverage_feedback(uncovered: Sequence[Requirement]) -> str:
    lines = "\n".join(f"- {r.id}: {r.text.strip()}" for r in uncovered)
    return (
        "Code computed the coverage of the mandatory requirements from your "
        f"requirement_ids. These {len(uncovered)} mandatory requirements are addressed by "
        f"no component:\n{lines}\n"
        "Extend the components that meet them (add the IDs and, where the description "
        "does not show how the requirement is met, say how) or add a component. Return "
        "the full solution (summary, every component, assumptions), not only the changes."
    )


class LoopState(TypedDict, total=False):
    messages: list[BaseMessage]
    iteration: int
    draft: SolutionDraft
    coverage: Coverage
    best: SolutionDraft
    best_coverage: Coverage
    rounds: list[CoverageRound]


Route = Literal["revise", "__end__"]


def build_graph(
    *,
    model: BaseChatModel,
    schema: type[SolutionDraft],
    requirements: Sequence[Requirement],
    max_iterations: int,
    settings: Settings,
    recorder: RunRecorder | None,
):
    """Compile the generate → check → revise loop. Runtime objects are bound here, so the
    state holds only messages, drafts and coverage."""
    by_id = {r.id: r for r in requirements}

    def generate(state: LoopState, config: RunnableConfig) -> LoopState:
        iteration = state.get("iteration", 0)
        node = GENERATE_NODE if iteration == 0 else REVISE_NODE
        result = structured_call(
            model,
            schema,
            state["messages"],
            node=node,
            settings=settings,
            recorder=recorder,
            config=config,
        )
        draft = result.value
        return {
            "draft": draft,
            "iteration": iteration + 1,
            "messages": [*state["messages"], AIMessage(content=draft.model_dump_json())],
        }

    def check(state: LoopState) -> LoopState:
        draft = state["draft"]
        coverage = compute_coverage(draft.components, requirements)
        update: LoopState = {
            "coverage": coverage,
            "rounds": [
                *state.get("rounds", []),
                CoverageRound(iteration=state["iteration"], coverage=coverage),
            ],
        }
        best = state.get("best_coverage")
        if best is None or len(coverage.uncovered_requirement_ids) <= len(
            best.uncovered_requirement_ids
        ):
            update["best"] = draft
            update["best_coverage"] = coverage
        else:
            logger.info(
                "%s: round %d left %d uncovered, round kept had %d; revision discarded",
                REVISE_NODE,
                state["iteration"],
                len(coverage.uncovered_requirement_ids),
                len(best.uncovered_requirement_ids),
            )
        return update

    def route(state: LoopState) -> Route:
        uncovered = state["coverage"].uncovered_requirement_ids
        if uncovered and state["iteration"] < max_iterations:
            return "revise"
        return END

    def revise(state: LoopState) -> LoopState:
        uncovered = [by_id[i] for i in state["coverage"].uncovered_requirement_ids]
        return {"messages": [*state["messages"], HumanMessage(coverage_feedback(uncovered))]}

    graph = StateGraph(LoopState)
    graph.add_node("generate", generate)
    graph.add_node("check", check)
    graph.add_node("revise", revise)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "check")
    graph.add_conditional_edges("check", route, {"revise": "revise", END: END})
    graph.add_edge("revise", "generate")
    return graph.compile()


# --------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------


def _cid(n: int) -> str:
    return f"C{n:02d}"


def to_solution(draft: SolutionDraft, coverage: Coverage) -> Solution:
    """Number the components ``C01…`` in reply order and attach the computed coverage."""
    components = [
        SolutionComponent(
            id=_cid(i),
            title=c.title.strip(),
            description=c.description.strip(),
            requirement_ids=list(dict.fromkeys(c.requirement_ids)),
            claims=c.claims,
        )
        for i, c in enumerate(draft.components, start=1)
    ]
    return Solution(
        summary=draft.summary.strip(),
        components=components,
        assumptions=draft.assumptions,
        coverage=coverage,
    )


def build_solution(
    requirements: RequirementsOutput,
    problem: ProblemStatement,
    *,
    title: str | None = None,
    model: BaseChatModel | None = None,
    settings: Settings | None = None,
    recorder: RunRecorder | None = None,
    config: RunnableConfig | None = None,
    max_iterations: int | None = None,
) -> SolutionResult:
    """Generate the solution and revise it while mandatory requirements are uncovered.

    ``max_iterations`` overrides ``Settings.solution_max_iterations`` (rounds, including
    the first). Raises ``StructuredOutputError`` when a round cannot be validated within
    the retry budget; nothing is dropped silently.
    """
    settings = settings or get_settings()
    recorder = recorder or current_recorder()
    if model is None:
        model = get_chat_model(settings=settings)
    if max_iterations is None:
        max_iterations = settings.solution_max_iterations
    title = title or "untitled RFP"

    text = render_prompt(requirements, problem, title=title)
    schema = solution_schema(
        requirements.requirement_ids(), allowed_chunk_ids(requirements, problem)
    )
    graph = build_graph(
        model=model,
        schema=schema,
        requirements=requirements.requirements,
        max_iterations=max(1, max_iterations),
        settings=settings,
        recorder=recorder,
    )
    final: LoopState = graph.invoke(
        {"messages": [HumanMessage(text)], "iteration": 0}, config=config
    )
    # Hand back the plain contract class, not the per-call subclass.
    best = SolutionDraft.model_validate(final["best"].model_dump())
    return SolutionResult(
        solution=to_solution(best, final["best_coverage"]), rounds=final["rounds"]
    )
