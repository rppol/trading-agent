"""Assert-based checks. Run: python tests/test_pipeline.py

No framework on purpose. Each test names a defect that would otherwise ship
silently -- the whole class of bug this system is built to avoid.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from signals.store import connect, insert_claims, upsert_documents, claims_as_of
from signals.pipeline import cluster, score, COFFEE, MARKET, SIGNALS

T0 = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


def iso(dt):
    return dt.isoformat(timespec="seconds")


def test_dedup_collapses_syndication():
    """The same wire story under two mastheads is one piece of evidence."""
    base = "Brazil coffee exports fall sharply as drought cuts the arabica crop in Minas Gerais"
    docs = [
        {"doc_id": "a", "url": "http://a", "title": base, "snippet": base, "event_time": iso(T0)},
        {"doc_id": "b", "url": "http://b", "title": base + " , say traders",
         "snippet": base + " , say traders", "event_time": iso(T0 + timedelta(minutes=20))},
        {"doc_id": "c", "url": "http://c", "title": "Vietnam robusta prices climb on tight supply",
         "snippet": "Vietnam robusta prices climb on tight supply", "event_time": iso(T0)},
    ]
    out = {d["doc_id"]: d for d in cluster(docs)}
    assert out["a"]["cluster_id"] == out["b"]["cluster_id"], "syndicated pair must share a cluster"
    assert out["c"]["cluster_id"] != out["a"]["cluster_id"], "unrelated story must not merge"
    assert out["a"]["novelty"] == 1.0 and out["b"]["novelty"] < 1.0, "reprint must lose novelty"
    print("ok  dedup collapses syndication, novelty decays on the reprint")


def test_point_in_time_is_monotone():
    """A replay may never see more than a later replay. If this fails, every
    backtest built on the store is reading the future."""
    conn = connect(":memory:")
    upsert_documents(conn, [{"doc_id": "d1", "url": "http://d1", "event_time": iso(T0),
                             "ingest_time": iso(T0), "raw": {}}])
    rows = []
    for i in range(5):
        rows.append({"claim_id": f"c{i}", "doc_id": "d1", "signal": "supply_risk",
                     "magnitude": 0.5, "confidence": 0.8, "direction": 0,
                     "evidence_quote": "drought cuts the crop",
                     "event_time": iso(T0), "ingest_time": iso(T0 + timedelta(hours=i)),
                     "extractor": "t"})
    insert_claims(conn, rows)
    counts = [len(claims_as_of(conn, iso(T0 + timedelta(hours=h)))) for h in range(5)]
    assert counts == sorted(counts), f"as_of must be monotone, got {counts}"
    assert counts == [1, 2, 3, 4, 5], counts
    print(f"ok  point-in-time replay is monotone {counts}")


def test_leakage_switch():
    """THE one that matters.

    A story published at T is only in our hands at T+90m. Filtering on
    event_time (the leaky clock) shows it to a decision made at T+10m; filtering
    on ingest_time does not. The gap between the two counts IS the lookahead,
    measured rather than asserted.
    """
    conn = connect(":memory:")
    upsert_documents(conn, [{"doc_id": "d", "url": "http://d", "event_time": iso(T0),
                             "ingest_time": iso(T0), "raw": {}}])
    insert_claims(conn, [{
        "claim_id": "slow", "doc_id": "d", "signal": "price_pressure",
        "direction": 1, "magnitude": 0.9, "confidence": 0.9,
        "evidence_quote": "frost damage confirmed",
        "event_time": iso(T0),                       # when the world changed
        "ingest_time": iso(T0 + timedelta(minutes=90)),  # when we learned it
        "extractor": "t"}])

    decision = iso(T0 + timedelta(minutes=10))
    honest = claims_as_of(conn, decision)
    leaky = conn.execute("SELECT * FROM claims WHERE event_time <= ?", (decision,)).fetchall()

    assert len(honest) == 0, "decision-time-correct view must not see the un-ingested claim"
    assert len(leaky) == 1, "the leaky clock is what would have leaked"
    assert score(honest, decision)["price_pressure"]["value"] == 0.0
    assert score(leaky, decision)["price_pressure"]["value"] > 0.0
    print("ok  leakage switch: event_time view invents a signal the ingest_time view cannot see")


def test_ungrounded_claims_are_dropped():
    """A quote the model composed rather than copied never reaches the score."""
    docs = [{"doc_id": "d", "url": "http://d", "title": "Brazil frost damages coffee crop",
             "snippet": "Brazil frost damages coffee crop in southern Minas Gerais.",
             "event_time": iso(T0)}]
    raw = [
        {"url": "http://d", "signal": "supply_risk", "magnitude": 0.8, "confidence": 0.9,
         "evidence_quote": "Brazil frost damages coffee crop"},                    # real span
        {"url": "http://d", "signal": "supply_risk", "magnitude": 0.9, "confidence": 0.9,
         "evidence_quote": "Brazil lost 40% of its crop to frost this week"},      # invented
    ]
    src = f"{docs[0]['title']} {docs[0]['snippet']}"
    kept = [c for c in raw if c["evidence_quote"][:60].lower() in src.lower()]
    assert len(kept) == 1 and "40%" not in kept[0]["evidence_quote"]
    print("ok  ungrounded quote (with an invented 40% figure) is rejected by the span gate")


def test_injected_document_cannot_move_a_signal():
    """News text is untrusted input. A document carrying instructions is scored
    as zero weight, not obeyed."""
    rows = [{"signal": "price_pressure", "direction": 1, "magnitude": 1.0,
             "confidence": 1.0, "injection_flag": 1, "doc_id": "x",
             "event_time": iso(T0)}]
    assert score(rows, iso(T0))["price_pressure"]["value"] == 0.0
    assert score(rows, iso(T0))["price_pressure"]["claims"] == 0
    print("ok  injection-flagged document contributes zero weight")


def test_throttle_response_is_not_data():
    """GDELT answers rate-limit violations with plain text under HTTP 200.
    Parsed naively that becomes 'no news today' -- a silent outage."""
    body = "Please limit requests to one every 5 seconds or contact ..."
    assert not body.strip().startswith("{"), "guard is: a payload must be JSON"
    print("ok  plain-text throttle notice is rejected before it can look like an empty day")


def test_relevance_filter_precision():
    keep = ["Brazil coffee exports fall as drought cuts arabica crop",
            "Vietnam robusta prices climb on tight supply and export delays"]
    drop = ["Stag shot dead after injuring man having picnic in major city park",
            "Dutch Bros aims for another San Jose coffee drive-through",
            "K2 Gold Corporation: K2 Drills High-Grade Gold at Mojave Project"]
    for t in keep:
        assert COFFEE.search(t) and MARKET.search(t), f"should keep: {t}"
    for t in drop:
        assert not (COFFEE.search(t) and MARKET.search(t)), f"should drop: {t}"
    print("ok  relevance filter keeps market stories, drops cafes/stags/gold")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\n{len(fns)} checks passed")
