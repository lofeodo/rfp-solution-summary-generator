"""Gold-label workflow: draft with the judge model, correct by hand, measure the correction.

    python -m evals.gold.label draft missouri      # writes evals/gold/missouri.draft.json
    python -m evals.gold.label init missouri       # copies it to missouri.json (+ hand items)
    # ... correct missouri.json by hand ...
    python -m evals.gold.label diff --all          # fraction of draft labels corrected
    python -m evals.gold.label check --all         # every gold quote is in the parsed text

The draft file is never edited after it is written, so the diff between it and the final
file is the record of what the human pass changed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from evals.gold.schema import (
    GoldChecklistItem,
    GoldRequirement,
    GoldSet,
    GoldSource,
    checklist_id,
    requirement_id,
)
from evals.gold.textmatch import find_quote
from rfp_agent.config import DATA_DIR
from rfp_agent.schemas import ParsedDocument, RequirementType, Strictness

GOLD_DIR = Path(__file__).resolve().parent
RFPS = ["missouri", "NYESD", "colfax", "federal_way"]

# Drafting asks for a long structured reply (40+ items with quotes); the provider default
# output cap and the pipeline's 120 s timeout are both too tight for that.
DRAFT_MAX_TOKENS = 16000
DRAFT_TIMEOUT_S = 600.0


# --------------------------------------------------------------------------------------
# What the drafting model returns (IDs and provenance are assigned by code)
# --------------------------------------------------------------------------------------


class DraftRequirement(BaseModel):
    text: str = Field(description="The requirement restated as one self-contained sentence")
    type: RequirementType
    strictness: Strictness
    quote: str = Field(description="Exact span copied from the document, one sentence or cell")
    page: int | None = Field(default=None, description="Page marker the quote appears under")
    section: str | None = Field(default=None, description="Nearest heading, as written")


class DraftRequirements(BaseModel):
    requirements: list[DraftRequirement]


class DraftChecklistItem(BaseModel):
    fact: str = Field(description="One fact a correct problem statement must mention")
    quote: str = Field(description="Exact span copied from the document that states it")
    page: int | None = None


class DraftChecklist(BaseModel):
    items: list[DraftChecklistItem]


# --------------------------------------------------------------------------------------
# Paths and document text
# --------------------------------------------------------------------------------------


def pdf_path(rfp: str) -> Path:
    return DATA_DIR / "rfps" / f"{rfp}.pdf"


def draft_path(rfp: str, gold_dir: Path = GOLD_DIR) -> Path:
    return gold_dir / f"{rfp}.draft.json"


def final_path(rfp: str, gold_dir: Path = GOLD_DIR) -> Path:
    return gold_dir / f"{rfp}.json"


def hand_path(rfp: str, gold_dir: Path = GOLD_DIR) -> Path:
    return gold_dir / f"{rfp}.hand.json"


def document_text(parsed: ParsedDocument) -> str:
    """Parsed pages joined with a page marker, so the model can report page numbers."""
    return "\n\n".join(f"[page {p.number}]\n{p.markdown}" for p in parsed.pages)


def parse(rfp: str) -> ParsedDocument:
    from rfp_agent.parsing import parse_pdf  # imported lazily: pymupdf is slow to load

    return parse_pdf(pdf_path(rfp))


def load_gold(path: Path) -> GoldSet:
    return GoldSet.model_validate_json(path.read_text(encoding="utf-8"))


def write_gold(gold: GoldSet, path: Path) -> None:
    path.write_text(gold.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# Draft
# --------------------------------------------------------------------------------------


@dataclass
class DraftReport:
    gold: GoldSet
    dropped_requirements: list[str] = field(default_factory=list)
    dropped_checklist: list[str] = field(default_factory=list)
    cost_usd: float = 0.0


def draft_gold(rfp: str, text: str, model: BaseChatModel) -> DraftReport:
    """Two judge calls (requirements, checklist). Items whose quote is not in ``text`` are
    dropped and reported: a gold label must be checkable against the source."""
    from rfp_agent.llm import load_prompt, model_spec_of, structured_call

    req_prompt = load_prompt("gold_requirements").render(document=text)
    req = structured_call(
        model, DraftRequirements, [HumanMessage(req_prompt)], node="gold_requirements"
    )
    chk_prompt = load_prompt("gold_checklist").render(document=text)
    chk = structured_call(model, DraftChecklist, [HumanMessage(chk_prompt)], node="gold_checklist")

    report = DraftReport(
        gold=GoldSet(
            rfp=rfp,
            source_pdf=f"data/rfps/{rfp}.pdf",
            drafted_with=model_spec_of(model),
            drafted_at=datetime.now(UTC).isoformat(timespec="seconds"),
        ),
        cost_usd=req.metrics.cost_usd + chk.metrics.cost_usd,
    )
    for d in req.value.requirements:
        if not find_quote(text, d.quote):
            report.dropped_requirements.append(d.quote)
            continue
        n = len(report.gold.requirements) + 1
        report.gold.requirements.append(
            GoldRequirement(id=requirement_id(n), **d.model_dump(), source=GoldSource.DRAFT)
        )
    for d in chk.value.items:
        if not find_quote(text, d.quote):
            report.dropped_checklist.append(d.quote)
            continue
        n = len(report.gold.checklist) + 1
        report.gold.checklist.append(
            GoldChecklistItem(id=checklist_id(n), **d.model_dump(), source=GoldSource.DRAFT)
        )
    return report


# --------------------------------------------------------------------------------------
# Init: draft -> final, plus hand-labelled items
# --------------------------------------------------------------------------------------


def init_final(rfp: str, gold_dir: Path = GOLD_DIR) -> GoldSet:
    """Copy the draft to the final file, appending items from ``<rfp>.hand.json`` with
    fresh IDs after the draft's. Refuses to overwrite an existing final file."""
    final = final_path(rfp, gold_dir)
    if final.exists():
        raise FileExistsError(f"{final} exists; edit it, or delete it to start over")
    gold = load_gold(draft_path(rfp, gold_dir))
    hand = hand_path(rfp, gold_dir)
    if hand.exists():
        extra = load_gold(hand)
        for r in extra.requirements:
            n = len(gold.requirements) + 1
            gold.requirements.append(
                r.model_copy(update={"id": requirement_id(n), "source": GoldSource.HAND})
            )
        for c in extra.checklist:
            n = len(gold.checklist) + 1
            gold.checklist.append(
                c.model_copy(update={"id": checklist_id(n), "source": GoldSource.HAND})
            )
        gold.notes.extend(extra.notes)
    write_gold(gold, final)
    return gold


# --------------------------------------------------------------------------------------
# Diff: how much did the human pass change?
# --------------------------------------------------------------------------------------

REQ_FIELDS = ("text", "type", "strictness", "quote")
CHK_FIELDS = ("fact", "quote")


@dataclass
class PartDiff:
    drafted: int = 0
    unchanged: int = 0
    modified: int = 0
    removed: int = 0
    added: int = 0
    field_changes: dict[str, int] = field(default_factory=dict)

    @property
    def corrected_fraction(self) -> float:
        """Share of drafted labels the human pass edited or deleted."""
        return (self.modified + self.removed) / self.drafted if self.drafted else 0.0


def _diff_part(draft: list[BaseModel], final: list[BaseModel], fields: tuple[str, ...]):
    out = PartDiff(drafted=len(draft), field_changes={f: 0 for f in fields})
    final_by_id = {x.id: x for x in final}
    draft_ids = {x.id for x in draft}
    for d in draft:
        f = final_by_id.get(d.id)
        if f is None:
            out.removed += 1
            continue
        changed = [name for name in fields if getattr(d, name) != getattr(f, name)]
        for name in changed:
            out.field_changes[name] += 1
        if changed:
            out.modified += 1
        else:
            out.unchanged += 1
    out.added = sum(1 for x in final if x.id not in draft_ids)
    return out


@dataclass
class GoldDiff:
    rfp: str
    requirements: PartDiff
    checklist: PartDiff


def diff_gold(draft: GoldSet, final: GoldSet) -> GoldDiff:
    return GoldDiff(
        rfp=final.rfp,
        requirements=_diff_part(draft.requirements, final.requirements, REQ_FIELDS),
        checklist=_diff_part(draft.checklist, final.checklist, CHK_FIELDS),
    )


DIFF_HEADER = (
    "| RFP | Req drafted | Req edited | Req removed | Req added | Req corrected "
    "| Checklist drafted | Checklist corrected | Checklist added |\n"
    "|---|---|---|---|---|---|---|---|---|"
)


def diff_row(d: GoldDiff) -> str:
    r, c = d.requirements, d.checklist
    return (
        f"| {d.rfp} | {r.drafted} | {r.modified} | {r.removed} | {r.added} "
        f"| {r.corrected_fraction:.0%} | {c.drafted} | {c.corrected_fraction:.0%} | {c.added} |"
    )


# --------------------------------------------------------------------------------------
# Check: every verifiable quote is in the parsed text
# --------------------------------------------------------------------------------------


def unverified_quotes(gold: GoldSet, text: str) -> list[str]:
    """IDs of items whose quote should be in the text but is not."""
    bad = [r.id for r in gold.requirements if r.quote_verifiable and not find_quote(text, r.quote)]
    bad += [
        c.id
        for c in gold.checklist
        if c.quote and c.quote_verifiable and not find_quote(text, c.quote)
    ]
    return bad


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

app = typer.Typer(add_completion=False, help=__doc__.split("\n\n")[0])
RfpArg = Annotated[str | None, typer.Argument(help=f"One of {', '.join(RFPS)}")]
AllOpt = Annotated[bool, typer.Option("--all", help="All four RFPs")]


def _targets(rfp: str | None, all_: bool) -> list[str]:
    if all_:
        return RFPS
    if rfp not in RFPS:
        raise typer.BadParameter(f"rfp must be one of {RFPS} (or pass --all)")
    return [rfp]


@app.command()
def draft(rfp: RfpArg = None, all_: AllOpt = False, force: bool = False) -> None:
    """Draft gold labels with the judge model (needs ANTHROPIC_API_KEY)."""
    from rfp_agent.llm import get_judge_model

    model = get_judge_model(max_tokens=DRAFT_MAX_TOKENS, timeout=DRAFT_TIMEOUT_S)
    for name in _targets(rfp, all_):
        out = draft_path(name)
        if out.exists() and not force:
            typer.echo(f"{name}: {out.name} exists, skipping (use --force to redraft)")
            continue
        report = draft_gold(name, document_text(parse(name)), model)
        write_gold(report.gold, out)
        typer.echo(
            f"{name}: {len(report.gold.requirements)} requirements, "
            f"{len(report.gold.checklist)} checklist items, "
            f"dropped {len(report.dropped_requirements)} + {len(report.dropped_checklist)} "
            f"with unmatched quotes, ${report.cost_usd:.3f}"
        )
        for q in report.dropped_requirements + report.dropped_checklist:
            typer.echo(f"  dropped: {q[:100]!r}")


@app.command()
def init(rfp: RfpArg = None, all_: AllOpt = False) -> None:
    """Copy each draft to its final file, appending hand-labelled items."""
    for name in _targets(rfp, all_):
        gold = init_final(name)
        typer.echo(f"{name}: wrote {final_path(name).name} ({len(gold.requirements)} req)")


@app.command()
def diff(rfp: RfpArg = None, all_: AllOpt = False) -> None:
    """Print the draft-vs-final correction table (markdown)."""
    typer.echo(DIFF_HEADER)
    for name in _targets(rfp, all_):
        if not (draft_path(name).exists() and final_path(name).exists()):
            typer.echo(f"| {name} | (no draft and final yet) |||||||| ")
            continue
        typer.echo(diff_row(diff_gold(load_gold(draft_path(name)), load_gold(final_path(name)))))


@app.command()
def check(rfp: RfpArg = None, all_: AllOpt = False) -> None:
    """Verify every gold quote against the parsed text; exit 1 on any miss."""
    failed = False
    for name in _targets(rfp, all_):
        path = final_path(name)
        if not path.exists():
            typer.echo(f"{name}: no final gold yet")
            continue
        gold = load_gold(path)
        bad = unverified_quotes(gold, document_text(parse(name)))
        size = "ok" if gold.checklist_size_ok() else f"{len(gold.checklist)} (want 8-12)"
        typer.echo(f"{name}: unverified quotes {bad or 'none'}; checklist size {size}")
        failed |= bool(bad) or not gold.checklist_size_ok()
    raise typer.Exit(1 if failed else 0)


if __name__ == "__main__":
    app()
