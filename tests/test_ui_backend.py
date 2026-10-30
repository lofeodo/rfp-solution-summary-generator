"""UI backend (S14) through FastAPI's TestClient. No network: the five LLM stages are
stubbed (``pipeline_stubs``), parsing and splitting run for real on Federal Way.

TestClient buffers a response body before returning it, so an SSE request returns only
once the stream closes, i.e. once the run has ended. Tests that need a run to stay open
hold it at a gate inside the quality-pass stub.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import ui.backend.__main__ as main_mod
import ui.backend.app as app_mod
from fakes import ScriptedChatModel
from pipeline_stubs import PDF, SETTINGS, Stubs
from rfp_agent.graph import SOLUTION, STAGES, StageEvent, run_pipeline
from rfp_agent.schemas import SplitDocument
from ui.backend.app import create_app
from ui.backend.models import ARTIFACTS
from ui.backend.runs import RunEntry

PDF_BYTES = PDF.read_bytes()
TIMEOUT = 60


# --------------------------------------------------------------------------------------
# Fixtures and helpers
# --------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def samples_dir(tmp_path_factory, chunk_id) -> Path:
    """A samples directory holding one finished stubbed run named ``sample1``."""
    root = tmp_path_factory.mktemp("samples")
    with pytest.MonkeyPatch.context() as mp:
        Stubs(chunk_id).install(mp)
        run_pipeline(
            PDF, settings=SETTINGS, model=ScriptedChatModel(), runs_dir=root, run_id="sample1"
        )
    return root


@pytest.fixture
def make_client(tmp_path, monkeypatch, chunk_id, samples_dir):
    """Factory: install stubs (or the given ones), build the app on temp dirs, return a
    started TestClient. Clients are closed at teardown."""
    clients: list[TestClient] = []

    def make(stubs: Stubs | None = None, *, fake_model: bool = True, **kwargs) -> TestClient:
        (stubs or Stubs(chunk_id)).install(monkeypatch)
        if fake_model:
            monkeypatch.setattr("ui.backend.runs.get_chat_model", lambda **kw: ScriptedChatModel())
        kwargs.setdefault("runs_dir", tmp_path / "runs")
        kwargs.setdefault("samples_dir", samples_dir)
        kwargs.setdefault("settings", SETTINGS)
        kwargs.setdefault("frontend_dist", None)
        client = TestClient(create_app(**kwargs))
        client.__enter__()
        clients.append(client)
        return client

    yield make
    for c in clients:
        c.__exit__(None, None, None)


def upload(client: TestClient, content: bytes = PDF_BYTES, name="federal_way.pdf", **form):
    return client.post(
        "/api/runs",
        files={"file": (name, content, "application/pdf")},
        data={k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in form.items()},
    )


def entry_of(client: TestClient, run_id: str) -> RunEntry:
    entry = client.app.state.registry.get(run_id)
    assert entry is not None
    return entry


def run_to_end(client: TestClient, **form) -> str:
    r = upload(client, **form)
    assert r.status_code == 202, r.text
    run_id = r.json()["run_id"]
    assert entry_of(client, run_id).wait_terminal(TIMEOUT)
    return run_id


def parse_sse(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.split("\n\n"):
        lines = [ln for ln in block.splitlines() if ln and not ln.startswith(":")]
        if not lines:
            continue
        fields = dict(ln.split(": ", 1) for ln in lines)
        out.append((fields["event"], json.loads(fields["data"])))
    return out


class Gate:
    """Holds a run inside its quality-pass stage until ``open()``."""

    def __init__(self, stubs: Stubs):
        self.entered = threading.Event()
        self.release = threading.Event()
        inner = stubs.run_quality_pass

        def gated(*args, **kwargs):
            self.entered.set()
            assert self.release.wait(TIMEOUT)
            return inner(*args, **kwargs)

        stubs.run_quality_pass = gated

    def open(self) -> None:
        self.release.set()


# --------------------------------------------------------------------------------------
# A whole run through the API
# --------------------------------------------------------------------------------------


def test_health(make_client):
    r = make_client().get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["model"] == SETTINGS.model


def test_upload_runs_and_serves_every_output(make_client, chunk_id):
    client = make_client()
    r = upload(client)
    assert r.status_code == 202
    assert r.json()["status"] in ("queued", "running")
    run_id = r.json()["run_id"]
    assert entry_of(client, run_id).wait_terminal(TIMEOUT)

    status = client.get(f"/api/runs/{run_id}").json()
    assert status["status"] == "finished", status["error"]
    assert status["source_name"] == "federal_way.pdf"
    assert status["model"] == SETTINGS.model
    assert [s["stage"] for s in status["stages"]] == list(STAGES)
    assert {s["status"] for s in status["stages"]} == {"finished"}
    assert status["artifacts"] == list(ARTIFACTS)
    assert status["totals"]["cost_usd"] > 0
    assert len(status["nodes"]) == 6  # stubbed LLM calls
    solution = next(s for s in status["stages"] if s["stage"] == SOLUTION)
    assert solution["calls"] == 1

    for name in ARTIFACTS:
        a = client.get(f"/api/runs/{run_id}/artifacts/{name}")
        assert a.status_code == 200, name
        assert a.headers["content-type"].startswith("application/json")
        assert isinstance(a.json(), dict)
    summary = client.get(f"/api/runs/{run_id}/artifacts/summary").json()
    assert summary["run_id"] == run_id

    md = client.get(f"/api/runs/{run_id}/summary.md")
    assert md.headers["content-type"].startswith("text/markdown")
    assert "Portal" in md.text

    for name in ("summary.json", "summary.md"):
        d = client.get(f"/api/runs/{run_id}/download/{name}")
        assert d.status_code == 200
        assert d.headers["content-disposition"].startswith("attachment")
        assert f"{run_id}-{name}" in d.headers["content-disposition"]

    pdf = client.get(f"/api/runs/{run_id}/source.pdf")
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content == PDF_BYTES

    split = SplitDocument.model_validate(client.get(f"/api/runs/{run_id}/artifacts/split").json())
    chunks = client.get(f"/api/runs/{run_id}/chunks").json()
    assert len(chunks) == len(split.chunks())
    c = client.get(f"/api/runs/{run_id}/chunks/{chunk_id}").json()
    assert c["id"] == chunk_id
    assert c["text"] == split.chunk_by_id(chunk_id).text
    assert c["page_start"] >= 1


def test_form_options_reach_the_pipeline(make_client, chunk_id):
    stubs = Stubs(chunk_id)
    client = make_client(stubs)
    run_id = run_to_end(
        client,
        model="deepseek:deepseek-other",
        full_text_problem=True,
        single_call_extraction=True,
        max_iterations=2,
    )
    assert stubs.calls["problem"]["full_text"] is True
    assert stubs.calls["requirements"]["single_call"] is True
    assert stubs.calls["solution"]["max_iterations"] == 2
    assert stubs.calls["parse_quality"]["settings"].model == "deepseek:deepseek-other"
    assert client.get(f"/api/runs/{run_id}").json()["model"] == "deepseek:deepseek-other"
    meta = json.loads((client.app.state.store.runs_dir / run_id / "upload.json").read_text())
    assert meta["options"]["max_iterations"] == 2


def test_events_replay_after_the_run(make_client):
    client = make_client()
    run_id = run_to_end(client)
    r = client.get(f"/api/runs/{run_id}/events")
    assert r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    kinds = [k for k, _ in events]
    assert kinds == ["stage"] * 16 + ["done"]
    stages = [StageEvent.model_validate(d) for k, d in events if k == "stage"]
    assert sorted(e.stage for e in stages if e.status == "started") == sorted(STAGES)
    assert sorted(e.stage for e in stages if e.status == "finished") == sorted(STAGES)
    assert events[-1][1] == {"status": "finished", "error": None}


def test_events_stream_live_while_the_run_is_in_flight(make_client, chunk_id):
    stubs = Stubs(chunk_id)
    gate = Gate(stubs)
    client = make_client(stubs)
    run_id = upload(client).json()["run_id"]
    assert gate.entered.wait(TIMEOUT)

    # Mid-run status: parse finished, quality pass started, nothing after it.
    status = client.get(f"/api/runs/{run_id}").json()
    assert status["status"] == "running"
    assert [(s["stage"], s["status"]) for s in status["stages"]] == [
        ("parse", "finished"),
        ("parse_quality", "started"),
    ]
    assert "parsed" in status["artifacts"] and "split" not in status["artifacts"]
    assert client.get(f"/api/runs/{run_id}/chunks").status_code == 404  # no split yet
    listed = {i["run_id"]: i for i in client.get("/api/runs").json()}
    assert listed[run_id]["status"] == "running"

    # Subscribe while running, then let the run go: the stream delivers the replayed
    # events and the live ones, and closes on "done".
    body: list[str] = []
    reader = threading.Thread(
        target=lambda: body.append(client.get(f"/api/runs/{run_id}/events").text)
    )
    reader.start()
    gate.open()
    reader.join(TIMEOUT)
    assert not reader.is_alive()
    events = parse_sse(body[0])
    assert [k for k, _ in events] == ["stage"] * 16 + ["done"]
    assert events[-1][1]["status"] == "finished"


def test_entry_wait_delivers_incrementally_and_flags_the_end():
    from datetime import UTC, datetime

    entry = RunEntry("r", "x.pdf", Path("x.pdf"), datetime.now(UTC), "m")
    assert entry.wait(0, 0.05) == ([], False)  # idle: the caller sends a keepalive

    def produce():
        for stage in ("parse", "split", "assemble"):
            entry.on_event(StageEvent(stage=stage, status="finished", started_at=datetime.now(UTC)))
        entry.set_status("finished")

    seen: list[str] = []
    cursor, terminal = 0, False
    t = threading.Thread(target=produce)
    t.start()
    while not terminal:
        new, terminal = entry.wait(cursor, 5)
        seen += [e.stage for e in new]
        cursor += len(new)
    t.join()
    assert seen == ["parse", "split", "assemble"]
    assert entry.wait(cursor, 0.01) == ([], True)
    assert [e.stage for e in entry.stages_so_far()] == ["parse", "split", "assemble"]


# --------------------------------------------------------------------------------------
# Failure, queueing, listing
# --------------------------------------------------------------------------------------


def test_failed_stage_keeps_earlier_outputs(make_client, chunk_id):
    client = make_client(Stubs(chunk_id, fail_at=SOLUTION))
    run_id = run_to_end(client)
    status = client.get(f"/api/runs/{run_id}").json()
    assert status["status"] == "failed"
    assert "solution boom" in status["error"]
    by_stage = {s["stage"]: s["status"] for s in status["stages"]}
    assert by_stage["solution"] == "failed"
    assert "risk" not in by_stage
    assert {"parsed", "split", "requirements", "problem", "run_log"} <= set(status["artifacts"])
    assert "solution" not in status["artifacts"] and "summary" not in status["artifacts"]
    assert client.get(f"/api/runs/{run_id}/artifacts/summary").status_code == 404
    assert client.get(f"/api/runs/{run_id}/summary.md").status_code == 404
    assert client.get(f"/api/runs/{run_id}/download/summary.md").status_code == 404
    events = parse_sse(client.get(f"/api/runs/{run_id}/events").text)
    assert events[-1][0] == "done" and events[-1][1]["status"] == "failed"
    listed = {i["run_id"]: i for i in client.get("/api/runs").json()}
    assert listed[run_id]["status"] == "failed"


def test_one_run_at_a_time(make_client, chunk_id):
    stubs = Stubs(chunk_id)
    gate = Gate(stubs)
    client = make_client(stubs)
    first = upload(client).json()["run_id"]
    assert gate.entered.wait(TIMEOUT)
    second = upload(client).json()
    assert second["status"] == "queued"
    assert client.get(f"/api/runs/{second['run_id']}").json()["status"] == "queued"
    assert client.get(f"/api/runs/{first}").json()["status"] == "running"
    gate.open()
    for run_id in (first, second["run_id"]):
        assert entry_of(client, run_id).wait_terminal(TIMEOUT)
        assert client.get(f"/api/runs/{run_id}").json()["status"] == "finished"


def test_listing_merges_live_runs_disk_runs_and_samples(make_client, tmp_path):
    client = make_client()
    run_id = run_to_end(client)
    (tmp_path / "runs" / "interrupted").mkdir()  # no log, no live run: not listed
    items = client.get("/api/runs").json()
    ids = [i["run_id"] for i in items]
    assert ids == [run_id, "sample1"]  # own runs first, samples last
    live, sample = items
    assert live["sample"] is False and live["source_name"] == "federal_way.pdf"
    assert sample["sample"] is True and sample["status"] == "finished"
    assert sample["source_name"] == "federal_way.pdf"
    assert sample["stages_done"] == len(STAGES)
    assert sample["cost_usd"] > 0 and sample["latency_s"] > 0

    # A fresh process (new app on the same dirs) still serves the finished run from disk.
    fresh = make_client()
    status = fresh.get(f"/api/runs/{run_id}").json()
    assert status["status"] == "finished" and len(status["nodes"]) == 6
    events = parse_sse(fresh.get(f"/api/runs/{run_id}/events").text)
    assert [k for k, _ in events] == ["stage"] * 8 + ["done"]  # finished records only

    interrupted = fresh.get("/api/runs/interrupted").json()
    assert interrupted["status"] == "failed" and "interrupted" in interrupted["error"]


def test_sample_runs_serve_their_source_pdf_from_the_repo(make_client, chunk_id):
    client = make_client()
    status = client.get("/api/runs/sample1").json()
    assert status["status"] == "finished" and status["sample"] is True
    assert client.get("/api/runs/sample1/source.pdf").content == PDF_BYTES
    assert client.get(f"/api/runs/sample1/chunks/{chunk_id}").status_code == 200


def test_sample_source_outside_the_repo_is_not_served(make_client, tmp_path, samples_dir):
    import shutil

    other = tmp_path / "samples2"
    shutil.copytree(samples_dir / "sample1", other / "evil")
    log_path = other / "evil" / "run_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8"))
    log["source_path"] = "../../../../etc/passwd.pdf"
    log_path.write_text(json.dumps(log), encoding="utf-8")
    client = make_client(samples_dir=other)
    assert client.get("/api/runs/evil").json()["status"] == "finished"
    assert client.get("/api/runs/evil/source.pdf").status_code == 404


# --------------------------------------------------------------------------------------
# Bad input and configuration
# --------------------------------------------------------------------------------------


def test_bad_uploads_are_rejected_and_leave_nothing(make_client, monkeypatch, tmp_path):
    client = make_client()
    runs = tmp_path / "runs"
    assert upload(client, content=b"hello, not a pdf").status_code == 400
    assert upload(client, content=b"").status_code == 400
    monkeypatch.setattr(app_mod, "MAX_UPLOAD_BYTES", 1000)
    assert upload(client).status_code == 413
    monkeypatch.setattr(app_mod, "MAX_UPLOAD_BYTES", 50 * 1024 * 1024)
    assert upload(client, max_iterations=0).status_code == 422
    assert client.post("/api/runs").status_code == 422  # no file
    assert not any(runs.iterdir()) if runs.exists() else True
    assert [i["run_id"] for i in client.get("/api/runs").json()] == ["sample1"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/runs/nope",
        "/api/runs/..%2F..%2Fdocs",
        "/api/runs/.hidden",
        "/api/runs/sample1/artifacts/nope",
        "/api/runs/sample1/artifacts/..%2Frun_log",
        "/api/runs/sample1/download/run_log.json",
        "/api/runs/sample1/chunks/S999.1",
        "/api/runs/sample1/chunks/not-a-chunk",
        "/api/runs/nope/events",
    ],
)
def test_unknown_things_are_404(make_client, path):
    assert make_client().get(path).status_code == 404


def test_missing_provider_key_is_503_before_anything_is_written(make_client, tmp_path):
    no_key = SETTINGS.model_copy(update={"deepseek_api_key": None})
    client = make_client(fake_model=False, settings=no_key)
    r = upload(client)
    assert r.status_code == 503
    assert "DEEPSEEK_API_KEY" in r.json()["detail"]
    runs = tmp_path / "runs"
    assert not runs.exists() or not any(runs.iterdir())


def test_unknown_provider_is_400(make_client):
    client = make_client(fake_model=False)
    r = upload(client, model="nosuchprovider:some-model")
    assert r.status_code == 400
    assert "cannot build model" in r.json()["detail"]


def test_cors_allows_the_vite_dev_server(make_client):
    r = make_client().get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


# --------------------------------------------------------------------------------------
# Frontend serving and entry point
# --------------------------------------------------------------------------------------


def test_built_frontend_is_served_with_spa_fallback(make_client, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (dist / "assets" / "a.js").write_text("console.log(1)", encoding="utf-8")
    client = make_client(frontend_dist=dist)
    assert client.get("/").text == "<html>app</html>"
    assert client.get("/runs/abc").text == "<html>app</html>"
    assert client.get("/assets/a.js").text == "console.log(1)"
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api/health").json()["status"] == "ok"


def test_no_frontend_routes_without_a_build(make_client, tmp_path):
    client = make_client(frontend_dist=tmp_path / "missing")
    assert client.get("/").status_code == 404


def test_main_passes_options_to_uvicorn(monkeypatch):
    seen = {}
    monkeypatch.setattr(main_mod.uvicorn, "run", lambda app, **kw: seen.update(app=app, **kw))
    main_mod.main(["--port", "9001", "--reload"])
    assert seen == {
        "app": "ui.backend.app:create_app",
        "factory": True,
        "host": "127.0.0.1",
        "port": 9001,
        "reload": True,
    }
