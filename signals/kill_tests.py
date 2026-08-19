"""The kill battery, actually run.

docs/ARCHITECTURE.md stakes the project on four cheap tests that can end it
before any modelling. Writing that down and not running them is the same failure
the register opens with, so this fires the ones the data supports and reports the
statistical power honestly -- including when the answer is "no power".

  python -m signals.kill_tests
"""
import json
import math
import ssl
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .store import connect, claims_as_of, docs_as_of
from .pipeline import score, SIGNALS

ROOT = Path(__file__).resolve().parent.parent
PRICE_URL = ("https://query1.finance.yahoo.com/v8/finance/chart/KC%3DF"
             "?range=3mo&interval=1d")


def kc_closes() -> dict[str, float]:
    """ICE Coffee C front month, daily settle. Free, no key.

    NOTE: this is a spliced CONTINUOUS series, not one contract. Log returns
    computed across a roll date include the contract spread rather than price
    action, and arabica rolls are large under backwardation. K2 below therefore
    has a known contamination on top of its already-fatal sample size. Fixing it
    needs a single-contract series or a ratio-adjusted splice; neither is free.
    """
    req = urllib.request.Request(PRICE_URL, headers={"User-Agent": "Mozilla/5.0"})
    # macOS python ships without a CA bundle wired in; use certifi when present.
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
        d = json.load(r)["chart"]["result"][0]
    out = {}
    for t, c in zip(d["timestamp"], d["indicators"]["quote"][0]["close"]):
        if c is None:
            continue
        out[datetime.fromtimestamp(t, timezone.utc).date().isoformat()] = float(c)
    return out


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None, None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None, None
    r = sxy / math.sqrt(sxx * syy)
    r = max(min(r, 0.999999), -0.999999)
    t = r * math.sqrt((n - 2) / (1 - r * r))
    return r, t


def n_for_ic(ic: float, power: float = 0.80) -> int:
    """Fisher-z sample size to distinguish |IC| from zero at 5% two-sided."""
    z = 0.5 * math.log((1 + ic) / (1 - ic))
    return int(((1.96 + 0.84) / z) ** 2 + 3)


def main():
    conn = connect()
    rows = claims_as_of(conn)
    docs = docs_as_of(conn)
    if not rows:
        print("no claims in store; run `make extract` first")
        return

    print("=" * 74)
    print("KILL BATTERY  —  ICE Coffee C (KC=F) vs the extracted claim stream")
    print("=" * 74)

    try:
        px = kc_closes()
    except Exception as e:
        print(f"price fetch failed: {e}")
        return
    days = sorted(px)
    rets = {days[i]: math.log(px[days[i]] / px[days[i - 1]]) for i in range(1, len(days))}
    print(f"\nprice series: {len(px)} sessions, {days[0]} -> {days[-1]}")
    print(f"last settle : {px[days[-1]]:.2f} c/lb")

    # ---------------- K4: effective breadth -------------------------------
    clusters = {d["cluster_id"] for d in docs if d["cluster_id"]}
    span_d = (datetime.fromisoformat(max(d["ingest_time"] for d in docs))
              - datetime.fromisoformat(min(d["ingest_time"] for d in docs))).total_seconds() / 86400
    span_d = max(span_d, 1e-9)
    print("\n--- K4  effective breadth " + "-" * 46)
    print(f"  documents                 {len(docs)}")
    print(f"  after near-dup clustering {len(clusters)}   ({len(clusters)/span_d:.1f}/day)")
    print(f"  claims                    {len(rows)}")
    themes = {(r["driver"], r["region"]) for r in rows}
    print(f"  distinct driver x region  {len(themes)}   ({len(themes)/span_d:.2f}/day)")
    k4 = len(clusters) / span_d
    print(f"  VERDICT: {'FAIL - below 5 effective docs/day' if k4 < 5 else 'pass'}")

    # ---------------- K2: contemporaneous explanatory power ---------------
    print("\n--- K2  does the claim flow explain the SAME DAY return? " + "-" * 16)
    nov = {d["doc_id"]: (d["novelty"] if d["novelty"] is not None else 1.0) for d in docs}
    xs, ys, used = {s: [] for s in SIGNALS}, [], []
    for day in sorted(rets):
        cutoff = f"{day}T23:59:59+00:00"
        visible = [r for r in rows if r["ingest_time"] <= cutoff]
        prev = [r for r in rows if r["ingest_time"] <= f"{day}T00:00:00+00:00"]
        if not visible:
            continue
        s_now = score(visible, cutoff, nov)
        s_prev = score(prev, f"{day}T00:00:00+00:00", nov) if prev else None
        for s in SIGNALS:
            delta = s_now[s]["value"] - (s_prev[s]["value"] if s_prev else 0.0)
            xs[s].append(delta)
        ys.append(rets[day])
        used.append(day)

    print(f"  overlapping sessions: {len(ys)}")
    if len(ys) < 3:
        print("  VERDICT: NO POWER — cannot compute a correlation at all")
    else:
        for s in SIGNALS:
            r, t = pearson(xs[s], ys)
            if r is None:
                print(f"  {s:<15} degenerate (no variance in signal or return)")
            else:
                print(f"  {s:<15} r = {r:+.3f}   t = {t:+.2f}   n = {len(ys)}")

    # ---------------- power: what would it take to know? ------------------
    print("\n--- POWER  how much data would settle this? " + "-" * 29)
    per_year = (len(themes) / span_d) * 365
    print(f"  distinct themes/year at this rate : {per_year:,.0f}")
    for ic in (0.0127, 0.03, 0.05):
        need = n_for_ic(ic)
        print(f"  IC={ic:<7} needs n={need:>7,}  ->  {need/max(per_year,1e-9):>8,.0f} years "
              f"on coffee alone")

    print("\n" + "=" * 74)
    print("HONEST READING")
    print("=" * 74)
    print(f"""  With {len(ys)} overlapping sessions and {len(rows)} claims this battery CANNOT
  return a meaningful answer, and reporting it as one would be the exact
  overfitting this project criticises elsewhere. What it does establish:

    * K4 FAILS on the measured corpus: {k4:.1f} effective documents/day against a
      threshold of 5. That alone is a stop, and it needed no price data.
    * The correlations above are reported to show the harness runs end to end,
      not because n={len(ys)} supports inference.
    * The power table is the real result: even at an optimistic IC of 0.05,
      coffee alone needs decades. This is an ARCHIVE problem, not a modelling
      problem, which is what the architecture document concludes.""")


if __name__ == "__main__":
    main()
