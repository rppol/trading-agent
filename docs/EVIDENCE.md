# Evidence

What was tested, and what died. Most of the attractive claims this project generated did not
survive measurement — that record is the point of this document, because a design nobody tried to
falsify is a design nobody has tested.

---

## 1. Claims killed or corrected

| Claim | Fate |
|---|---|
| Gas → urea → coffee cost chain | r ≈ 0, and **the cause peaked six months after the effect** |
| Fertiliser costs cut yields | falsified by a **record crop, +12.8%** |
| Positioning crowding causes squeezes | correlation real (t = +2.79), **mechanism backwards** — the middle of the crowding distribution moves most, not the tails |
| GDELT lacks wire coverage | it has it. Domain-matching said 0%; **field-matching found AP 2.19%, Reuters 1.66%** — and 69% of the corpus (the translingual stream) had never been fetched at all |
| The ICE rule was a buried signal | **Reuters reported it the next day.** The edge was interpretation, not detection |
| Tradeable documents: 15–25/day | **4.7/day** — a 5x funnel inflation |
| The pipeline is 97% commodity-agnostic | **survivorship** — it counted code that exists, not code that is missing |
| Certified stocks predict price | withdrawn. The figure was not reproducible by the shipped harness, and the series it rested on has a three-year hole (§4) |

Not one was a coding error. Each was a plausible story that survived because nothing in the
process was built to kill it. **The design's first obligation is therefore falsifiability, not
capability.**

---

## 2. The case study: the ICE rule, and why it is an interpretation edge

In 2023 ICE changed the certification rules for coffee delivered against the "C" contract.

**The claim this started as — a buried signal nobody noticed — is false.** Reuters reported the
rule change the day after it was announced, and a trade blog linked it to stocks within two
weeks. A detector firing on the announcement would have been **last, not first**.

**What was real is a 28-day framing gap.** The rule was reported as an administrative change on
30 September. Explicit attribution of the stock decline to it did not appear until **30 November**
— 28 days after the mechanism was visible in the data. Everyone had the fact; almost nobody had
done the arithmetic.

**The measurable relationship.** Pending grading as a share of certified stocks, sampled weekly
across **182 observations, roughly mid-2023 to August 2026** (the window our parser can actually
read — see §4), against subsequent certified-stock change:

| Horizon | Pending share | Mean-reversion control | Momentum control |
|---|---:|---:|---:|
| 14 days | **+0.644** | +0.362 | +0.592 |
| 28 days | **+0.606** | +0.321 | +0.522 |
| 42 days | **+0.583** | +0.300 | +0.320 |

Thresholds were **pre-registered before evaluation**. The relationship beats both controls at all
three horizons.

**The honest out-of-sample result:** three alerts in 1.7 years, two hits from two scored. **At
n=2 that is inside the coin-flip band** and is reported as an alert-rate result — a human can
actually review three alerts in 1.7 years — not as evidence of skill.

**And the level is a trap.** A 23-year low in certified stocks preceded a **45.5% price decline**;
a multi-year high preceded a **70% rally**. The stock *level* is not the signal; the *flow*
through the grading queue is.

---

## 3. The pattern confirmed on a second commodity

**India, wheat.** By 10 May 2022 the FCI had procured **5.51% of a 44.4 Mt season target** — the
season finished near 18.7–19.5 Mt against 43.44 Mt the prior year, a **>50% shortfall**, all of it
publicly reported. Three days later India banned wheat exports. The press called it a "surprising
U-turn"; CBOT went **+5.9% with the July contract limit-up**.

Same shape as the coffee finding — a public, unaggregated primary-source trail ahead of a market
surprise — on a different continent, commodity and mechanism. **Two instances is the difference
between an anecdote and a pattern.**

Wheat also **re-confirms the differential rule and finds its exception**. A regional shock lives
in spreads: Russia's weekly export duty has no mechanism to move CBOT soft red wheat. The
exception is size — the Black Sea corridor carried ~33 Mt, and its collapse moved **flat price
+3.5% in a session**. So the rule is gated by **origin share of world trade, not by geography**,
and needs that threshold written into it.

**Two attractive wheat hypotheses died.** Black Sea Grain Initiative deadlines were
calendar-visible and universally watched — the structural opposite of buried. And the
protein-premium parallel inverts: drought raises protein **crop-wide**, so high-protein wheat
becomes *more* abundant and the premium **narrows** rather than spikes.

---

## 4. Silent absence in our own data

**The ICE certified-stock parser reads 0% of 2021, 0% of 2022 and 43% of 2023** — pre-2024 files
are binary OLE `.xls`, the parser handles the later text format, and it returns `None` without
raising. Measured across 1,266 cached files; roughly 61% parse, essentially all from mid-2023.

`series()` returns only the rows it could parse, so a caller requesting 2021–2026 gets 2023
onward and **no indication anything is missing**. Consequences, both real: a November 2022 figure
quoted in an earlier draft cannot have come from this pipeline (which is why two different values
for it appeared in one document), and the regression in §2 has had its stated period corrected
from 2021 to 2023.

**This is the register's own thesis found in our own code** — a parser returning empty on an
unrecognised format is indistinguishable from a world where nothing happened.

---

## 5. Corpus measurements

Every quantitative claim elsewhere resolves here. An earlier draft carried these inline in three
documents, and when one was corrected the others kept computing from dead numbers. **A number
with three homes has no home.**

| Quantity | Value | Basis |
|---|---:|---|
| Batches cached | 673 | ~7.0 days of 15-minute GKG batches |
| Documents ingested | 675,840 | rows with ≥20 tab-separated fields |
| Documents per batch | **mean 1,004, median 946** | range 314–2,189 — a 7x spread, so no single figure is representative |
| Documents per day | **96,405** | mean × 96 batches |
| Distinct domains | 8,383 | field `V2SourceCommonName` |
| Coffee term in title | **619 total, 88.3/day** | 0.092% of documents |
| Removed by retail blocklist | 153 total, 21.8/day | 25% of coffee-mentioning titles |
| **Survives the market filter** | **33 total, 4.7/day** | the corpus the prototype extracts from |
| Cheap filter removal rate | **95%** | *of coffee-mentioning documents* — not of the raw stream, where the full funnel is ~99.5% |
| Dedup: documents → clusters | **33 → 29** | ratio 0.121, i.e. **12% echo** |
| Claims extracted | 13 | after both grounding gates |
| Extraction cost | **$0.76** for 33 documents | ~**$0.023/document** |
| GDELT filename vs publication | label is **~9.8 min ahead** | `Last-Modified` across consecutive batches |

**Scope note, because it has caused confusion:** 4.7 documents/day is the *coffee pilot's
tradeable* rate — roughly 3,400 claims over two years. The storage sizing elsewhere (1–4M
documents, ~3.6M vectors) targets a **multi-commodity book**, not this pilot. The two numbers
describe different systems and must not be compared.

---

## 6. Sources: what works and what is dead

| Source | State |
|---|---|
| GDELT GKG 2.1 bulk | **works, unthrottled.** Use bulk files, never the DOC API on a request path |
| GDELT DOC API | **throttled, and fails open** — returns an error string under HTTP 200 |
| GDELT translingual stream | **works**, and is ~2–2.7x the English stream by volume. Was never fetched until review caught it |
| ICE certified stocks | works 2024+; **silently empty before that** (§4) |
| CFTC Commitments of Traders | **works** — Socrata API, 1,053 weekly reports back to 2006 |
| USDA PSD | works, but **serves only the current vintage** — must be snapshotted at ingest or it rewrites history |
| Yahoo `KC=F` | works for price |
| ICO, Cecafé, Conab | **not machine-readable** — PDFs, often scans |

**Terminology traps that silently corrupt a series:** bags vs tonnes (a 60 kg bag is not a metric
tonne); crop year vs calendar year, which differ by origin; "certified" vs "pending grading" vs
"transition" stocks, which are three different quantities and one is a subset rather than an
addend; and Arabica "C" vs Robusta contracts, quoted in different units.

---

## 7. How we would know we are still wrong

Stated in advance, because every wrong claim above was retrofitted after the fact.

- **The nowcast does not beat published consensus** on the official release, over a pre-registered
  window. Then the system is an expensive way to reproduce a free number.
- **The error bar does not widen when coverage drops.** Then the stated uncertainty is decoration.
- **Entity resolution turns out to be easy.** Then there is no moat and a competitor replicates in
  a fortnight.
- **The aggregate is dominated by one publisher.** Then one subscription replaces the pipeline.
- **The falsification battery already fails its own gate:** 4.2 effective documents/day against a
  threshold of 5. On the measured corpus this is a stop, and it needed no price data.
