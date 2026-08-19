"""Assert-based checks. Run: python tests/test_pipeline.py

Every test here calls PRODUCTION code. An earlier version of this file
reimplemented the grounding gate inline and asserted against its own copy, which
meant the one test aimed at the gate was structurally incapable of failing --
and that is exactly why a gate that did not exist shipped as documented.
A test that cannot contradict the prose is not a test.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from signals.store import connect, insert_claims, upsert_documents, claims_as_of
from signals import pipeline as P

T0 = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
iso = lambda dt: dt.isoformat(timespec="seconds")


def _doc(**kw):
    d = {"doc_id": "d", "url": "http://d", "title": "Brazil frost damages coffee crop",
         "snippet": "Brazil frost damages coffee crop in southern Minas Gerais. "
                    "Exports fell 12,500 tonnes in July.",
         "event_time": iso(T0), "ingest_time": iso(T0), "raw": {}}
    d.update(kw)
    return d


# ---------------------------------------------------------------- grounding

def test_span_gate_rejects_fabricated_continuation():
    """The gate used to compare only the first 60 characters of a quote stored to
    300, so a real opening followed by invention passed and was DISPLAYED as
    verbatim evidence. This asserts the whole span is checked."""
    src = _doc()["snippet"]
    real = "Brazil frost damages coffee crop in southern Minas Gerais."
    assert P.ground(real, src)[0], "a genuine span must pass"

    # 60 real characters, then fabrication
    hybrid = real[:60] + " and 62% of the national crop was destroyed."
    assert len(hybrid) > 60
    assert not P.ground(hybrid, src)[0], "fabricated continuation must be rejected"
    print("ok  span gate checks the whole quote, not a 60-char prefix")


def test_number_gate_actually_exists():
    """This is the regression test for the worst defect in the project: the number
    check was `_numbers(...) or True`, which is unconditionally true. It was
    asserted in three places across two documents and did not exist."""
    src = _doc()["snippet"]
    ok_span, ok_nums = P.ground("Exports fell 12,500 tonnes in July.", src)
    assert ok_span and ok_nums, "a real figure present in the source must pass"

    # the number check must be capable of returning False on its own
    span, nums = P.ground("Exports fell 12,500 tonnes in July.", "Exports fell in July.")
    assert not nums, "a figure absent from the source must fail the NUMBER check"
    assert P.ground("", src) == (False, False)
    print("ok  number gate is real (and can return False, which it could not before)")


def test_grounding_survives_unicode():
    """Normalisation is most of the gate's work. Without it a correct quote from a
    PDF-derived source is rejected, which presents as a quality problem."""
    src = "Conab — Brazil’s crop agency — raised its estimate to 55.2 million bags."
    quote = 'Conab - Brazil\'s crop agency - raised its estimate to 55.2 million bags.'
    assert P.ground(quote, src)[0], "smart quotes/dashes/nbsp must not reject a correct span"
    print("ok  grounding normalises unicode before comparing")


# ---------------------------------------------------------------- extraction path

def test_extract_end_to_end_enforces_both_gates():
    """Exercises the real extract(), not a copy of its logic."""
    docs = [_doc()]
    raw = [
        {"url": "http://d", "signal": "supply_risk", "magnitude": 0.8,
         "source_hedging": 0.9, "balance_effect": "tighter",
         "evidence_quote": "Brazil frost damages coffee crop"},                 # good
        {"url": "http://d", "signal": "supply_risk", "magnitude": 0.9,
         "source_hedging": 0.9, "balance_effect": "tighter",
         "evidence_quote": "Brazil lost 40% of its crop to frost this week"},   # invented
        {"url": "http://d", "signal": "supply_risk", "magnitude": 0.9,
         "source_hedging": 0.9, "balance_effect": "tighter",
         "evidence_quote": "Exports fell 99,999 tonnes in July."},              # real shape, fake number
    ]
    orig = P._parse_array
    P._parse_array = lambda _t: raw
    orig_claude = P._claude
    P._claude = lambda prompt, model="sonnet": ("", {"usd": 0.0, "in": 0, "out": 0})
    try:
        claims, _ = P.extract(docs, backend="claude-cli")
    finally:
        P._parse_array, P._claude = orig, orig_claude

    quotes = [c["evidence_quote"] for c in claims]
    assert len(claims) == 1, f"only the grounded claim should survive, got {quotes}"
    assert "40%" not in quotes[0], "invented span must be rejected"
    assert "99,999" not in quotes[0], "invented NUMBER must be rejected"
    assert all(c["verified_number"] == 1 for c in claims)
    print("ok  extract() rejects both a fabricated span and a fabricated number")


def test_direction_is_computed_not_extracted():
    """The design's load-bearing principle is that the model never emits a price
    direction. It previously did, and the value was multiplied into the signal."""
    assert '"direction"' not in P.PROMPT, "the prompt must not ask for a direction FIELD"
    assert '"balance_effect"' in P.PROMPT, "it must ask for a physical balance fact instead"
    assert "Never state a price direction" in P.PROMPT, "and must say so explicitly"
    assert P.BALANCE_SIGN["tighter"] == 1 and P.BALANCE_SIGN["looser"] == -1
    print("ok  price direction is derived from a stated physical fact, not extracted")


def test_replay_backend_returns_the_committed_claims():
    """Replay silently recovered zero claims while the README called it 'what CI
    and reviewers use'. Zero claims and a quiet news day looked identical."""
    docs = [json.loads(l) for l in (ROOT / "fixtures" / "documents.jsonl").open()]
    claims, _ = P.extract(docs, backend="replay")
    assert len(claims) > 0, "replay must recover the committed fixtures"
    print(f"ok  replay backend recovers {len(claims)} claims from fixtures")


# ---------------------------------------------------------------- clocks

def test_point_in_time_is_monotone():
    conn = connect(":memory:")
    upsert_documents(conn, [_doc()])
    insert_claims(conn, [{
        "claim_id": f"c{i}", "doc_id": "d", "signal": "supply_risk", "magnitude": 0.5,
        "confidence": 0.8, "direction": 0, "evidence_quote": "drought cuts the crop",
        "event_time": iso(T0), "ingest_time": iso(T0 + timedelta(hours=i)),
        "extractor": "t"} for i in range(5)])
    counts = [len(claims_as_of(conn, iso(T0 + timedelta(hours=h)))) for h in range(5)]
    assert counts == [1, 2, 3, 4, 5], counts
    print(f"ok  point-in-time replay is monotone {counts}")


def test_leakage_switch():
    """The gap between the two clocks IS the lookahead, measured not asserted."""
    conn = connect(":memory:")
    upsert_documents(conn, [_doc()])
    insert_claims(conn, [{
        "claim_id": "slow", "doc_id": "d", "signal": "price_pressure", "direction": 1,
        "magnitude": 0.9, "confidence": 0.9, "evidence_quote": "frost damage confirmed",
        "event_time": iso(T0), "ingest_time": iso(T0 + timedelta(minutes=90)),
        "extractor": "t"}])
    decision = iso(T0 + timedelta(minutes=10))
    honest = claims_as_of(conn, decision)
    leaky = conn.execute("SELECT * FROM claims WHERE event_time <= ?", (decision,)).fetchall()
    assert len(honest) == 0 and len(leaky) == 1
    assert P.score(honest, decision)["price_pressure"]["value"] == 0.0
    assert P.score(leaky, decision)["price_pressure"]["value"] > 0.0
    print("ok  leakage switch: the event_time view invents a signal the honest view cannot see")


def test_future_dated_claim_cannot_dominate():
    """A publisher-declared event_time in the future used to clamp to age 0, i.e.
    maximum weight forever, and ingest_time was legitimately in the past so no
    filter caught it."""
    rows = [{"signal": "supply_risk", "magnitude": 1.0, "confidence": 1.0, "direction": 0,
             "injection_flag": 0, "doc_id": "d",
             "event_time": iso(T0 + timedelta(days=3650))}]
    assert P.score(rows, iso(T0))["supply_risk"]["claims"] == 0, \
        "a claim dated ten years ahead must not score"
    print("ok  future-dated claim is excluded rather than given maximum weight")


def test_claims_are_append_only():
    """INSERT OR REPLACE silently overwrote a claim AND its ingest_time on
    re-extraction, destroying the record of what was known when."""
    conn = connect(":memory:")
    upsert_documents(conn, [_doc()])
    base = {"claim_id": "x", "doc_id": "d", "signal": "supply_risk", "magnitude": 0.5,
            "confidence": 0.8, "direction": 0, "evidence_quote": "q",
            "event_time": iso(T0), "ingest_time": iso(T0), "extractor": "v1"}
    insert_claims(conn, [base])
    insert_claims(conn, [{**base, "magnitude": 0.9, "ingest_time": iso(T0 + timedelta(days=1))}])
    row = conn.execute("SELECT magnitude, ingest_time FROM claims WHERE claim_id='x'").fetchone()
    assert row["magnitude"] == 0.5 and row["ingest_time"] == iso(T0), \
        "an existing claim must never be overwritten"
    print("ok  claims table is append-only; a re-run cannot rewrite history")


# ---------------------------------------------------------------- scoring

def test_signals_decay_at_different_rates():
    """One global half-life made the three signals differ only in output range --
    a tariff decayed like a sentiment blip."""
    assert P.HALFLIFE_D["policy_shock"] > P.HALFLIFE_D["supply_risk"] > P.HALFLIFE_D["price_pressure"]
    old = iso(T0 - timedelta(days=20))
    mk = lambda sig: [{"signal": sig, "magnitude": 1.0, "confidence": 1.0, "direction": 1,
                       "injection_flag": 0, "doc_id": "d", "event_time": old}]
    pol = P.score(mk("policy_shock"), iso(T0))["policy_shock"]["evidence_weight"]
    sup = P.score(mk("supply_risk"), iso(T0))["supply_risk"]["evidence_weight"]
    assert pol > sup * 5, f"policy must persist far longer than supply risk ({pol} vs {sup})"
    print(f"ok  per-signal decay: policy weight {pol} vs supply {sup} at 20 days")


def test_injected_document_cannot_move_a_signal():
    rows = [{"signal": "price_pressure", "direction": 1, "magnitude": 1.0, "confidence": 1.0,
             "injection_flag": 1, "doc_id": "x", "event_time": iso(T0)}]
    s = P.score(rows, iso(T0))["price_pressure"]
    assert s["value"] == 0.0 and s["claims"] == 0
    print("ok  injection-flagged document contributes zero weight")


# ---------------------------------------------------------------- filters

def test_relevance_filter():
    keep = ["Brazil coffee exports fall as drought cuts arabica crop",
            "Vietnam robusta prices climb on tight supply and export delays",
            "Amazon deforestation rules hit coffee exporters",
            "Closure of the Port of Santos delays coffee shipments",
            "ICE certified stock of coffee falls to 16-month low"]
    drop = ["Stag shot dead after injuring man having picnic in major city park",
            "Dutch Bros aims for another San Jose coffee drive-through",
            "Coffee tables stay tidy with B&M's three-piece storage set",
            "K2 Gold Corporation: K2 Drills High-Grade Gold at Mojave Project"]
    for t in keep:
        assert P.COFFEE.search(t) and P.MARKET.search(t) and not P.BLOCK.search(t), f"should keep: {t}"
    for t in drop:
        assert not (P.COFFEE.search(t) and P.MARKET.search(t) and not P.BLOCK.search(t)), f"should drop: {t}"
    print("ok  filter keeps market stories incl. deforestation/port/stock, drops retail")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\n{len(fns)} checks passed")
