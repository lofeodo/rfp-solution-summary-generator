"""Prompt loader: {{var}} rendering and hash recording."""

import hashlib

import pytest

from rfp_agent.llm import load_prompt
from rfp_agent.observability import RunRecorder

TEXT = 'Chunk {{chunk_id}}:\n{{ text }}\nReturn JSON like {"a": 1}.\n'


@pytest.fixture
def prompts_dir(tmp_path):
    (tmp_path / "demo.md").write_text(TEXT, encoding="utf-8", newline="\n")
    return tmp_path


def test_render_substitutes_and_keeps_single_braces(prompts_dir):
    p = load_prompt("demo", prompts_dir=prompts_dir)
    assert p.variables == {"chunk_id", "text"}
    out = p.render(chunk_id="S3.2", text="The vendor shall...")
    assert out == 'Chunk S3.2:\nThe vendor shall...\nReturn JSON like {"a": 1}.\n'


def test_missing_variable_raises(prompts_dir):
    with pytest.raises(KeyError, match="text"):
        load_prompt("demo", prompts_dir=prompts_dir).render(chunk_id="S1.1")


def test_unused_variable_raises(prompts_dir):
    with pytest.raises(ValueError, match="chunkid"):
        load_prompt("demo", prompts_dir=prompts_dir).render(chunk_id="S1.1", text="t", chunkid="x")


def test_hash_is_file_sha256_and_recorded(prompts_dir, tmp_path):
    expected = hashlib.sha256((prompts_dir / "demo.md").read_bytes()).hexdigest()
    rec = RunRecorder("a.pdf", "m:x", 0.0, runs_dir=tmp_path / "runs")
    with rec.activate(write=False):
        p = load_prompt("demo", prompts_dir=prompts_dir)
    assert p.sha256 == expected
    assert rec.log.prompt_hashes == {"demo": expected}


def test_missing_file_raises(prompts_dir):
    with pytest.raises(FileNotFoundError):
        load_prompt("nope", prompts_dir=prompts_dir)
