"""Versions, stale flags, revision log and diff (ST12b). Pure file and model code."""

from __future__ import annotations

from datetime import UTC, datetime

from rfp_agent import versions
from rfp_agent.schemas import (
    Artefact,
    ArtefactVersion,
    Claim,
    Coverage,
    RequirementsOutput,
    RevisionKind,
    RevisionRecord,
    Solution,
    SolutionComponent,
    VersionState,
)


def solution(*components: SolutionComponent, assumptions=()) -> Solution:
    return Solution(
        summary="An approach.",
        components=list(components),
        assumptions=list(assumptions),
        coverage=Coverage(mandatory_total=1, mandatory_covered=1),
    )


def comp(cid: str, *, title: str = "Portal", reqs=("R001",), desc: str = "Delivers it.", claims=()):
    return SolutionComponent(
        id=cid, title=title, description=desc, requirement_ids=list(reqs), claims=list(claims)
    )


def test_diff_matches_lists_by_id_and_claims_by_text():
    before = solution(comp("C01"), comp("C02", title="Training"))
    after = solution(
        comp("C01", claims=[Claim(text="Paper today.", chunk_ids=["S1.1"])]),
        comp("C03", title="Hosting"),
        assumptions=[Claim(text="Azure is acceptable.", kind="inference", chunk_ids=["S1.1"])],
    )
    d = versions.diff(before, after)
    assert "components[C03]" in d.added
    assert "components[C02]" in d.removed
    assert "components[C01].claims[Paper today.]" in d.added
    assert "assumptions[Azure is acceptable.]" in d.added
    assert not d.changed


def test_diff_set_diffs_scalar_lists_and_reports_field_changes():
    before = solution(comp("C01", reqs=("R001", "R002")))
    after = solution(comp("C01", reqs=("R001", "R003"), desc="Delivers it, hosted."))
    d = versions.diff(before, after)
    assert d.added == ["components[C01].requirement_ids[R003]"]
    assert d.removed == ["components[C01].requirement_ids[R002]"]
    assert [(c.path, c.before, c.after) for c in d.changed] == [
        ("components[C01].description", "Delivers it.", "Delivers it, hosted.")
    ]


def test_diff_of_equal_objects_is_empty_and_duplicate_claims_stay_two_items():
    s = solution(comp("C01"))
    assert versions.diff(s, s.model_copy(deep=True)).empty
    one = solution(assumptions=[Claim(text="Same.", kind="inference", chunk_ids=["S1.1"])])
    two = solution(assumptions=[Claim(text="Same.", kind="inference", chunk_ids=["S1.1"])] * 2)
    assert versions.diff(one, two).added == ["assumptions[Same. #2]"]


def test_commit_keeps_v1_writes_live_and_next_version(tmp_path):
    live = tmp_path / "solution.json"
    live.write_text('{"old": true}\n', encoding="utf-8")
    original = live.read_bytes()
    state = VersionState()
    obj = RequirementsOutput()  # any model; the content is what matters
    assert versions.commit(tmp_path, Artefact.SOLUTION, obj, state) == 2
    assert (tmp_path / "solution.v1.json").read_bytes() == original
    assert (tmp_path / "solution.v2.json").read_bytes() == live.read_bytes()
    assert state.artefacts[Artefact.SOLUTION].version == 2
    assert versions.is_versioned(tmp_path, Artefact.SOLUTION)
    assert versions.commit(tmp_path, Artefact.SOLUTION, obj, state) == 3
    assert (tmp_path / "solution.v1.json").read_bytes() == original  # never rewritten


def test_requirements_confirmed_copy_is_made_lazily_and_extractor_file_untouched(tmp_path):
    extracted = tmp_path / "requirements.json"
    extracted.write_text(RequirementsOutput().model_dump_json(), encoding="utf-8")
    before = extracted.read_bytes()
    state = VersionState()
    versions.commit(tmp_path, Artefact.REQUIREMENTS, RequirementsOutput(), state)
    assert extracted.read_bytes() == before
    assert (tmp_path / "requirements_confirmed.json").is_file()
    assert (tmp_path / "requirements_confirmed.v1.json").read_bytes() == before
    assert (tmp_path / "requirements_confirmed.v2.json").is_file()


def test_mark_stale_cascades_downstream_and_keeps_first_reason():
    state = VersionState()
    assert versions.mark_stale(state, Artefact.SOLUTION, "solution v2") == [Artefact.RISKS]
    assert versions.mark_stale(state, Artefact.REQUIREMENTS, "requirements v2") == [
        Artefact.SOLUTION
    ]
    assert versions.mark_stale(state, Artefact.RISKS, "risks v2") == []
    assert dict(versions.stale_artefacts(state)) == {
        Artefact.SOLUTION: "requirements v2",
        Artefact.RISKS: "solution v2",
    }


def test_commit_clears_the_stale_flag(tmp_path):
    (tmp_path / "risks.json").write_text("{}", encoding="utf-8")
    state = VersionState()
    state.artefacts[Artefact.RISKS] = ArtefactVersion(stale=True, stale_because="x")
    versions.commit(tmp_path, Artefact.RISKS, RequirementsOutput(), state)
    assert not state.artefacts[Artefact.RISKS].stale


def test_version_state_and_revision_log_round_trip(tmp_path):
    assert versions.load_version_state(tmp_path) == VersionState()
    assert versions.review_history(tmp_path) is None
    state = VersionState()
    versions.mark_stale(state, Artefact.PROBLEM, "problem v2")
    versions.save_version_state(tmp_path, state)
    assert versions.load_version_state(tmp_path) == state
    log = versions.load_revisions(tmp_path)
    assert versions.next_revision_id(log) == "V01"
    record = RevisionRecord(
        id="V01",
        kind=RevisionKind.REVISE,
        artefact=Artefact.PROBLEM,
        reviewer="Dana",
        instruction="Shorter.",
        created_at=datetime.now(UTC),
    )
    versions.append_revision(tmp_path, record)
    log = versions.append_revision(tmp_path, record.model_copy(update={"id": "V02"}))
    assert [r.id for r in log.revisions] == ["V01", "V02"]
    assert versions.next_revision_id(log) == "V03"
    history = versions.review_history(tmp_path)
    assert history is not None and [r.id for r in history.revisions] == ["V01", "V02"]
