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
| Claims extracted | 13 | after both grounding gates |
| Extraction cost | **$0.76** for 33 documents | ~$0.023/document via the `claude -p` CLI |
| GDELT filename vs publication | **label is ~9.8 min ahead** | HEAD `Last-Modified` across consecutive batches |

## Wire and institutional coverage in the same corpus

| Source | Documents in 7 days |
|---|---:|
| Reuters | **0** |
| Cecafe, Conab, ICO | **0** |
| Comunicaffe, Perfect Daily Grind, Barchart, StoneX, Platts | **0** |
| Noticias Agricolas, Globo Rural, Valor | **0** |
| Bloomberg | 189 |
| Argus Media | 39 |
| Fastmarkets | 15 |
| Daily Coffee News | 11 |
| `iheart.com` (radio syndication) | **52,439 — 7.8% of the corpus** |

## Corrections already applied to this table

- **1,550 documents per batch** was published, taken from a *single* sampled batch written
  down as a constant. True mean is 1,004. Every downstream funnel figure was ~5x too large.
- **15–25 tradeable documents per day** was published. The measured figure is **4.7**.
- **"50 documents collapsed into 24 clusters — half the corpus was echo"** was published as the
  sole empirical support for novelty weighting. The shipped corpus is **33 into 29, 12% echo**.
  The claim overstated its own evidence fourfold.
