"""Gold-label format, quote matching, and the draft/init/diff workflow. No network, no PDFs
(except the committed-gold check, which parses only RFPs that have a final gold file)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from evals.gold import label
from evals.gold.label import (
    DraftReport,
    diff_gold,
    diff_row,
    draft_gold,
    init_final,
    unverified_quotes,
    write_gold,
)
from evals.gold.schema import GoldChecklistItem, GoldRequirement, GoldSet, GoldSource
from evals.gold.textmatch import find_quote, normalise
from fakes import ScriptedChatModel, tool_call_msg
from rfp_agent.schemas import RequirementType, Strictness

DOC = (
    "[page 1]\n## **Scope**\n"
    "The Contractor **shall** deliver a web\napplication by March 1, 2025.\n"
    "Proposals should be under 20 pages.\n\n"
    "[page 2]\n| Item | Limit |\n|---|---|\n| Budget | Not to exceed<br>$175,000 |\n"
    "The vendor’s team must include a project manager – full time.\n"
)


def req(i: int, quote: str, **kw) -> GoldRequirement:
    base = dict(
        id=f"GR{i:03d}",
        text=f"Requirement {i}",
        type=RequirementType.FUNCTIONAL,
        strictness=Strictness.MANDATORY,
        quote=quote,
    )
    return GoldRequirement(**(base | kw))


def chk(i: int, fact: str = "A fact", quote: str | None = None) -> GoldChecklistItem:
    return GoldChecklistItem(id=f"GC{i:02d}", fact=fact, quote=quote)


def gold(**kw) -> GoldSet:
    return GoldSet(rfp="t", source_pdf="data/rfps/t.pdf", **kw)


# ---------------------------------------------------------------- schema


def test_round_trip():
    g = gold(requirements=[req(1, "deliver a web application", page=1)], checklist=[chk(1)])
    assert GoldSet.model_validate_json(g.model_dump_json()) == g


def test_duplicate_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate requirement ids"):
        gold(requirements=[req(1, "a"), req(1, "b")])
    with pytest.raises(ValidationError, match="duplicate checklist ids"):
        gold(checklist=[chk(1), chk(1)])


@pytest.mark.parametrize("bad", ["R001", "GR1", "GR01", "gr001"])
def test_bad_requirement_id_rejected(bad):
    with pytest.raises(ValidationError):
        req(1, "x", id=bad)


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        GoldRequirement.model_validate(req(1, "x").model_dump() | {"chunk_ids": ["S1.1"]})


def test_checklist_size():
    assert not gold(checklist=[chk(i) for i in range(1, 8)]).checklist_size_ok()
    assert gold(checklist=[chk(i) for i in range(1, 9)]).checklist_size_ok()
    assert not gold(checklist=[chk(i) for i in range(1, 14)]).checklist_size_ok()


# ---------------------------------------------------------------- quote matching


def test_normalise_strips_markup_and_typography():
    assert normalise("The **vendor’s**  team\n| x |") == "the vendor's team x"
    assert normalise("a–b<br>c") == "a-b c"


@pytest.mark.parametrize(
    "quote",
    [
        "The Contractor shall deliver a web application by March 1, 2025.",  # bold, newline
        "Not to exceed $175,000",  # across <br> in one cell
        "The vendor's team must include a project manager - full time.",  # curly, en dash
        "proposals SHOULD be under 20 pages",  # case
    ],
)
def test_find_quote_hits(quote):
    assert find_quote(DOC, quote)


@pytest.mark.parametrize("quote", ["deliver a mobile application", "", "   "])
def test_find_quote_misses(quote):
    assert not find_quote(DOC, quote)


# ---------------------------------------------------------------- draft


def draft_req(quote: str, **kw) -> dict:
    return {
        "text": "t",
        "type": "functional",
        "strictness": "mandatory",
        "quote": quote,
        "page": 1,
        "section": "Scope",
    } | kw


CHECKLIST_OK = [
    {"fact": f"Budget cap fact {i}", "quote": "Not to exceed $175,000"} for i in range(7)
] + [{"fact": "Invented", "quote": "a sentence that is not there"}]


def test_short_checklist_is_sent_back_and_retried():
    short = {"items": CHECKLIST_OK[:3]}
    model = ScriptedChatModel(
        responses=[
            tool_call_msg("DraftRequirements", {"requirements": []}),
            tool_call_msg("DraftChecklist", short),
            tool_call_msg("DraftChecklist", {"items": CHECKLIST_OK}),
        ]
    )
    report = draft_gold("t", DOC, model)
    assert len(report.gold.checklist) == 7
    feedback = model.calls[2][-1].content
    assert "between 8 and 12 facts, got 3" in feedback


def test_draft_assigns_ids_and_drops_unmatched_quotes():
    model = ScriptedChatModel(
        responses=[
            tool_call_msg(
                "DraftRequirements",
                {
                    "requirements": [
                        draft_req("shall deliver a web application"),
                        draft_req("deliver a mobile app"),  # not in the document
                        draft_req("Not to exceed $175,000", type="budget_pricing", page=2),
                    ]
                },
            ),
            tool_call_msg("DraftChecklist", {"items": CHECKLIST_OK}),
        ]
    )
    report: DraftReport = draft_gold("t", DOC, model)
    g = report.gold
    assert [r.id for r in g.requirements] == ["GR001", "GR002"]
    assert g.requirements[1].type is RequirementType.BUDGET_PRICING
    assert all(r.source is GoldSource.DRAFT for r in g.requirements)
    assert report.dropped_requirements == ["deliver a mobile app"]
    assert [c.id for c in g.checklist] == [f"GC{i:02d}" for i in range(1, 8)]
    assert report.dropped_checklist == ["a sentence that is not there"]
    assert g.drafted_with == "fake:scripted"
    # the document reached the model inside the prompt
    assert "Not to exceed<br>$175,000" in model.calls[0][-1].content


# ---------------------------------------------------------------- init and diff


@pytest.fixture
def gold_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(label, "GOLD_DIR", tmp_path)
    return tmp_path


def test_init_merges_hand_items_and_refuses_overwrite(gold_dir):
    draft = gold(requirements=[req(1, "a"), req(2, "b")], checklist=[chk(1)])
    write_gold(draft, label.draft_path("t", gold_dir))
    hand = gold(
        requirements=[req(1, "image table row", quote_verifiable=False)],
        notes=["Page 5 table is an image; labelled from the page render."],
    )
    write_gold(hand, label.hand_path("t", gold_dir))

    final = init_final("t", gold_dir)
    assert [r.id for r in final.requirements] == ["GR001", "GR002", "GR003"]
    assert final.requirements[2].source is GoldSource.HAND
    assert final.requirements[2].quote_verifiable is False
    assert final.notes == hand.notes
    with pytest.raises(FileExistsError):
        init_final("t", gold_dir)


def test_diff_counts_and_fraction():
    draft = gold(
        requirements=[req(1, "a"), req(2, "b"), req(3, "c"), req(4, "d")],
        checklist=[chk(1), chk(2)],
    )
    final = gold(
        requirements=[
            req(1, "a"),  # unchanged
            req(2, "b", strictness=Strictness.DESIRED, source=GoldSource.CORRECTED),
            req(3, "c", source=GoldSource.CORRECTED, note="note-only edits do not count"),
            # GR004 removed
            req(5, "e", source=GoldSource.HAND),  # added
        ],
        checklist=[chk(1), chk(2, fact="A sharper fact")],
    )
    d = diff_gold(draft, final)
    r = d.requirements
    assert (r.drafted, r.unchanged, r.modified, r.removed, r.added) == (4, 2, 1, 1, 1)
    assert r.field_changes == {"text": 0, "type": 0, "strictness": 1, "quote": 0}
    assert r.corrected_fraction == 0.5
    assert d.checklist.corrected_fraction == 0.5
    assert diff_row(d) == "| t | 4 | 1 | 1 | 1 | 50% | 2 | 50% | 0 |"


def test_unverified_quotes_skips_image_items():
    g = gold(
        requirements=[
            req(1, "shall deliver a web application"),
            req(2, "not in the text"),
            req(3, "also not in the text", quote_verifiable=False),
        ],
        checklist=[chk(1, quote="Not to exceed $175,000"), chk(2, quote="missing"), chk(3)],
    )
    assert unverified_quotes(g, DOC) == ["GR002", "GC02"]


# ---------------------------------------------------------------- committed gold


FINALS = [name for name in label.RFPS if label.final_path(name).exists()]


@pytest.mark.parametrize("name", FINALS)
def test_committed_gold_is_valid_and_grounded(name):
    g = label.load_gold(label.final_path(name))
    assert g.rfp == name
    assert g.checklist_size_ok()
    assert unverified_quotes(g, label.document_text(label.parse(name))) == []
