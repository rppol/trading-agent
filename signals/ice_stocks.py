"""ICE Coffee C certified warehouse stocks — free, daily, point-in-time.

Published at a deterministic public URL with no auth, back at least two years:
  https://www.ice.com/publicdocs/futures_us_reports/coffee/coffee_cert_stock_YYYYMMDD.xls

This is the highest-value free series available to a coffee desk and it is not in
GDELT at any volume. It carries three numbers, only one of which is widely
watched:

  TOTAL BAGS CERTIFIED   the headline every desk quotes
  TRANSITION BAGS        a SUBSET of the total (not additive), carrying a
                         discount from 2027 -- a structural cliff in plain sight
  PENDING GRADING        coffee submitted but not yet passed. It becomes
                         certified stock days later, so it mechanically leads
                         the headline number

Parse by SECTION HEADER, never by row index: the layout shifts between days as
"TODAY'S GRADING SUMMARY" collapses to text lines and the pending table appears
and disappears. A fixed-index parser reads the wrong table silently for months.
"""
import re
import ssl
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "data" / "ice_cache"
URL = ("https://www.ice.com/publicdocs/futures_us_reports/coffee/"
       "coffee_cert_stock_{ymd}.xls")

# The section HEADERS themselves changed over time: files before ~2024 use
# "BAGS CERTIFIED" and have no transition section at all (it was created for the
# 2023 de-certification rule). Matching the later string literally silently
# failed every pre-2024 file -- fetch succeeded, parse returned nothing, and the
# series simply stopped. Same shape as every other silent-absence bug here.
SECTIONS = {
    "total": re.compile(r"^(?:TOTAL )?BAGS CERTIFIED\s*$", re.I),
    "transition": re.compile(r"TRANSITION BAGS CERTIFIED", re.I),
    "pending": re.compile(r"Pending Grading Report", re.I),
}


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(d: date) -> bytes | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / f"{d:%Y%m%d}.xls"
    if key.exists():
        return key.read_bytes() or None
    req = urllib.request.Request(URL.format(ymd=f"{d:%Y%m%d}"),
                                 headers={"User-Agent": "trading-agent/0.1"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45, context=_ctx()) as r:
                b = r.read()
            key.write_bytes(b)
            return b
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Genuine absence -- a weekend or exchange holiday. Safe to cache.
                key.write_bytes(b"")
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    # Transient failure. Do NOT negative-cache: an earlier version did, which made
    # a rate-limited fetch permanently indistinguishable from a genuine holiday and
    # silently truncated the series by 15 months. Same shape as the GDELT fail-open.
    return None


def parse(blob: bytes) -> dict | None:
    """Section-aware. Returns the grand totals plus the per-origin breakdown."""
    import io
    import xlrd
    try:
        sh = xlrd.open_workbook(file_contents=blob).sheet_by_index(0)
    except Exception:
        return None
    rows = [[str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)]
            for r in range(sh.nrows)]

    out = {"as_of": None, "origins": {}}
    for row in rows:
        j = " ".join(row)
        if "As of:" in j:
            m = re.search(r"As of:\s*(.+?)\s{2,}", j + "  ")
            out["as_of"] = m.group(1).strip() if m else None
            break

    for key, header in SECTIONS.items():
        start = next((i for i, r in enumerate(rows)
                      if header.search(" ".join(c for c in r if c).strip())), None)
        if start is None:
            out[key] = None
            continue
        out[key] = None
        for i in range(start, min(start + 40, len(rows))):
            cells = [c for c in rows[i] if c]
            if not cells:
                continue
            # a later section header ends this one
            if i > start and any(h.search(" ".join(c for c in rows[i] if c).strip())
                                 for h in SECTIONS.values()):
                break
            if cells[0].startswith("Total in Bags"):
                nums = [c for c in cells if re.fullmatch(r"-?\d+\.?\d*", c)]
                if nums:
                    out[key] = int(float(nums[-1]))
                break
            if key == "total" and len(cells) > 2 and re.fullmatch(r"-?\d+\.?\d*", cells[-1]):
                out["origins"][cells[0]] = int(float(cells[-1]))
    return out


def series(start: date, end: date) -> list[dict]:
    rows = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            b = fetch(d)
            if b:
                p = parse(b)
                if p and p.get("total"):
                    rows.append({"date": d.isoformat(), **p})
        d += timedelta(days=1)
    return rows


if __name__ == "__main__":
    import json
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    end = date.today()
    s = series(end - timedelta(days=days), end)
    print(json.dumps([{k: v for k, v in r.items() if k != "origins"} for r in s], indent=1))
