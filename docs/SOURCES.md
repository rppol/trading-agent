# Sources

What is actually reachable, in what format, and what is dead. Every row was probed; verified
failures are recorded because a dead source that everyone still cites is more dangerous than a
missing one.

## Verified working APIs — use these before writing a scraper

| Source | Standard | Base URL | Auth | Depth |
|---|---|---|---|---|
| **Statistics Canada WDS** | REST/JSON | `https://www150.statcan.gc.ca/t1/wds/rest/` | none | field crops back to **1908** |
| **ABS Data API** (Australia) | **SDMX 2.1** | `https://data.api.abs.gov.au/rest/` | none | broadacre crops only **2022-23→** |
| **datos.gob.ar Series** | REST/JSON+CSV | `https://apis.datos.gob.ar/series/api/` | none | wheat area back to **1923** |
| **CFTC Commitments of Traders** | Socrata | `https://publicreporting.cftc.gov/resource/72hh-3qpy.json` | none | **1,053 weekly reports, 2006→** |
| **ICE certified stocks** | deterministic URL | `.../coffee_cert_stock_YYYYMMDD.xls` | none | daily, **2016→**, never revised |
| **Canadian Grain Commission** | CSV | `grainscanada.gc.ca/.../grain-statistics-weekly/` | none | weekly, 100+ years |

Two of these carry traps worth naming. The **ABS** series is levy-administrative data starting
2022-23, so it is useless for history — long Australian wheat lives in ABARES, which was
unreachable. And **StatCan's** `getChangedSeriesList` returns HTTP 409 outside the release
window, which reads as broken and is not.

## Verified dead or blocked — the ones still in everyone's citations

| Source | Status |
|---|---|
| `statsethiopia.gov.et` | **NXDOMAIN.** Live host is `ess.gov.et` — the dead one is what the literature cites |
| `coffeeboard.go.tz` (Tanzania) | **NXDOMAIN**, no working domain found |
| **ECX** (Ethiopian Commodity Exchange) | DNS resolves, **TCP refused/timeout from two networks**. Down or geo-fenced. The private mirror `2merkato.com` republishes its daily trade tables |
| `ecta.gov.et` / `coffee.gov.et` | **NXDOMAIN.** Ethiopian export figures reach the public only via press release |
| Bolsa de Cereales (Argentina) | **HTTP 403** WAF interstitial; the `estimacionesagricolas.` subdomain everyone cites **does not resolve** |
| Conseil du Café-Cacao (CI) | **HTTP 401** on the root — Basic auth or WAF, not a normal block |
| Ethiopian Customs / Ministry of Revenues | DNS OK, **TCP connect fails** |

**The Uganda case is the instructive one.** UCDA was dissolved in December 2024 and its functions
folded into the agriculture ministry — but `ugandacoffee.go.ug` survived the merger. So the
**institutional** discontinuity was not a **URL** discontinuity; it is a **schema** discontinuity,
and the check that matters is whether the report layout changed at the handover. A monitor keyed
on the URL would have seen nothing and silently started parsing a different document.

## Format reality

The APIs give you annual and monthly official statistics. **Every weekly signal that actually
moves a desk is a PDF or an XLS behind a scraper** — Argentine crop reports, export-sale
registrations, Australian state crop reports. The exceptions are Canadian Grain Commission
(CSV) and the ICE stock file.

Worst case observed: Uganda's monthly coffee report is a **PowerPoint deck exported to PDF**.
The text is embedded, so no OCR is needed, but per-glyph kerning splits words and numbers
(`R o b u s ta`, `240,117, 40 5`) and there is no table grid — extraction is coordinate
clustering against a per-layout template, and filenames churn so badly
(`07-April 2025 Report pptx(1).pptxii.pdf`) that URLs must always be scraped, never constructed.

## Terminology traps that silently corrupt a series

- **DJVE** (Argentina) is a *registration of an export sale*, not a shipment. It leads physical
  flows by weeks and spikes on duty-rate changes with no matching cargo. Never sum it with
  customs exports. Its pre-2016 predecessor, **ROE Verde**, is a different regime — splicing
  them without a break flag is a fabricated series.
- **campaña 2025/26** harvests in **late 2025**. Mapping it to a calendar year is off by one.
- **superficie sembrada vs cosechada** — sown versus harvested area. The gap is abandonment, and
  in a drought year the gap *is* the signal. Two series, never interchangeable.
- **quintal (qq) = 100 kg** in Argentina, not the Spanish 46 kg and not a hundredweight.
- **bueno / regular / malo** is a three-bucket crop-condition scale, not USDA's five. `regular`
  means *fair-to-mediocre*, not "normal" — a false friend that inverts the reading.
- **trigo pan vs candeal** — bread versus durum wheat. Headline "trigo" numbers are pan only.

## The options gap, stated as a gap

There is **no peer-reviewed study of seasonality or term structure in coffee option implied
volatility.** Coffee appears in the agricultural options literature once (Giot 2003, three
NYBOT IV series in a value-at-risk study, 1994–1999) and not for seasonality. The seasonal-IV
literature is built on corn, soybeans, wheat, hogs, cotton, sugar and natural gas — the softs
that appear are **sugar and cocoa, never coffee**. The Brazilian frost premium is documented
only in *futures* prices.

So any claim that July/September expiries carry systematically higher implied volatility is an
**untested hypothesis, not a citation**. That is a real opportunity and it must be presented as
one.

**And a claim to avoid:** "commodity option skew is persistently call-side, unlike equity
indices" does not survive the evidence. McKenzie et al. (2022), the only comprehensive study of
agricultural IV *functions*, find a pronounced **put-side** skew in cattle and a flat smile in
grains. Triantafyllou et al. (2015) find grain implied skewness **negative before 2002 and
positive after** — regime-dependent, with maize's full-sample mean still negative. The
defensible statement is that agricultural skew is *not reliably negative the way equity index
skew is*, varies by commodity, shifts by regime, and **has never been measured for coffee**.
