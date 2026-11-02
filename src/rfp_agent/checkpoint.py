"""The checkpoint (ST12a): apply a reviewer's decisions to the extracted requirements.

Pure code, no LLM. The reviewer's row actions are deterministic (accept, reject, change
strictness or type), so they are applied here and validated here; the backend calls
``apply_checkpoint`` before it resumes a run, so a bad record is refused with a message
instead of failing inside the pipeline. Anything that produces new text (merge, split,
add) goes through the model with the extractor's validators in ST12b.
"""

from __future__ import annotations

from rfp_agent.schemas import (
    CheckpointRecord,
    DecisionAction,
    RequirementOrigin,
    RequirementsOutput,
)

CHECKPOINT_FILENAME = "checkpoint.json"
CONFIRMED_REQUIREMENTS_FILENAME = "requirements_confirmed.json"


class CheckpointError(ValueError):
    """The record refers to requirements that do not exist, or contradicts itself."""


def validate_checkpoint(requirements: RequirementsOutput, record: CheckpointRecord) -> list[str]:
    """Every problem with ``record`` against ``requirements``, in decision order."""
    known = set(requirements.requirement_ids())
    problems: list[str] = []
    seen: set[str] = set()
    for d in record.decisions:
        rid = d.requirement_id
        if rid not in known:
            problems.append(f"{rid}: no such requirement")
        if rid in seen:
            problems.append(f"{rid}: more than one decision")
        seen.add(rid)
        if d.action is DecisionAction.REJECT and (d.strictness is not None or d.type is not None):
            problems.append(f"{rid}: a rejected requirement cannot also be edited")
    return problems


def apply_checkpoint(
    requirements: RequirementsOutput, record: CheckpointRecord
) -> RequirementsOutput:
    """The confirmed requirement list: rejected requirements removed (and their IDs
    stripped from ``conflicts_with`` and ambiguity ``requirement_ids`` so no citation
    dangles), strictness and type changes applied with ``origin = reviewed``.

    Raises ``CheckpointError`` naming every problem when the record does not fit.
    """
    problems = validate_checkpoint(requirements, record)
    if problems:
        raise CheckpointError("; ".join(problems))
    by_id = {d.requirement_id: d for d in record.decisions}
    rejected = set(record.rejected_ids())
    kept = []
    for r in requirements.requirements:
        if r.id in rejected:
            continue
        updates: dict[str, object] = {}
        d = by_id.get(r.id)
        if d is not None:
            if d.strictness is not None and d.strictness is not r.strictness:
                updates["strictness"] = d.strictness
            if d.type is not None and d.type is not r.type:
                updates["type"] = d.type
            if updates:
                updates["origin"] = RequirementOrigin.REVIEWED
        if rejected & set(r.conflicts_with):
            updates["conflicts_with"] = [c for c in r.conflicts_with if c not in rejected]
        kept.append(r.model_copy(update=updates) if updates else r)
    ambiguities = [
        a.model_copy(
            update={"requirement_ids": [i for i in a.requirement_ids if i not in rejected]}
        )
        if rejected & set(a.requirement_ids)
        else a
        for a in requirements.ambiguities
    ]
    return requirements.model_copy(update={"requirements": kept, "ambiguities": ambiguities})
