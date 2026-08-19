"""CFTC Commitments of Traders — free, no token, and the feed this design calls
"the one line most readers skim".

ARCHITECTURE section 6 builds regime conditioning on positioning and the repo
never fetched it, which made the most load-bearing claim in the signal layer
purely assertional. This closes that.

The two clocks matter here more than anywhere:
  event_time  = report_date_as_yyyy_mm_dd  (the TUESDAY the positions were held)
  ingest_time = that Tuesday + 3 days at 20:30 UTC (release is Friday 15:30 ET)

A naive implementation keyed on the Tuesday hands itself THREE FREE DAYS of
lookahead every single week -- the position data for Tuesday is not public until
Friday afternoon, and a backtest that acts on it Tuesday is trading on
information nobody had.
"""
import json
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
CACHE = Path(__file__).resolve().parent.parent / "data" / "cot.json"
RELEASE_LAG_DAYS = 3          # Tuesday as-of -> Friday release
RELEASE_UTC = "20:30:00+00:00"  # 15:30 ET


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(market: str = "COFFEE", limit: int = 5000) -> list[dict]:
    q = urllib.parse.urlencode({
        "$where": f"contract_market_name like '%{market}%'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": limit,
    })
    req = urllib.request.Request(f"{API}?{q}",
                                 headers={"User-Agent": "trading-agent/0.1"})
    with urllib.request.urlopen(req, timeout=60, context=_ctx()) as r:
        return json.load(r)


def knowable_at(report_date: str) -> str:
    """When this report could first have been acted on."""
    d = datetime.fromisoformat(report_date.replace("Z", "+00:00")).date()
    return f"{d + timedelta(days=RELEASE_LAG_DAYS)}T{RELEASE_UTC}"


def normalise(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        try:
            oi = float(r.get("open_interest_all") or 0)
            mm_l = float(r.get("m_money_positions_long_all") or 0)
            mm_s = float(r.get("m_money_positions_short_all") or 0)
            pm_l = float(r.get("prod_merc_positions_long_all") or 0)
            pm_s = float(r.get("prod_merc_positions_short_all") or 0)
        except (TypeError, ValueError):
            continue
        if oi <= 0:
            continue
        out.append({
            "event_time": r["report_date_as_yyyy_mm_dd"][:10],
            "ingest_time": knowable_at(r["report_date_as_yyyy_mm_dd"]),
            "market": r.get("contract_market_name", ""),
            "open_interest": int(oi),
            "mm_net": int(mm_l - mm_s),
            "mm_net_pct_oi": round(100 * (mm_l - mm_s) / oi, 2),
            "commercial_net": int(pm_l - pm_s),
            "commercial_net_pct_oi": round(100 * (pm_l - pm_s) / oi, 2),
        })
    out.sort(key=lambda x: x["event_time"])
    return out


def crowding(rows: list[dict], window: int = 156) -> list[dict]:
    """Percentile rank of managed-money net length within a trailing window.

    This is the regime variable section 6 argues for: it says who is offside, not
    what the news is. Extreme crowding is what turns a headline into a squeeze --
    and the design's own scepticism applies, since Gorton/Hayashi/Rouwenhorst
    reject hedging pressure as a risk-premium determinant outright.
    """
    out = []
    for i, r in enumerate(rows):
        hist = [h["mm_net_pct_oi"] for h in rows[max(0, i - window):i]]
        pct = (100 * sum(1 for h in hist if h < r["mm_net_pct_oi"]) / len(hist)) if hist else None
        out.append({**r, "mm_crowding_pct": round(pct, 1) if pct is not None else None})
    return out


def main():
    rows = crowding(normalise(fetch()))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(rows, indent=1))
    print(f"CFTC Commitments of Traders — COFFEE   {len(rows)} weekly reports")
    print(f"  {rows[0]['event_time']} -> {rows[-1]['event_time']}\n")
    print(f"{'as-of':<12}{'knowable':<12}{'OI':>9}{'MM net':>9}{'%OI':>7}{'crowd%':>8}")
    for r in rows[-10:]:
        print(f"{r['event_time']:<12}{r['ingest_time'][:10]:<12}{r['open_interest']:>9,}"
              f"{r['mm_net']:>9,}{r['mm_net_pct_oi']:>7.1f}"
              f"{(r['mm_crowding_pct'] if r['mm_crowding_pct'] is not None else -1):>8.0f}")
    hi = [r for r in rows if (r["mm_crowding_pct"] or 0) >= 90]
    lo = [r for r in rows if r["mm_crowding_pct"] is not None and r["mm_crowding_pct"] <= 10]
    print(f"\n  weeks in the top decile of managed-money length: {len(hi)}")
    print(f"  weeks in the bottom decile:                      {len(lo)}")
    print("\n  Note the clock: every row is knowable three days AFTER its as-of date.")
    print("  Keying a backtest on the Tuesday grants three free days of lookahead,")
    print("  every week, and it looks like skill.")


if __name__ == "__main__":
    main()
