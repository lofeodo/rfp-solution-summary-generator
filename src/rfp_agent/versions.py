"""Versions, stale flags, the revision log and the diff of a reviewed run (ST12b).

Pure file and state helpers, no LLM. A run directory keeps every artefact's live file
where the pipeline, the renderer and the UI already read it (``problem.json``,
``solution.json``, ``risks.json``, ``requirements_confirmed.json``); this module adds

- ``<stem>.vN.json``: a copy of each version, ``v1`` taken from the live file just
  before its first change, so an unrevised run gains no files;
- ``current.json`` (``VersionState``): each artefact's version and stale flag, and the
  sign-off once there is one;
- ``revisions.json`` (``RevisionLog``): append-only, one record per revision,
  regeneration or sign-off, with the reviewer, the instruction, the diff and the cost.

Stale rules: a change to the requirements or the problem statement makes the solution
and the risks stale; a change to the solution makes the risks stale. A revision or a
regeneration of an artefact clears its own flag. Nothing is regenerated automatically.

``diff`` compares two versions structurally: items of a list are matched by their ``id``
(requirements, components, risks), claims by their text, scalar lists as sets; what
remains is a field change with its before and after values.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from rfp_agent.checkpoint import CHECKPOINT_FILENAME, CONFIRMED_REQUIREMENTS_FILENAME
from rfp_agent.schemas import (
    Artefact,
    ArtefactVersion,
    CheckpointRecord,
    DiffSummary,
    FieldChange,
    ReviewHistory,
    RevisionLog,
    RevisionRecord,
    VersionState,
)

CURRENT_FILENAME = "current.json"
REVISIONS_FILENAME = "revisions.json"
EXTRACTED_REQUIREMENTS_FILENAME = "requirements.json"

LIVE_FILES: dict[Artefact, str] = {
    Artefact.REQUIREMENTS: CONFIRMED_REQUIREMENTS_FILENAME,
    Artefact.PROBLEM: "problem.json",
    Artefact.SOLUTION: "solution.json",
    Artefact.RISKS: "risks.json",
}

DOWNSTREAM: dict[Artefact, tuple[Artefact, ...]] = {
    Artefact.REQUIREMENTS: (Artefact.SOLUTION, Artefact.RISKS),
    Artefact.PROBLEM: (Artefact.SOLUTION, Artefact.RISKS),
    Artefact.SOLUTION: (Artefact.RISKS,),
    Artefact.RISKS: (),
}


# --------------------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------------------


def _write_json(path: Path, obj: BaseModel) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(obj.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def live_path(run_dir: Path, artefact: Artefact) -> Path:
    return Path(run_dir) / LIVE_FILES[artefact]


def version_path(run_dir: Path, artefact: Artefact, version: int) -> Path:
    """``solution.v2.json``, ``requirements_confirmed.v1.json``..."""
    stem = LIVE_FILES[artefact].removesuffix(".json")
    return Path(run_dir) / f"{stem}.v{version}.json"


def is_versioned(run_dir: Path, artefact: Artefact) -> bool:
    """True once the artefact has changed at least once (its ``v1`` copy exists)."""
    return version_path(run_dir, artefact, 1).is_file()


def ensure_live(run_dir: Path, artefact: Artefact) -> Path:
    """The artefact's live file. For the requirements of a run still waiting at the
    checkpoint there is no confirmed list yet: it starts as a copy of the extractor's
    output, which itself is never changed. Raises ``FileNotFoundError`` when the run
    has no such artefact."""
    path = live_path(run_dir, artefact)
    if not path.is_file() and artefact is Artefact.REQUIREMENTS:
        extracted = Path(run_dir) / EXTRACTED_REQUIREMENTS_FILENAME
        if extracted.is_file():
            shutil.copyfile(extracted, path)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def load_version_state(run_dir: Path) -> VersionState:
    path = Path(run_dir) / CURRENT_FILENAME
    if not path.is_file():
        return VersionState()
    return VersionState.model_validate_json(path.read_text(encoding="utf-8"))


def save_version_state(run_dir: Path, state: VersionState) -> Path:
    return _write_json(Path(run_dir) / CURRENT_FILENAME, state)


def load_revisions(run_dir: Path) -> RevisionLog:
    path = Path(run_dir) / REVISIONS_FILENAME
    if not path.is_file():
        return RevisionLog()
    return RevisionLog.model_validate_json(path.read_text(encoding="utf-8"))


def next_revision_id(log: RevisionLog) -> str:
    return f"V{len(log.revisions) + 1:02d}"


def append_revision(run_dir: Path, record: RevisionRecord) -> RevisionLog:
    """Append ``record`` to ``revisions.json``; earlier records are never rewritten."""
    log = load_revisions(run_dir)
    log.revisions.append(record)
    _write_json(Path(run_dir) / REVISIONS_FILENAME, log)
    return log


def commit(
    run_dir: Path,
    artefact: Artefact,
    obj: BaseModel,
    state: VersionState,
    *,
    now: datetime | None = None,
) -> int:
    """Make ``obj`` the artefact's next version: keep a copy of the current version if
    none exists yet, write the live file and its ``vN+1`` copy, clear the stale flag.
    Updates ``state`` in place (the caller saves it) and returns the new version."""
    run_dir = Path(run_dir)
    current = state.artefacts.get(artefact, ArtefactVersion())
    live = ensure_live(run_dir, artefact)
    before = version_path(run_dir, artefact, current.version)
    if not before.is_file():
        shutil.copyfile(live, before)
    new = current.version + 1
    _write_json(live, obj)
    shutil.copyfile(live, version_path(run_dir, artefact, new))
    state.artefacts[artefact] = ArtefactVersion(version=new, updated_at=now or datetime.now(UTC))
    return new


def mark_stale(
    state: VersionState,
    changed: Artefact,
    because: str,
    *,
    present: Iterable[Artefact] | None = None,
) -> list[Artefact]:
    """Mark the artefacts downstream of ``changed`` stale; return the ones newly marked.
    An artefact already stale keeps its first reason. With ``present``, only those
    artefacts are marked: one not drafted yet (a run waiting at the checkpoint) will be
    drafted from the current inputs, so it cannot be stale."""
    allowed = set(present) if present is not None else set(Artefact)
    marked = []
    for a in DOWNSTREAM[changed]:
        if a not in allowed:
            continue
        v = state.artefacts.get(a, ArtefactVersion())
        if not v.stale:
            state.artefacts[a] = v.model_copy(update={"stale": True, "stale_because": because})
            marked.append(a)
    return marked


def stale_artefacts(state: VersionState) -> list[tuple[Artefact, str]]:
    return [(a, v.stale_because or "") for a, v in state.artefacts.items() if v.stale]


def is_signed_off(state: VersionState) -> bool:
    return state.signed_off is not None


def review_history(
    run_dir: Path, checkpoint: CheckpointRecord | None = None
) -> ReviewHistory | None:
    """Every human touchpoint recorded in ``run_dir``: the checkpoint (``checkpoint``,
    or ``checkpoint.json``), the revisions and the sign-off. ``None`` when there is none,
    so an unattended run's summary stays as it was."""
    run_dir = Path(run_dir)
    if checkpoint is None and (run_dir / CHECKPOINT_FILENAME).is_file():
        checkpoint = CheckpointRecord.model_validate_json(
            (run_dir / CHECKPOINT_FILENAME).read_text(encoding="utf-8")
        )
    revisions = load_revisions(run_dir).revisions
    sign_off = load_version_state(run_dir).signed_off
    if checkpoint is None and not revisions and sign_off is None:
        return None
    return ReviewHistory(checkpoint=checkpoint, revisions=revisions, sign_off=sign_off)


# --------------------------------------------------------------------------------------
# Diff
# --------------------------------------------------------------------------------------

_LABEL_CHARS = 60


def diff(before: Any, after: Any) -> DiffSummary:
    """Structural difference from ``before`` to ``after`` (models or JSON values)."""
    out = DiffSummary()
    _diff(_plain(before), _plain(after), "", out)
    return out


def _plain(value: Any) -> Any:
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else value


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _label(item: Any) -> str | None:
    """How a list item is matched across versions, or ``None`` to match by position."""
    if isinstance(item, dict):
        for key in ("id", "chunk_id"):
            if isinstance(item.get(key), str):
                return item[key]
        if isinstance(item.get("text"), str):
            text = " ".join(item["text"].split())
            return text if len(text) <= _LABEL_CHARS else text[: _LABEL_CHARS - 3] + "..."
        return None
    if isinstance(item, list):
        return None
    return str(item)


def _keyed(items: list[Any]) -> dict[str, Any] | None:
    keyed: dict[str, Any] = {}
    for item in items:
        label = _label(item)
        if label is None:
            return None
        n, base = 2, label
        while label in keyed:  # two claims with the same text stay two items
            label = f"{base} #{n}"
            n += 1
        keyed[label] = item
    return keyed


def _diff(a: Any, b: Any, path: str, out: DiffSummary) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for key in a:
            if key not in b:
                out.removed.append(_join(path, key))
            else:
                _diff(a[key], b[key], _join(path, key), out)
        out.added.extend(_join(path, key) for key in b if key not in a)
        return
    if isinstance(a, list) and isinstance(b, list):
        ka, kb = _keyed(a), _keyed(b)
        if ka is not None and kb is not None:
            scalar = not any(isinstance(x, dict) for x in a + b)
            for label, item in ka.items():
                if label not in kb:
                    out.removed.append(f"{path}[{label}]")
                elif not scalar:
                    _diff(item, kb[label], f"{path}[{label}]", out)
            out.added.extend(f"{path}[{label}]" for label in kb if label not in ka)
            return
        for i in range(max(len(a), len(b))):
            if i >= len(a):
                out.added.append(f"{path}[{i}]")
            elif i >= len(b):
                out.removed.append(f"{path}[{i}]")
            else:
                _diff(a[i], b[i], f"{path}[{i}]", out)
        return
    if a != b:
        out.changed.append(FieldChange(path=path, before=a, after=b))
