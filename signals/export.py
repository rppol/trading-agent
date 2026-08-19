"""Emit the static JSON the site reads.

The site recomputes signal values in the browser from raw claims rather than
consuming a precomputed number. That is deliberate: it lets the leakage switch
re-score under either clock live, which is the one argument in this project that
is far more convincing shown than described.
"""
import json
from pathlib import Path

from .store import connect, claims_as_of, docs_as_of
from .pipeline import SIGNALS, EXTRACTOR, HALFLIFE_D

OUT = Path(__file__).resolve().parent.parent / "web" / "data"


def main() -> dict:
    conn = connect()
    docs = docs_as_of(conn)
    rows = claims_as_of(conn)
    OUT.mkdir(parents=True, exist_ok=True)

    dmap = {d["doc_id"]: d for d in docs}
    claims = [{
        "claim_id": r["claim_id"], "signal": r["signal"], "direction": r["direction"],
        "magnitude": r["magnitude"], "confidence": r["confidence"],
        "horizon_days": r["horizon_days"], "driver": r["driver"], "region": r["region"],
        "contract": r["contract"], "evidence_quote": r["evidence_quote"],
        "injection_flag": bool(r["injection_flag"]),
        "event_time": r["event_time"], "ingest_time": r["ingest_time"],
        "extractor": r["extractor"],
        "source_url": dmap[r["doc_id"]]["url"] if r["doc_id"] in dmap else None,
        "source_title": dmap[r["doc_id"]]["title"] if r["doc_id"] in dmap else None,
        "domain": dmap[r["doc_id"]]["domain"] if r["doc_id"] in dmap else None,
        "novelty": dmap[r["doc_id"]]["novelty"] if r["doc_id"] in dmap else 1.0,
    } for r in rows]

    clusters = {d["cluster_id"] for d in docs if d["cluster_id"]}
    meta = {
        "generated": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        "extractor": EXTRACTOR,
        "halflife_days": HALFLIFE_D,
        "signals": list(SIGNALS),
        "corpus": {
            "documents": len(docs),
            "clusters": len(clusters),
            "dedup_ratio": round(1 - len(clusters) / len(docs), 3) if docs else 0,
            "claims": len(claims),
            "window_start": min((d["event_time"] for d in docs), default=None),
            "window_end": max((d["event_time"] for d in docs), default=None),
            "languages": sorted({d["language"] for d in docs if d["language"]}),
        },
        # Measured across the full 673-batch corpus, not extrapolated from a sample.
        # An earlier version quoted 1550 docs/batch from a single observation; the
        # true distribution is mean 1004, median 946, range 314-2189.
        "funnel": {"docs_per_day": 96405, "coffee_in_title_per_day": 88.3,
                   "tradeable_per_day": 4.7, "cheap_filter_removes_pct": 95,
                   "docs_per_batch_mean": 1004, "docs_per_batch_median": 946},
    }
    (OUT / "claims.json").write_text(json.dumps(claims, separators=(",", ":")))
    (OUT / "docs.json").write_text(json.dumps([{
        "doc_id": d["doc_id"], "title": d["title"], "url": d["url"], "domain": d["domain"],
        "language": d["language"], "region": d["source_country"],
        "cluster_id": d["cluster_id"], "novelty": d["novelty"],
        "event_time": d["event_time"], "ingest_time": d["ingest_time"],
    } for d in docs], separators=(",", ":")))
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
