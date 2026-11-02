"""Stubs for the five LLM stages of the pipeline, shared by the graph, CLI and UI
backend tests. Parsing and splitting run for real on Federal Way (the smallest RFP); the
stubs return fixture objects that cite real chunk IDs, so the assembler's citation check
passes. No network."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

import pytest

from rfp_agent import graph as graph_mod
from rfp_agent.agents.problem import ProblemResult
from rfp_agent.agents.requirements import RequirementsReport
from rfp_agent.agents.risk import Findings, RiskResult
from rfp_agent.agents.solution import CoverageRound, SolutionResult
from rfp_agent.config import DATA_DIR, Settings
from rfp_agent.graph import PARSE_QUALITY, PROBLEM, REQUIREMENTS, RISK, SOLUTION
from rfp_agent.parsing import parse_pdf
from rfp_agent.schemas import (
    Claim,
    Coverage,
    Likelihood,
    NodeMetrics,
    ParseQualityReport,
    ProblemStatement,
    Requirement,
    RequirementsOutput,
    RequirementType,
    Risk,
    RiskAssessment,
    RiskSource,
    Severity,
    Solution,
    SolutionComponent,
    Strictness,
)
from rfp_agent.splitting import split_document

PDF = DATA_DIR / "rfps" / "federal_way.pdf"
SETTINGS = Settings(_env_file=None, max_structured_retries=1)


def first_chunk_id() -> str:
    """A real chunk ID of Federal Way, so stub outputs pass the citation check."""
    return split_document(parse_pdf(PDF)).chunks()[0].id


def fixtures(cid: str) -> dict[str, object]:
    reqs = RequirementsOutput(
        requirements=[
            Requirement(
                id="R001",
                text="Provide a hosted portal.",
                type=RequirementType.FUNCTIONAL,
                strictness=Strictness.MANDATORY,
                quote="Provide a hosted portal.",
                chunk_ids=[cid],
            ),
            Requirement(
                id="R002",
                text="Submit five copies.",
                type=RequirementType.SUBMISSION,
                strictness=Strictness.MANDATORY,
                quote="Submit five copies.",
                chunk_ids=[cid],
            ),
        ]
    )
    statement = ProblemStatement(
        client_situation=[Claim(text="Paper process.", chunk_ids=[cid])],
        goal=[Claim(text="A portal.", chunk_ids=[cid])],
        success_criteria=[Claim(text="Go-live.", chunk_ids=[cid])],
        constraints=[Claim(text="Budget.", chunk_ids=[cid])],
    )
    coverage = Coverage(mandatory_total=1, mandatory_covered=1)
    solution = Solution(
        summary="An approach.",
        components=[
            SolutionComponent(
                id="C01",
                title="Portal",
                description="Delivers it.",
                requirement_ids=["R001"],
                claims=[Claim(text="Paper today.", chunk_ids=[cid])],
            )
        ],
        coverage=coverage,
    )
    risks = RiskAssessment(
        risks=[
            Risk(
                id="K01",
                title="Slip",
                description="Could slip.",
                severity=Severity.HIGH,
                likelihood=Likelihood.MEDIUM,
                justification="Tight.",
                source=RiskSource.RFP,
                requirement_ids=["R001"],
                chunk_ids=[cid],
            )
        ]
    )
    return {
        "requirements": reqs,
        "problem": ProblemResult(mode="hierarchical", statement=statement),
        "solution": SolutionResult(
            solution=solution, rounds=[CoverageRound(iteration=1, coverage=coverage)]
        ),
        "risks": RiskResult(assessment=risks, findings=Findings()),
    }


def metric(node: str, cost: float = 0.01) -> NodeMetrics:
    return NodeMetrics(
        node=node,
        model="scripted",
        input_tokens=100,
        output_tokens=10,
        cost_usd=cost,
        latency_s=0.5,
        started_at=datetime.now(UTC),
    )


class Stubs:
    """Replacements for the five LLM stages; records what each received."""

    def __init__(self, cid: str, *, fail_at: str | None = None, barrier: bool = False):
        self.fx = fixtures(cid)
        self.calls: dict[str, dict] = {}
        self.fail_at = fail_at
        self.barrier = threading.Barrier(2, timeout=5) if barrier else None

    def _enter(self, stage: str, **kwargs) -> None:
        self.calls[stage] = kwargs
        if self.fail_at == stage:
            raise RuntimeError(f"{stage} boom")
        if self.barrier is not None and stage in (REQUIREMENTS, PROBLEM):
            self.barrier.wait()  # both branches must be inside at once

    def run_quality_pass(self, parsed, *, model, settings, recorder, config):
        self._enter(PARSE_QUALITY, model=model, settings=settings)
        recorder.record(metric("parse_quality"))
        return parsed.model_copy(update={"flags": []}), ParseQualityReport(judged_pages=[5])

    def extract_requirements(self, split, *, title, model, settings, recorder, config, single_call):
        self._enter(REQUIREMENTS, split=split, title=title, single_call=single_call)
        recorder.record(metric("requirements_extract"))
        recorder.record(metric("requirements_dedupe"))
        return self.fx["requirements"], RequirementsReport(chunks=len(split.chunks()))

    def build_problem_statement(
        self, split, *, title, model, settings, recorder, config, full_text
    ):
        self._enter(PROBLEM, split=split, full_text=full_text)
        recorder.record(metric("problem_synthesis"))
        return self.fx["problem"]

    def build_solution(
        self, requirements, problem, *, title, model, settings, recorder, config, max_iterations
    ):
        self._enter(
            SOLUTION, requirements=requirements, problem=problem, max_iterations=max_iterations
        )
        recorder.record(metric("solution_generate"))
        return self.fx["solution"]

    def build_risks(
        self,
        requirements,
        problem,
        solution,
        *,
        title,
        referenced_documents,
        flags,
        model,
        settings,
        recorder,
        config,
    ):
        self._enter(RISK, solution=solution, flags=list(flags), title=title)
        recorder.record(metric("risk_assess"))
        return self.fx["risks"]

    def install(self, monkeypatch: pytest.MonkeyPatch) -> Stubs:
        for name in (
            "run_quality_pass",
            "extract_requirements",
            "build_problem_statement",
            "build_solution",
            "build_risks",
        ):
            monkeypatch.setattr(graph_mod, name, getattr(self, name))
        return self
