# Measurements

Every quantitative claim in the other documents resolves here. They are measured, not
estimated, and the measurement command is given so each can be re-run.

The reason this file exists: an earlier draft carried the same figures inline in three
documents, and when one was corrected the others silently kept computing recommendations from
dead numbers. A number with three homes has no home.

| Quantity | Value | Basis |
|---|---:|---|
| Batches cached | 673 | ~7.0 days of 15-minute GKG batches |
| Documents ingested | 675,840 | all rows with >=20 tab-separated fields |
| Documents per batch | **mean 1,004, median 946** | range 314–2,189 — a 7x spread, so no single figure is representative |
| Documents per day | **96,405** | mean x 96 batches |
| Distinct domains | 8,383 | field `V2SourceCommonName` |
| Coffee term in the title | **619 total, 88.3/day** | 0.092% of documents |
| Removed by the retail blocklist | 153 total, 21.8/day | 25% of coffee-mentioning titles |
| **Survives the market filter** | **33 total, 4.7/day** | the corpus the prototype extracts from |
| Cheap filter removal rate | **95%** | of coffee-mentioning documents, before any model runs |
| Dedup: documents -> clusters | **33 -> 29** | dedup ratio **0.121**, i.e. 12% echo |
| Claims extracted | 13 | after both grounding gates (one was silently lost to a colliding id until 2026-08-19) |
| Extraction cost | **$0.76** for 33 documents | ~$0.023/document via the `claude -p` CLI |
| GDELT filename vs publication | **label is ~9.8 min ahead** | HEAD `Last-Modified` across consecutive batches |

## Wire and institutional coverage in the same corpus

| Source | Documents in 7 days |
|---|---:|
| Reuters | **0** |
| Cecafe, Conab, ICO | **0** |
| Comunicaffe, Perfect Daily Grind, Barchart, StoneX, Platts | **0** |
| Noticias Agricolas, Globo Rural, Valor | **0** |
| Bloomberg | **0** (the 189 once reported were all `bnnbloomberg.ca`) |
| Argus Media | 39 (`argusmedia` subdomains) |
| Fastmarkets | 15 |
| Daily Coffee News | 11 |
| `iheart.com` (radio syndication) | **52,439 — 7.8% of the corpus** |

## The translingual stream, measured after review found it was never fetched

192 batches, ~2 days.

| Quantity | English stream | Translingual stream |
|---|---:|---:|
| Documents per day | ~96,000 | **~217,000** |
| Share of total corpus | **31%** | 69% |
| Coffee term in title | 88.3/day | 12.5/day |
| Survives the market filter | 4.7/day | 2.5/day |

Top source languages in the translingual sample: Spanish 69,994 · Chinese 41,291 · German
39,347 · Russian 28,059 · Italian 26,465 · Turkish 22,218 · Portuguese 19,554 · French 18,490.

The coffee yield looks lower, and that is an artefact of our own instrument: the relevance
lexicon is `coffee|arabica|robusta`, **English only**. The five survivors matched solely because
"robusta" is a loanword. `café`, `cà phê`, `kaffee`, `кофе` and `咖啡` match nothing, so the
true translingual yield is unmeasured and certainly higher.

What the survivors were — the category an earlier draft declared absent from GDELT entirely:

- `vov.vn` — "Giá cà phê hôm nay 18/8: Giá cà phê Robusta tăng" (today's coffee price, robusta rising)
- `dantri.com.vn` — Vietnamese daily agricultural prices, coffee jumping
- `investimentosenoticias.com.br` — Brazilian robusta market

## Wire presence by field, not by domain

The distinction that broke the original headline claim.

| Wire | As a domain | Named in `V1Organizations` |
|---|---:|---:|
| Associated Press | **0** | 14,815 (**2.19%**) |
| Reuters | **0** | 11,198 (**1.66%**) |
| Bloomberg | **0** | 2,511 (0.37%) |
| Dow Jones | 0 | 524 (0.08%) |

The earlier table reported "Bloomberg 189" and "Daily Coffee News 11" from **substring** matching
against the domain field: those 189 were all `bnnbloomberg.ca`, a Canadian licensee. Exact-domain
equality puts Bloomberg at zero too.

## Corrections already applied to this table

- **1,550 documents per batch** was published, taken from a *single* sampled batch written
  down as a constant. True mean is 1,004. Every downstream funnel figure was ~5x too large.
- **15–25 tradeable documents per day** was published. The measured figure is **4.7**.
- **"50 documents collapsed into 24 clusters — half the corpus was echo"** was published as the
  sole empirical support for novelty weighting. The shipped corpus is **33 into 29, 12% echo**.
  The claim overstated its own evidence fourfold.
- **"GDELT does not contain coffee market news"** was published as the headline finding. Wire
  content is present at 2–4% under republisher domains, and the stream containing origin-country
  coffee price reporting was never fetched. The corrected claim is in ARCHITECTURE §0.
