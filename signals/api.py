"""Serving. Two latency classes, deliberately separate.

  cached  -- GET /v1/signals/coffee          target p99 < 250ms
  fresh   -- POST /v1/refresh -> job id      minutes, runs the LLM

Mixing them is the classic mistake: one slow inference behind a synchronous
endpoint turns a sub-second SLO into a timeout during exactly the news storm
the system exists to handle.
"""
import json
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .store import connect, now, claims_as_of, docs_as_of
from .pipeline import score, run, SIGNALS

app = FastAPI(title="trading-agent", version="0.1.0",
              description="Coffee signals extracted from GDELT GKG by an LLM.")

# ponytail: unbounded dict. A caller sweeping as_of at second resolution would
# grow it without limit; cap it with an LRU when the API is exposed to anyone
# other than us.
_cache: dict[str, tuple[float, dict]] = {}
_stats = {"hits": 0, "misses": 0}
_jobs: dict[str, dict] = {}
TTL = 30.0
WEB = Path(__file__).resolve().parent.parent / "web"


def _norm(as_of: str | None) -> str | None:
    """A '+' in a query string decodes to a space, so `?as_of=...T00:00:00+00:00`
    arrives as '...T00:00:00 00:00'. Repair it rather than 500 -- callers paste
    ISO timestamps by hand constantly, and a stack trace is a poor answer."""
    if not as_of:
        return None
    v = as_of.strip()
    if len(v) > 6 and v[-6] == " " and v[-3] == ":":
        v = v[:-6] + "+" + v[-5:]
    try:
        datetime.fromisoformat(v)
    except ValueError:
        raise HTTPException(400, f"as_of must be ISO8601, got {as_of!r}")
    return v


def _novelty(conn, as_of=None) -> dict:
    return {r["doc_id"]: (r["novelty"] if r["novelty"] is not None else 1.0)
            for r in docs_as_of(conn, as_of)}


def _snapshot(as_of: str | None) -> dict:
    conn = connect()
    rows = claims_as_of(conn, as_of)
    docs = docs_as_of(conn, as_of)
    sig = score(rows, as_of, _novelty(conn, as_of))
    latest = max((r["event_time"] for r in rows), default=None)
    return {
        "commodity": "coffee",
        "as_of": as_of or now(),
        "point_in_time": bool(as_of),
        "signals": sig,
        "corpus": {
            "documents": len(docs),
            "clusters": len({d["cluster_id"] for d in docs if d["cluster_id"]}),
            "claims": len(rows),
            "latest_event": latest,
            # staleness is reported, never hidden. A caller acting on a signal
            # is entitled to know how old the newest evidence under it is.
            # Measured against the replay instant, not wall clock. Reporting
            # "9,108 minutes stale" for a historical replay is true of now and
            # meaningless of the replay.
            "staleness_minutes": round(
                ((datetime.fromisoformat(as_of) if as_of else datetime.now(timezone.utc))
                 - datetime.fromisoformat(latest)).total_seconds() / 60
            ) if latest else None,
        },
    }


@app.get("/healthz")
def healthz():
    return {"ok": True, "time": now()}


@app.get("/v1/signals/{commodity}")
def signals(commodity: str, as_of: str | None = Query(None, description="ISO8601; replays the world as known at that instant")):
    if commodity != "coffee":
        raise HTTPException(404, "only coffee is wired in this slice")
    as_of = _norm(as_of)
    key = as_of or "_live"
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < TTL:
        _stats["hits"] += 1
        return JSONResponse(hit[1], headers={"x-cache": "hit"})
    _stats["misses"] += 1
    snap = _snapshot(as_of)
    _cache[key] = (time.time(), snap)
    return JSONResponse(snap, headers={"x-cache": "miss"})


@app.get("/v1/signals/{commodity}/history")
def history(commodity: str, days: int = 7, step_hours: int = 6):
    """Rebuilds the series by replaying the second clock. Every point is what
    the system would have said then -- not today's claims back-dated, which is
    how most 'historical signal' charts quietly become lookahead."""
    conn = connect()
    rows = claims_as_of(conn, None)
    end = datetime.now(timezone.utc)
    out = []
    for i in range(int(days * 24 / step_hours), -1, -1):
        t = (end - timedelta(hours=i * step_hours)).isoformat(timespec="seconds")
        visible = [r for r in rows if r["ingest_time"] <= t]
        if not visible:
            continue
        # Novelty must be recomputed as of t. Using today's novelty back-dated a
        # weight that later documents determined -- a lookahead hiding inside a
        # correct-looking filter.
        out.append({"t": t, **{k: v["value"] for k, v in score(visible, t, _novelty(conn, t)).items()},
                    "claims": len(visible)})
    return {"commodity": commodity, "points": out}


@app.get("/v1/claims")
def claims(signal: str | None = None, as_of: str | None = None, limit: int = 50):
    """The evidence ledger. Every signal number upstream decomposes into these
    rows, and every row carries the verbatim span it was derived from."""
    if signal and signal not in SIGNALS:
        raise HTTPException(400, f"signal must be one of {SIGNALS}")
    as_of = _norm(as_of)
    conn = connect()
    rows = claims_as_of(conn, as_of, signal)[:limit]
    urls = {r["doc_id"]: r for r in docs_as_of(conn, as_of)}
    return {"count": len(rows), "claims": [{
        "claim_id": r["claim_id"], "signal": r["signal"],
        "direction": r["direction"], "magnitude": r["magnitude"],
        "confidence": r["confidence"], "horizon_days": r["horizon_days"],
        "driver": r["driver"], "region": r["region"], "contract": r["contract"],
        "evidence_quote": r["evidence_quote"],
        "injection_flag": bool(r["injection_flag"]),
        "event_time": r["event_time"], "ingest_time": r["ingest_time"],
        "extractor": r["extractor"],
        "source_url": urls[r["doc_id"]]["url"] if r["doc_id"] in urls else None,
        "source_title": urls[r["doc_id"]]["title"] if r["doc_id"] in urls else None,
        "novelty": urls[r["doc_id"]]["novelty"] if r["doc_id"] in urls else None,
    } for r in rows]}


def _worker(job_id: str, backend: str, batches: int):
    try:
        res = run(backend=backend, batches=batches)
        _jobs[job_id].update(status="done", finished=now(), detail=res)
        # Only the live key is mutable. A point-in-time read can never change --
        # no future write alters the past -- so clearing historical entries threw
        # away valid work and contradicted the design's own central claim.
        _cache.pop("_live", None)
    except Exception as e:
        _jobs[job_id].update(status="failed", finished=now(), detail={"error": str(e)[:400]})


@app.post("/v1/refresh")
def refresh(backend: str = "claude-cli", batches: int = 8):
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"job_id": job_id, "status": "running", "created": now(),
                     "finished": None, "detail": {"backend": backend}}
    threading.Thread(target=_worker, args=(job_id, backend, batches), daemon=True).start()
    return JSONResponse({"job_id": job_id, "status": "running",
                         "poll": f"/v1/jobs/{job_id}"}, status_code=202)


@app.get("/v1/jobs/{job_id}")
def job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "no such job")
    return _jobs[job_id]


@app.get("/v1/metrics")
def metrics():
    conn = connect()
    docs = docs_as_of(conn)
    rows = claims_as_of(conn)
    tot = _stats["hits"] + _stats["misses"]
    return {
        "cache": {**_stats, "hit_rate": round(_stats["hits"] / tot, 3) if tot else None},
        "corpus": {"documents": len(docs),
                   "clusters": len({d["cluster_id"] for d in docs if d["cluster_id"]}),
                   "dedup_ratio": round(1 - len({d["cluster_id"] for d in docs if d["cluster_id"]})
                                        / len(docs), 3) if docs else None,
                   "claims": len(rows),
                   "claims_flagged_injection": sum(1 for r in rows if r["injection_flag"])},
        "jobs": {"running": sum(1 for j in _jobs.values() if j["status"] == "running"),
                 "total": len(_jobs)},
    }


if WEB.exists():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
