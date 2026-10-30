"""Requirements extractor (S5) with a scripted fake model. No network."""

from __future__ import annotations

import json
import random

from langchain_core.messages import AIMessage, HumanMessage

from fakes import ScriptedChatModel, tool_call_msg
from rfp_agent.agents.requirements import (
    NODE_DEDUPE,
    NODE_EXTRACT,
    NODE_EXTRACT_SINGLE,
    apply_groups,
    check_groups,
    exact_dedupe,
    extract_requirements,
    render_chunk_prompt,
    sanitise_groups,
)
from rfp_agent.config import Settings
from rfp_agent.llm import load_prompt
from rfp_agent.observability import RunRecorder
from rfp_agent.schemas import (
    Chunk,
    DedupeOutput,
    Requirement,
    RequirementsOutput,
    RequirementType,
    Section,
    SectionKind,
    SplitDocument,
    Strictness,
)

SETTINGS = Settings(_env_file=None, max_structured_retries=1, llm_concurrency=1)

TEXTS = {
    "S1.1": "The Contractor **shall** deliver a web application by March 1, 2025. "
    "Proposals should be under 20 pages.",
    "S2.1": "Proposals should be under 20 pages. The budget is not to exceed $175,000. "
    "See Attachment F for the software requirements.",
    "S2.2": "The vendor’s team must include a project manager – full time. "
    "Pricing is in Attachment F. The Contractor shall deliver a web application.",
}


def split(ids: list[str] | None = None, texts: dict[str, str] | None = None) -> SplitDocument:
    texts = texts or TEXTS
    ids = ids or list(texts)
    sections: dict[str, Section] = {}
    for cid in ids:
        sid = cid.split(".")[0]
        sections.setdefault(
            sid,
            Section(
                id=sid,
                title=f"Section {sid}",
                level=1,
                path=[f"Section {sid}"],
                page_start=1,
                page_end=2,
                kind=SectionKind.REQUIREMENT_BEARING,
            ),
        ).chunks.append(
            Chunk(
                id=cid,
                section_id=sid,
                section_path=[f"Section {sid}"],
                page_start=1,
                page_end=1,
                text=texts.get(cid, f"Chunk {cid} says nothing of note."),
            )
        )
    return SplitDocument(sections=list(sections.values()))


def item(text: str, quote: str, type_: str = "functional", strictness: str = "mandatory") -> dict:
    return {"text": text, "type": type_, "strictness": strictness, "quote": quote}


def reply(reqs=(), ambs=(), gaps=()) -> AIMessage:
    return tool_call_msg(
        "ChunkExtraction",
        {"requirements": list(reqs), "ambiguities": list(ambs), "gaps": list(gaps)},
    )


def dedupe(groups=(), conflicts=()) -> AIMessage:
    return tool_call_msg("DedupeOutput", {"groups": list(groups), "conflicts": list(conflicts)})


def run(doc: SplitDocument, responses: list[AIMessage], **kw):
    model = ScriptedChatModel(responses=responses)
    settings = kw.pop("settings", SETTINGS)
    out, report = extract_requirements(doc, model=model, settings=settings, title="Test RFP", **kw)
    return model, out, report


WEB = item(
    "Deliver a web application by March 1, 2025.", "deliver a web application by March 1, 2025"
)
PAGES = item(
    "Proposals are under 20 pages.", "Proposals should be under 20 pages", "submission", "desired"
)
BUDGET = item("Budget not to exceed $175,000.", "not to exceed $175,000", "budget_pricing")
PM = item("Team includes a full-time project manager.", "must include a project manager", "other")


# ---------------------------------------------------------------- prompt


def test_prompt_renders_chunk_and_has_no_other_placeholders():
    prompt = load_prompt("requirements_extract")
    assert prompt.variables == {"unit", "mode_rules", "title", "input"}
    chunk = split().chunks()[0]
    text = render_chunk_prompt(prompt, chunk, "Test RFP")
    assert "Title: Test RFP" in text
    assert '<chunk id="S1.1">' in text and TEXTS["S1.1"] in text
    assert "Section: Section S1" in text and "Pages: 1" in text
    assert "{{" not in text
    assert load_prompt("requirements_dedupe").variables == {"requirements"}


# ---------------------------------------------------------------- happy path


def test_empty_document_makes_no_call():
    model, out, report = run(SplitDocument(sections=[]), [])
    assert model.calls == [] and out == RequirementsOutput() and report.chunks == 0


def test_items_are_numbered_cited_and_verified():
    doc = split(["S1.1", "S2.1"])
    ambiguity = {"description": "Which pages count?", "requirement_indexes": [0, 7]}
    gap = {"description": "Software requirements elsewhere", "referenced_document": "Attachment F"}
    model, out, report = run(
        doc, [reply([WEB]), reply([PAGES, BUDGET], [ambiguity], [gap]), dedupe()]
    )
    assert [r.id for r in out.requirements] == ["R001", "R002", "R003"]
    assert [r.chunk_ids for r in out.requirements] == [["S1.1"], ["S2.1"], ["S2.1"]]
    assert all(r.quote_verified for r in out.requirements)
    assert out.requirements[1].strictness is Strictness.DESIRED
    assert out.requirements[2].type is RequirementType.BUDGET_PRICING
    (amb,) = out.ambiguities
    assert (amb.id, amb.chunk_ids, amb.requirement_ids) == ("A01", ["S2.1"], ["R002"])  # 7 dropped
    (g,) = out.gaps
    assert (g.id, g.referenced_document, g.chunk_ids) == ("G01", "Attachment F", ["S2.1"])
    assert len(model.calls) == 3  # two chunks, one grouping call
    assert report.pre_dedupe == 3 and report.exact_merges == 0 and report.fuzzy_merges == 0
    assert not report.unverified_quotes and not report.calls_failed


def test_single_requirement_skips_the_grouping_call():
    model, out, report = run(split(["S1.1"]), [reply([WEB])])
    assert len(model.calls) == 1 and len(out.requirements) == 1


# ---------------------------------------------------------------- quote verification


def test_unverified_quote_is_fed_back_and_corrected_reply_accepted():
    bad = item("Deliver a web application.", "deliver a mobile application")
    model, out, report = run(split(["S1.1"]), [reply([bad]), reply([WEB])])
    assert len(model.calls) == 2
    first, second = model.calls
    assert second[0] == first[0]
    assert isinstance(second[1], AIMessage) and json.loads(second[1].content)["requirements"]
    assert isinstance(second[2], HumanMessage)
    assert 'the quote "deliver a mobile application" was not found verbatim in chunk S1.1' in (
        second[2].content
    )
    (r,) = out.requirements
    assert r.quote_verified and r.quote == WEB["quote"]
    assert report.quote_retries == 1 and report.unverified_quotes == []


def test_worse_retry_is_discarded():
    bad = item("Deliver a web application.", "deliver a mobile application")
    worse = item("Pages.", "under 200 pages")
    model, out, report = run(
        split(["S1.1"]), [reply([bad, PAGES]), reply([worse, worse]), dedupe()]
    )
    assert [r.quote for r in out.requirements] == [bad["quote"], PAGES["quote"]]
    assert [r.quote_verified for r in out.requirements] == [False, True]
    assert report.unverified_quotes == ["R001"]


def test_still_unverified_quote_is_kept_and_flagged():
    bad = item("Deliver a web application.", "deliver a mobile application")
    _, out, report = run(split(["S1.1"]), [reply([bad]), reply([bad])])
    (r,) = out.requirements
    assert not r.quote_verified and report.unverified_quotes == ["R001"]


def test_quote_matches_through_markup_and_typography():
    quote = item("Full-time PM.", "The vendor's team must include a project manager - full time.")
    _, out, _ = run(split(["S2.2"]), [reply([quote])])
    assert out.requirements[0].quote_verified


def test_failed_chunk_is_skipped_and_counted(caplog):
    broken = tool_call_msg("ChunkExtraction", {"requirements": "not a list"})
    model, out, report = run(split(["S1.1", "S2.1"]), [broken, broken, reply([BUDGET])])
    assert report.calls_failed == ["S1.1"]
    assert [r.chunk_ids for r in out.requirements] == [["S2.1"]]
    assert "chunk S1.1 failed" in caplog.text


# ---------------------------------------------------------------- exact dedupe


def test_same_text_across_overlapping_chunks_folds():
    doc = split(["S1.1", "S2.1"])
    stricter = PAGES | {"strictness": "mandatory"}
    ambiguity = {"description": "Which pages count?", "requirement_indexes": [0]}
    _, out, report = run(doc, [reply([PAGES]), reply([stricter], [ambiguity]), dedupe()])
    (r,) = out.requirements
    assert (r.id, r.chunk_ids, r.merged_from) == ("R001", ["S1.1", "S2.1"], ["R002"])
    assert r.strictness is Strictness.MANDATORY
    assert out.ambiguities[0].requirement_ids == ["R001"]
    assert report.pre_dedupe == 2 and report.exact_merges == 1


def test_exact_dedupe_adopts_a_verified_quote_over_an_unverified_one():
    a = Requirement(id="R001", text="X", type="other", strictness="optional", quote="bad",
                    chunk_ids=["S1.1"], quote_verified=False)  # fmt: skip
    b = Requirement(id="R002", text="X", type="other", strictness="desired", quote="good",
                    chunk_ids=["S1.2"], quote_verified=True)  # fmt: skip
    (kept,), fold = exact_dedupe([a, b])
    assert (kept.quote, kept.quote_verified, kept.strictness) == ("good", True, Strictness.DESIRED)
    assert fold == {"R002": "R001"}


# ---------------------------------------------------------------- fuzzy dedupe


def three() -> tuple[SplitDocument, list[AIMessage]]:
    web2 = item("Web app delivered by 1 March 2025.", "deliver a web application", "timeline")
    return split(["S1.1", "S2.1", "S2.2"]), [reply([WEB, PAGES]), reply([BUDGET]), reply([web2])]


def test_groups_merge_into_representative():
    doc, replies = three()
    group = {"representative_id": "R004", "member_ids": ["R001"]}
    model, out, report = run(doc, [*replies, dedupe([group])])
    assert [r.id for r in out.requirements] == ["R002", "R003", "R004"]
    r = out.requirements[2]
    assert (r.merged_from, r.chunk_ids) == (["R001"], ["S2.2", "S1.1"])
    assert r.text == "Web app delivered by 1 March 2025." and r.strictness is Strictness.MANDATORY
    assert report.fuzzy_merges == 1 and not report.dedupe_fallback
    dedupe_prompt = model.calls[3][0].content
    assert 'R001 [mandatory, functional] Deliver a web application by March 1, 2025. — "' in (
        dedupe_prompt
    )


def test_violations_get_one_retry_then_fallback():
    doc, replies = three()
    bad = [
        {"representative_id": "R009", "member_ids": ["R001"]},
        {"representative_id": "R004", "member_ids": ["R001", "R004"]},
        {"representative_id": "R002", "member_ids": ["R001"]},
    ]
    model, out, report = run(doc, [*replies, dedupe(bad), dedupe(bad)])
    feedback = model.calls[4][2].content
    assert "requirement ID R009 does not exist" in feedback
    assert "representative R004 is also a member" in feedback
    assert "R001 appears in group 0 and group 1" in feedback
    assert report.dedupe_retried and report.dedupe_fallback and len(report.dedupe_violations) == 4
    # Sanitised: group 0 dropped (unknown representative), R001 lands in group 1 only.
    assert [r.id for r in out.requirements] == ["R002", "R003", "R004"]
    assert out.requirements[2].merged_from == ["R001"]


def test_conflict_pair_inside_a_group_is_split_and_flagged():
    doc, replies = three()
    group = {"representative_id": "R004", "member_ids": ["R001"]}
    conflict = {"requirement_ids": ["R001", "R004"], "reason": "Different dates."}
    _, out, report = run(doc, [*replies, dedupe([group], [conflict]), dedupe([group], [conflict])])
    assert report.dedupe_fallback and report.dedupe_violations == [
        "conflicting items R001, R004 are inside the same group"
    ]
    ids = [r.id for r in out.requirements]
    assert ids == ["R001", "R002", "R003", "R004"]
    assert out.requirements[0].conflicts_with == ["R004"]
    assert out.requirements[3].conflicts_with == ["R001"]
    (amb,) = out.ambiguities
    assert amb.description == "Conflicting requirements R001 and R004: Different dates."
    assert (amb.requirement_ids, amb.chunk_ids) == (["R001", "R004"], ["S1.1", "S2.2"])
    assert report.conflicts == 1 and report.fuzzy_merges == 0


def test_conflict_ids_follow_merges():
    doc, replies = three()
    group = {"representative_id": "R004", "member_ids": ["R001"]}
    conflict = {"requirement_ids": ["R001", "R003"], "reason": "Budget vs date."}
    _, out, _ = run(doc, [*replies, dedupe([group], [conflict])])
    by_id = {r.id: r for r in out.requirements}
    assert by_id["R004"].conflicts_with == ["R003"] and by_id["R003"].conflicts_with == ["R004"]


def test_grouping_call_failure_keeps_exact_result():
    doc, replies = three()
    broken = tool_call_msg("DedupeOutput", {"groups": "no"})
    _, out, report = run(doc, [*replies, broken, broken])
    assert report.dedupe_failed and len(out.requirements) == 4


def test_every_original_id_lands_in_exactly_one_place_for_any_grouping():
    rng = random.Random(5)
    ids = [f"R{n:03d}" for n in range(1, 9)]
    reqs = [
        Requirement(
            id=i,
            text=f"text {i}",
            type="other",
            strictness="optional",
            quote=f"q {i}",
            chunk_ids=[f"S{n}.1"],
        )  # fmt: skip
        for n, i in enumerate(ids, 1)
    ]
    pool = ids + ["R099", "R100"]
    for _ in range(60):
        groups = [
            {
                "representative_id": rng.choice(pool),
                "member_ids": rng.sample(pool, rng.randint(1, 4)),
            }
            for _ in range(rng.randint(0, 4))
        ]
        conflicts = [
            {"requirement_ids": rng.sample(pool, 2), "reason": "r"}
            for _ in range(rng.randint(0, 2))
        ]
        output = sanitise_groups(DedupeOutput(groups=groups, conflicts=conflicts), ids)
        assert check_groups(output, ids) == []
        survivors, fold = apply_groups(reqs, output)
        landed = [r.id for r in survivors] + [m for r in survivors for m in r.merged_from]
        assert sorted(landed) == ids
        assert all(fold[m] == r.id for r in survivors for m in r.merged_from)


# ---------------------------------------------------------------- gaps and reporting


def test_gaps_dedupe_by_document_name():
    doc = split(["S2.1", "S2.2"])
    g1 = {"description": "Software requirements elsewhere", "referenced_document": "Attachment F"}
    g2 = {"description": "Pricing elsewhere", "referenced_document": "attachment f"}
    g3 = {"description": "Spreadsheet", "referenced_document": "ATTACHMENT F: SOFTWARE ABILITIES"}
    g4 = {"description": "Other", "referenced_document": "Attachment FF"}
    _, out, _ = run(doc, [reply([BUDGET], gaps=[g1]), reply([PM], gaps=[g2, g3, g4]), dedupe()])
    assert [(g.id, g.referenced_document) for g in out.gaps] == [
        ("G01", "Attachment F"),
        ("G02", "Attachment FF"),
    ]
    assert (
        out.gaps[0].chunk_ids == ["S2.1", "S2.2"] and out.gaps[0].description == g1["description"]
    )


def test_calls_land_on_the_active_recorder(tmp_path):
    rec = RunRecorder("t.pdf", "fake:scripted", 0.0, runs_dir=tmp_path)
    with rec.activate(write=False):
        run(split(["S1.1", "S2.1"]), [reply([WEB]), reply([BUDGET]), dedupe()])
    assert [n.node for n in rec.log.nodes] == [NODE_EXTRACT, NODE_EXTRACT, NODE_DEDUPE]
    assert set(rec.log.prompt_hashes) == {"requirements_extract", "requirements_dedupe"}


def test_concurrent_calls_keep_document_order():
    ids = [f"S{n}.1" for n in range(1, 9)]
    doc = split(ids, {i: f"Chunk {i} text: the vendor shall do thing {i}." for i in ids})

    def responder(messages):
        if "requirements_dedupe" in messages[0].content or "Each line is" in messages[0].content:
            return dedupe()
        cid = messages[0].content.split('<chunk id="')[1].split('"')[0]
        return reply([item(f"Do thing {cid}.", f"shall do thing {cid}")])

    model = ScriptedChatModel(responder=responder)
    settings = Settings(_env_file=None, max_structured_retries=1, llm_concurrency=4)
    out, report = extract_requirements(doc, model=model, settings=settings, title="T")
    assert [r.chunk_ids for r in out.requirements] == [[i] for i in ids]
    assert [r.id for r in out.requirements] == [f"R{n:03d}" for n in range(1, 9)]
    assert len(model.calls) == 9 and all(r.quote_verified for r in out.requirements)


# ---------------------------------------------------------------- single call


def cited(d: dict, chunk_id: str) -> dict:
    return d | {"chunk_id": chunk_id}


def document_reply(reqs=(), ambs=(), gaps=()) -> AIMessage:
    return tool_call_msg(
        "DocumentExtraction",
        {"requirements": list(reqs), "ambiguities": list(ambs), "gaps": list(gaps)},
    )


def test_single_call_verifies_against_cited_chunk_and_skips_grouping():
    doc = split(["S1.1", "S2.1", "S2.2"])
    first = document_reply(
        [cited(BUDGET, "S2.1"), cited(WEB, "S9.9"), cited(PM, "S1.1")],
        [{"description": "Vague.", "requirement_indexes": [0], "chunk_ids": ["S2.1", "S7.7"]}],
    )
    fixed = document_reply(
        [cited(BUDGET, "S2.1"), cited(WEB, "S1.1"), cited(PM, "S2.2")],
        [{"description": "Vague.", "requirement_indexes": [0], "chunk_ids": ["S2.1"]}],
        [
            {
                "description": "Pricing elsewhere",
                "referenced_document": "Attachment F",
                "chunk_ids": [],
            }
        ],
    )
    model, out, report = run(doc, [first, fixed], single_call=True)
    assert len(model.calls) == 2  # one document call, its retry, no grouping call
    feedback = model.calls[1][2].content
    assert "chunk ID S9.9 does not exist" in feedback
    assert 'the quote "must include a project manager" was not found verbatim in chunk S1.1' in (
        feedback
    )
    assert [(r.id, r.chunk_ids) for r in out.requirements] == [
        ("R001", ["S1.1"]),
        ("R002", ["S2.1"]),
        ("R003", ["S2.2"]),
    ]
    assert out.ambiguities[0].requirement_ids == ["R002"]
    assert out.gaps[0].referenced_document == "Attachment F"
    assert report.single_call and report.quote_retries == 1 and report.dropped_unknown_chunk == 0
    assert out.requirements[0].text == WEB["text"]


def test_single_call_drops_unknown_chunk_after_retry():
    doc = split(["S1.1"])
    bad = document_reply([cited(WEB, "S9.9"), cited(WEB, "S1.1")])
    _, out, report = run(doc, [bad, bad], single_call=True)
    assert [r.chunk_ids for r in out.requirements] == [["S1.1"]]
    assert report.dropped_unknown_chunk == 1


def test_single_call_setting_is_the_default_and_node_is_named():
    settings = Settings(_env_file=None, max_structured_retries=1, single_call_extraction=True)
    rec = RunRecorder("t.pdf", "fake:scripted", 0.0)
    with rec.activate(write=False):
        model, out, report = run(
            split(["S1.1"]), [document_reply([cited(WEB, "S1.1")])], settings=settings
        )
    assert report.single_call and [n.node for n in rec.log.nodes] == [NODE_EXTRACT_SINGLE]
