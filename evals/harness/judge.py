"""Judge plumbing: the model, the prompts, a cost recorder and a thread pool.

Every judge call goes through S1's ``structured_call`` (validate, feed the error back,
retry) and is recorded into this judge's own ``RunRecorder``, so the judge's cost is a
run log like any other. Per-call schema subclasses (``exact_ids``) make the judge return
exactly one verdict per item it was shown; a missing or invented ID is sent back as a
validation error, the same pattern the agents use (F4).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, create_model, model_validator

from evals.harness.schemas import JudgeCost
from rfp_agent.config import Settings, get_settings
from rfp_agent.llm import (
    Prompt,
    StructuredOutputError,
    load_prompt,
    model_spec_of,
    structured_call,
)
from rfp_agent.observability import RunRecorder, per_node_totals

logger = logging.getLogger(__name__)

# This checkout's prompts, not the installed package's (the editable install points at the
# main checkout when the harness runs in a worktree).
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
# Verdicts are classification-like; the default effort would spend far more thinking
# tokens across hundreds of batched calls for little gain (D35).
JUDGE_EFFORT = "medium"
JUDGE_MAX_TOKENS = 16000
JUDGE_TIMEOUT_S = 300.0


def build_judge_model(settings: Settings | None = None) -> BaseChatModel:
    """The configured judge (``Settings.judge_model``) with the harness's effort, cap and
    timeout. Raises ``MissingApiKeyError`` when the key is absent."""
    from rfp_agent.llm import get_judge_model

    settings = settings or get_settings()
    overrides: dict[str, Any] = {"max_tokens": JUDGE_MAX_TOKENS, "timeout": JUDGE_TIMEOUT_S}
    if settings.judge_model.startswith("anthropic:"):
        overrides["output_config"] = {"effort": JUDGE_EFFORT}
    return get_judge_model(settings, **overrides)


def exact_ids[T: BaseModel](
    base: type[T], list_field: str, id_field: str, expected: Iterable[str]
) -> type[T]:
    """A subclass of ``base`` whose ``list_field`` must hold exactly one entry per ID in
    ``expected`` (matched on ``id_field``). Keeps the class name, which is the tool name."""
    wanted = list(dict.fromkeys(expected))

    def check(self: T) -> T:
        got = [getattr(x, id_field) for x in getattr(self, list_field)]
        missing = [i for i in wanted if i not in got]
        unknown = [i for i in got if i not in wanted]
        dupes = sorted({i for i in got if got.count(i) > 1})
        problems = []
        if missing:
            problems.append(f"missing entries for {missing}")
        if unknown:
            problems.append(f"entries for IDs that were not shown: {unknown}")
        if dupes:
            problems.append(f"more than one entry for {dupes}")
        if problems:
            raise ValueError(
                f"Return exactly one `{list_field}` entry per {id_field} shown: "
                + "; ".join(problems)
            )
        return self

    return create_model(
        base.__name__,
        __base__=base,
        __module__=base.__module__,
        __validators__={"exact_ids": model_validator(mode="after")(check)},
    )


class Judge:
    """One judge model, its prompts and its cost log, shared by every scorer of a run."""

    def __init__(
        self,
        model: BaseChatModel,
        *,
        settings: Settings | None = None,
        prompts_dir: Path = PROMPTS_DIR,
        concurrency: int | None = None,
        run_id: str = "judge",
        source: str = "eval",
    ) -> None:
        self.model = model
        self.settings = settings or get_settings()
        self.prompts_dir = prompts_dir
        self.concurrency = concurrency or self.settings.llm_concurrency
        self.spec = model_spec_of(model)
        self.recorder = RunRecorder(source, self.spec, 0.0, run_id=run_id)
        self.failures = 0
        self._prompts: dict[str, Prompt] = {}

    def prompt(self, name: str) -> Prompt:
        if name not in self._prompts:
            p = load_prompt(name, prompts_dir=self.prompts_dir)
            self._prompts[name] = p
            self.recorder.record_prompt(name, p.sha256)
        return self._prompts[name]

    def call[T: BaseModel](self, schema: type[T], prompt: str, node: str, **variables: str) -> T:
        """Render ``prompt`` and return a validated ``schema``; raises
        ``StructuredOutputError`` when the retry budget runs out."""
        text = self.prompt(prompt).render(**variables)
        result = structured_call(
            self.model,
            schema,
            [HumanMessage(text)],
            node=node,
            settings=self.settings,
            recorder=self.recorder,
        )
        return result.value

    def map[I, O](self, fn: Callable[[I], O], items: Sequence[I]) -> list[O | None]:
        """``fn`` over ``items`` on the thread pool, in order. A batch whose judge call
        fails after its retries yields ``None`` and is counted in ``failures``."""

        def safe(item: I) -> O | None:
            try:
                return fn(item)
            except StructuredOutputError as exc:
                logger.warning("judge batch failed: %s", exc)
                self.failures += 1
                return None

        if not items:
            return []
        if self.concurrency <= 1 or len(items) == 1:
            return [safe(i) for i in items]
        with ThreadPoolExecutor(max_workers=min(self.concurrency, len(items))) as pool:
            return list(pool.map(safe, items))

    def cost(self) -> JudgeCost:
        log = self.recorder.log
        return JudgeCost(
            model=self.spec,
            calls=len(log.nodes),
            failures=self.failures,
            totals=log.totals(),
            per_node=per_node_totals(log),
        )
