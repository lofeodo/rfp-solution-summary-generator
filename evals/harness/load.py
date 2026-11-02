"""Load one pipeline run directory and the gold set for its RFP.

A run directory is what ``rfp_agent.graph.run_pipeline`` writes (S10): every stage's JSON,
``summary.json`` and ``run_log.json``. Only ``summary.json``, ``split.json`` and
``run_log.json`` are required; the stage results add the rounds, the mode and the
findings when present.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from evals.gold.label import RFPS, final_path, load_gold
from evals.gold.schema import GoldSet
from rfp_agent.agents.problem import ProblemResult
from rfp_agent.agents.risk import Findings, RiskResult, detect_findings
from rfp_agent.agents.solution import SolutionResult
from rfp_agent.schemas import Chunk, Requirement, RunLog, SolutionSummary, SplitDocument


class RunLoadError(FileNotFoundError):
    """A required file is missing from the run directory."""


def rfp_name(source_path: str) -> str:
    """Gold name for a source PDF path: ``data/rfps/NYESD.pdf`` -> ``NYESD``. Matched
    case-insensitively against the gold names, so a sample directory called ``nyesd``
    still finds ``NYESD.json``."""
    stem = Path(source_path.replace("\\", "/")).stem
    for name in RFPS:
        if name.lower() == stem.lower():
            return name
    return stem


def _read(path: Path) -> str:
    if not path.exists():
        raise RunLoadError(f"{path} not found")
    return path.read_text(encoding="utf-8")


@dataclass
class EvalRun:
    run_dir: Path
    summary: SolutionSummary
    split: SplitDocument
    log: RunLog
    problem: ProblemResult | None = None
    solution: SolutionResult | None = None
    risks: RiskResult | None = None
    report: dict = field(default_factory=dict)

    @classmethod
    def load(cls, run_dir: str | Path) -> EvalRun:
        run_dir = Path(run_dir)
        summary = SolutionSummary.model_validate_json(_read(run_dir / "summary.json"))
        split = SplitDocument.model_validate_json(_read(run_dir / "split.json"))
        log = RunLog.model_validate_json(_read(run_dir / "run_log.json"))

        def optional(name: str, model):
            path = run_dir / name
            return (
                model.model_validate_json(path.read_text(encoding="utf-8"))
                if path.exists()
                else None
            )

        report_path = run_dir / "requirements_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        return cls(
            run_dir=run_dir,
            summary=summary,
            split=split,
            log=log,
            problem=optional("problem.json", ProblemResult),
            solution=optional("solution.json", SolutionResult),
            risks=optional("risks.json", RiskResult),
            report=report,
        )

    # -- identity ---------------------------------------------------------------------

    @property
    def rfp(self) -> str:
        return rfp_name(self.summary.source_path)

    def gold(self) -> GoldSet:
        return load_gold(final_path(self.rfp))

    # -- lookups ----------------------------------------------------------------------

    @cached_property
    def chunks(self) -> dict[str, Chunk]:
        return {c.id: c for c in self.split.chunks()}

    @cached_property
    def requirements(self) -> dict[str, Requirement]:
        return {r.id: r for r in self.summary.requirements.requirements}

    def chunk_text(self, chunk_id: str) -> str | None:
        chunk = self.chunks.get(chunk_id)
        return chunk.text if chunk else None

    def pages_of(self, requirement: Requirement) -> set[int]:
        """Pages spanned by the chunks a requirement cites."""
        pages: set[int] = set()
        for cid in requirement.chunk_ids:
            c = self.chunks.get(cid)
            if c:
                pages.update(range(c.page_start, c.page_end + 1))
        return pages

    def source_blocks(self, ids: list[str]) -> list[tuple[str, str]]:
        """``(id, text)`` for every cited ID that resolves: a chunk's section path and
        text (the heading often carries the fact, e.g. "Task 2"), or a requirement's
        statement and quote. Unknown IDs are skipped (they are counted as dangling
        elsewhere)."""
        out: list[tuple[str, str]] = []
        seen: set[str] = set()
        for i in ids:
            if i in seen:
                continue
            seen.add(i)
            if i in self.chunks:
                c = self.chunks[i]
                heading = " > ".join(c.section_path)
                pages = f"page {c.page_start}" + (
                    f"-{c.page_end}" if c.page_end != c.page_start else ""
                )
                out.append((i, f"[{heading}, {pages}]\n{c.text}"))
            elif i in self.requirements:
                r = self.requirements[i]
                out.append((i, f"{r.text}\nQuote: {r.quote}"))
        return out

    def findings(self) -> Findings:
        """The risk stage's findings, or recomputed from the summary for older runs."""
        if self.risks is not None:
            return self.risks.findings
        return detect_findings(
            self.summary.requirements,
            self.summary.solution,
            referenced_documents=self.summary.referenced_documents,
            flags=self.summary.flags,
        )

    @property
    def wall_s(self) -> float:
        if self.log.finished_at is None:
            return 0.0
        return (self.log.finished_at - self.log.started_at).total_seconds()
