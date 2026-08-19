"""Retrospective replay: would this design have caught it, and did it pay?

The claim under test is NOT "we predict price". The design explicitly does not
claim that, and the case study shows a correct physical signal with no
flat-price edge. The claim is narrower and testable:

    we surface material changes in primary documents, mechanically, ahead of
    the commentary that eventually reports them.

So this measures DETECTION -- dated alerts, lead time, and a pre-registered
directional test -- and reports the price leg separately and sceptically.

WHY A REPLAY OVER THIS SOURCE IS HONEST. The ICE certified stock file for date D
was published on D and is never revised. Fetching coffee_cert_stock_20231130.xls
today returns exactly what a trader saw that afternoon. GDELT rewrites its own
archive and USDA PSD serves only the current vintage; this source does neither,
which is what makes point-in-time replay meaningful rather than decorative.

PRE-REGISTRATION. Every threshold below was fixed before any outcome was
computed, and they are deliberately round numbers rather than tuned ones. A
threshold chosen after seeing the result is a parameter fitted to the answer.
"""
import json
import statistics as st
from datetime import date, datetime, timedelta
from pathlib import Path

# ---- pre-registered detector thresholds. Fixed before evaluation. ----------
SURGE_MULT = 3.0      # pending > 3x its trailing median
SURGE_MIN = 20_000    # ...and materially large in absolute terms
DRAIN_FRAC = 0.10     # pending < 10% of trailing median
DRAIN_RUN = 5         # ...for this many consecutive sessions
CLIFF_PCT = 15.0      # certified down this much over CLIFF_WIN sessions
CLIFF_WIN = 20
LOOKBACK = 60         # trailing window for the medians
HORIZON = 42          # sessions over which the prediction is judged
COOLDOWN = 42         # suppress repeat alerts of the same kind


def load(path="/tmp/ice_full.json"):
    rows = json.loads(Path(path).read_text())
    rows.sort(key=lambda r: r["date"])
    return rows


def detect(rows):
    """Deterministic. No model anywhere in this function -- which is the point:
    the highest-value 'agent' in the design is a diff with a threshold."""
    alerts = []
    last = {}
    drain_run = 0
    for i, r in enumerate(rows):
        if i < LOOKBACK:
            continue
        hist = rows[i - LOOKBACK:i]
        med_pending = st.median([h["pending"] for h in hist]) or 0
        d = r["date"]

        def emit(kind, detail, direction):
            prev = last.get(kind)
            if prev and (datetime.fromisoformat(d) - datetime.fromisoformat(prev)).days < COOLDOWN:
                return
            last[kind] = d
            alerts.append({"date": d, "kind": kind, "detail": detail,
                           "predicts": direction, "certified": r["total"],
                           "pending": r["pending"]})

        # 1. the queue surges -> coffee is inbound -> stocks should REBUILD
        if med_pending > 0 and r["pending"] > max(SURGE_MULT * med_pending, SURGE_MIN):
            emit("PENDING_SURGE",
                 f"pending {r['pending']:,} vs trailing median {med_pending:,.0f}", +1)

        # 2. the queue empties -> nothing inbound -> stocks should keep DRAINING
        drain_run = drain_run + 1 if (med_pending > 0 and r["pending"] < DRAIN_FRAC * med_pending) else 0
        if drain_run == DRAIN_RUN:
            emit("PENDING_DRAIN",
                 f"pending {r['pending']:,} under {DRAIN_FRAC:.0%} of median for {DRAIN_RUN} sessions", -1)

        # 3. a stock cliff -- context, not a directional prediction
        if i >= CLIFF_WIN:
            base = rows[i - CLIFF_WIN]["total"]
            if base > 0 and 100 * (r["total"] - base) / base <= -CLIFF_PCT:
                emit("STOCK_CLIFF",
                     f"certified {base:,} -> {r['total']:,} in {CLIFF_WIN} sessions", 0)
    return alerts


def judge(rows, alerts):
    """Did the directional alerts come true, over the pre-registered horizon?"""
    idx = {r["date"]: i for i, r in enumerate(rows)}
    out = []
    for a in alerts:
        if a["predicts"] == 0:
            continue
        i = idx[a["date"]]
        j = min(i + HORIZON, len(rows) - 1)
        if j <= i:
            continue
        chg = 100 * (rows[j]["total"] - rows[i]["total"]) / max(rows[i]["total"], 1)
        out.append({**a, "fwd_change_pct": round(chg, 1),
                    "correct": (chg > 0) == (a["predicts"] > 0)})
    return out


def main():
    rows = load()
    print(f"ICE certified stock series: {len(rows)} sessions, "
          f"{rows[0]['date']} -> {rows[-1]['date']}\n")

    alerts = detect(rows)
    judged = judge(rows, alerts)

    print("=" * 76)
    print("DETECTION REPLAY  -- pre-registered thresholds, no model in the loop")
    print("=" * 76)
    by_kind = {}
    for a in alerts:
        by_kind.setdefault(a["kind"], []).append(a)
    for k, v in sorted(by_kind.items()):
        print(f"  {k:<15} {len(v):>3} alerts over "
              f"{(datetime.fromisoformat(rows[-1]['date'])-datetime.fromisoformat(rows[0]['date'])).days/365:.1f} years")
    print()

    for a in alerts:
        arrow = {1: "stocks REBUILD", -1: "stocks KEEP DRAINING", 0: "context only"}[a["predicts"]]
        print(f"  {a['date']}  {a['kind']:<15} {arrow:<22} {a['detail']}")

    if judged:
        hit = sum(1 for j in judged if j["correct"])
        print("\n" + "=" * 76)
        print(f"DIRECTIONAL TEST over {HORIZON} sessions   n = {len(judged)}")
        print("=" * 76)
        print(f"{'date':<12}{'alert':<16}{'predicted':>10}{'actual %':>10}  hit")
        for j in judged:
            print(f"{j['date']:<12}{j['kind']:<16}"
                  f"{('up' if j['predicts']>0 else 'down'):>10}"
                  f"{j['fwd_change_pct']:>10.1f}  {'YES' if j['correct'] else 'no'}")
        print(f"\n  hit rate: {hit}/{len(judged)} = {100*hit/len(judged):.0f}%")
        print(f"  a coin gives {len(judged)/2:.1f}; with n={len(judged)} the "
              f"95% band is roughly {len(judged)/2 - 1.96*(len(judged)**0.5)/2:.1f}"
              f"-{len(judged)/2 + 1.96*(len(judged)**0.5)/2:.1f} hits")
        print("\n  Read this as a DETECTION result, not a trading result. It says the")
        print("  queue leads the stock number, which the design already claims and")
        print("  which is partly an accounting identity. It says nothing about price.")


if __name__ == "__main__":
    main()
