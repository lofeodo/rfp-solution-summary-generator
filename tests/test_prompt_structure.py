"""Every prompt in ``prompts/`` follows the structure described in ``prompts/README.md``.

The structure is a fixed order of ``##`` headings: the instruction sections first
(Role, Task, Context, Output, Rules, optional Examples, Tone), then one heading per input
block, then Final checks. Placeholders live in the input blocks, except the few that code
splices into an instruction section (listed in ``INSTRUCTION_PLACEHOLDERS``). Code-built
input uses ``###`` headings, so prompts never do.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from rfp_agent.llm import PROMPTS_DIR, load_prompt

PROMPT_FILES = sorted(p.stem for p in PROMPTS_DIR.glob("*.md") if p.stem != "README")
LEADING = ["Role", "Task", "Context", "Output", "Rules"]
OPTIONAL_AFTER_RULES = "Examples"
TONE = "Tone"
FINAL = "Final checks"
INSTRUCTION_SECTIONS = {*LEADING, OPTIONAL_AFTER_RULES, TONE, FINAL}

# Placeholders that code splices into an instruction section rather than an input block.
INSTRUCTION_PLACEHOLDERS = {
    "requirements_extract": {"unit", "mode_rules"},  # agents/requirements.py
    "judge_pairwise": {"what"},  # evals/harness/pairwise.py
}

# The scripted judge in tests/test_harness.py recognises each judge prompt by one phrase.
JUDGE_PHRASES = {
    "judge_match": "against a gold standard",
    "judge_requirements": "grading the output of an automated requirements extractor",
    "judge_grounding": "check whether statements",
    "judge_checklist": "checklist of facts",
    "judge_solution": "review a proposed solution approach",
    "judge_risks": "review the risk register",
}

HEADING = re.compile(r"^(#+) (.*)$", re.M)
VAR = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


def headings(text: str) -> list[tuple[int, str]]:
    return [(len(m.group(1)), m.group(2).strip()) for m in HEADING.finditer(text)]


def sections(text: str) -> dict[str, str]:
    """Section title -> body, for ``##`` headings."""
    out: dict[str, str] = {}
    parts = re.split(r"^## (.*)$", text, flags=re.M)
    for title, body in zip(parts[1::2], parts[2::2], strict=True):
        out[title.strip()] = body
    return out


def test_every_prompt_is_listed():
    assert len(PROMPT_FILES) == 17


@pytest.mark.parametrize("name", PROMPT_FILES)
def test_heading_order(name: str):
    text = load_prompt(name).text
    hs = headings(text)
    assert all(level == 2 for level, _ in hs), f"{name}: only ## headings are allowed"
    titles = [t for _, t in hs]
    assert titles[: len(LEADING)] == LEADING, f"{name}: starts {titles[:5]}"
    rest = titles[len(LEADING) :]
    if rest and rest[0] == OPTIONAL_AFTER_RULES:
        rest = rest[1:]
    assert rest and rest[0] == TONE, f"{name}: Tone must follow Rules or Examples"
    inputs = rest[1:-1]
    assert inputs, f"{name}: needs at least one input block before Final checks"
    assert not INSTRUCTION_SECTIONS & set(inputs), f"{name}: reserved heading reused"
    assert rest[-1] == FINAL, f"{name}: must end with Final checks"
    assert len(titles) == len(set(titles)), f"{name}: duplicate heading"


@pytest.mark.parametrize("name", PROMPT_FILES)
def test_placeholders_live_in_input_blocks(name: str):
    text = load_prompt(name).text
    allowed = INSTRUCTION_PLACEHOLDERS.get(name, set())
    for title, body in sections(text).items():
        found = set(VAR.findall(body))
        if title in INSTRUCTION_SECTIONS:
            assert found <= allowed, f"{name}: {found - allowed} in section {title}"
        else:
            assert found, f"{name}: input block {title} has no placeholder"
    assert set(VAR.findall(text)) == load_prompt(name).variables


@pytest.mark.parametrize("name", PROMPT_FILES)
def test_sections_have_content(name: str):
    secs = sections(load_prompt(name).text)
    for title in (*LEADING, TONE, FINAL):
        assert secs[title].strip(), f"{name}: empty section {title}"
    rules = secs["Rules"]
    assert re.search(r"^- \*\*[^*]+\*\*", rules, re.M), f"{name}: rules are bold-named"
    assert "\n\n" not in secs["Role"].strip(), f"{name}: Role is one paragraph"
    assert "\n\n" not in secs["Task"].strip(), f"{name}: Task is one paragraph"


@pytest.mark.parametrize("name", PROMPT_FILES)
def test_lf_line_endings(name: str):
    assert b"\r" not in (PROMPTS_DIR / f"{name}.md").read_bytes()


@pytest.mark.parametrize(("name", "phrase"), sorted(JUDGE_PHRASES.items()))
def test_judge_recognition_phrase(name: str, phrase: str):
    task = sections(load_prompt(name).text)["Task"]
    assert phrase in task, f"{name}: the scripted judge looks for {phrase!r} in Task"
    for other, other_phrase in JUDGE_PHRASES.items():
        if other != name:
            assert other_phrase not in load_prompt(name).text


def test_shared_definitions_stay_aligned():
    """The risk scales and the requirement scope are shared between prompts (D31)."""
    risk = load_prompt("risk").text
    judge = load_prompt("judge_risks").text
    for line in (
        "`high`: the project fails, misses a contractual date, or overruns the budget by",
        "`medium`: material rework, a slip or a cost that contingency can absorb;",
        "`low`: handled in normal delivery;",
        "`high`: expected unless someone acts;",
        "`medium`: plausible; it turns on facts the RFP does not settle;",
        "`low`: needs an unusual event;",
    ):
        assert line in risk and line in judge, line
    scope = (
        "an obligation or constraint on the vendor, its\n  proposal, or its solution that "
        "would change how a competent bidder designs, staffs,\n  prices, schedules or "
        "submits its response."
    )
    assert scope in load_prompt("requirements_extract").text
    assert scope in load_prompt("gold_requirements").text


def test_readme_lists_every_prompt():
    readme = (Path(PROMPTS_DIR) / "README.md").read_text(encoding="utf-8")
    for name in PROMPT_FILES:
        assert f"`{name}.md`" in readme, name
