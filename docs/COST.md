# Cost

All measured figures resolve to [MEASUREMENTS.md](MEASUREMENTS.md).

Back-of-envelope for the system at the brief's stated scale. Assumptions are stated so they
can be argued with; the [interactive model](../index.html#/cost) recomputes as you change them.

The headline is counter-intuitive and it is the point of this document:

> **The LLM is roughly 0.4% of the bill. Data licences are about half. People are most of
> the rest.** The "AI" line item is the cheapest part of the AI system.

---

## 1. What the volumes actually cost

| Source | Volume | Bytes/day | Note |
|---|---|---|---|
| Price ticks, 5 venues | 10–50M msgs | ~0.4–2 GB raw, ~200 MB columnar | Bursts matter, averages don't |
| Positioning (COT) | Weekly | Kilobytes | Highest value per byte in the system |
| News + analyst | ~500 docs | ~15 MB, ~1M LLM tokens | ~$9/day at frontier pricing |
| Satellite | 1–5 TB | 1–5 TB | The only large number |
| AIS | 10M pings = **116/sec** | ~350 MB raw, ~60 MB columnar | 128 GB/year. One box |
| Social + transcripts | ~200k items | ~60 MB, ~30M tokens | Cascade or bankruptcy |
| Macro, weather, FX | Small | ~100 MB | Vintaging is the cost, not volume |

Everything except imagery fits comfortably on one well-chosen machine. Imagery is
**a thousand times** the rest combined.

---

## 2. Steady state, staged

Year 1, decisions taken as described in [ARCHITECTURE.md](ARCHITECTURE.md).

Footprint: 200 areas of interest at 4 km² each, 200k text items/day, 1 TB/day of imagery.

| Line | $/month | Share |
|---|---:|---:|
| People — 5 engineers (see note) | 30,000 | 39.9% |
| AIS licence — commercial S-AIS | 20,000 | 26.6% |
| Exchange data + derived-data licences | 12,000 | 16.0% |
| Satellite tasking — 30 triggered events | 6,000 | 8.0% |
| Cloud infra — compute, streaming, DB | 4,000 | 5.3% |
| Object storage — 90% tiered to archive | 2,153 | 2.9% |
| GPU — vision, AOI-scoped only | 700 | 0.9% |
| ASR — transcripts | 60 | 0.1% |
| **LLM tokens — every text source** | **294** | **0.4%** |
| **Total** | **75,208** | |

**Data licences 51%. People 40%. All compute and inference together under 10%.**

**The people line is the weakest number in this table and it inverts the headline.** $30,000 a
month for five engineers is **$72,000 a year fully loaded each**, which holds only at offshore
rates and is not stated as an assumption. At a realistic $250–400k fully loaded, the monthly
total becomes ~$170,000 and the split flips to **people 73%, data licences 22%.** The finding
that survives either way — and in fact strengthens — is that **the LLM is the cheapest line in
the system**, falling from 0.4% to 0.17%. The licences-versus-people framing does not survive,
and is corrected here rather than defended.

**A second collision, between this table and §1a.** The breadth argument says viability needs
20–40 commodities. The derived-data schedule below prices per instrument. At 24 commodities,
CME derived-data licensing alone is roughly **$534,000/year — about 59% of this entire staged
budget**, and the $75,208 figure understates by well over half. The two halves of this document
were never priced together, and doing so is the single most useful correction available to it.

---

## 3. The naive version of the identical system

Same requirements, same outputs, four decisions made carelessly:

**The same footprint** — identical AOIs, identical document volume, identical imagery — with
three policies chosen carelessly:

| Decision | Naive | Staged | Factor |
|---|---:|---:|---:|
| Satellite tasking — daily blanket commercial vs free Sentinel baseline with triggered commercial | 240,000 | 6,000 | **40×** |
| Text routing — every item to a frontier model vs 95% on a small model | 3,600 | 294 | **12×** |
| Storage — S3 Standard untiered vs 90% tiered to archive | 8,395 | 2,153 | **3.9×** |

**Naive total: $318,755/month. Staged: $75,208/month. Just over fourfold.**

Two things worth saying plainly about that number.

**Scope is held fixed on purpose.** It is easy to manufacture a fiftyfold gap by also
inflating the AOI count in the "naive" column, but that compares a bigger system to a
smaller one rather than comparing two ways of running the same system. Every row above
varies a decision, not a requirement.

**One line dominates everything.** Satellite tasking policy alone accounts for 96% of the
gap. The cascade and the storage tier are real and worth doing, but a team that optimises
tokens while blanket-tasking commercial imagery has tuned the 0.4% and ignored the 76%.

---

## 4. Where the leverage actually is

**Imagery: crop before you infer.** Full-scene inference over 1 TB/day is enormous and
almost all of it is ocean, cloud and land nobody trades. AOI-scoped inference over a few
hundred ports and growing regions is ~4,000 tiles/day; at ~12 ms per 512×512 tile that is
**under a minute of GPU per day**. A single always-on GPU is already oversized by two orders
of magnitude. The saving comes from cropping, not from a faster model.

**Imagery: task on events, not on schedule.** Commercial tasking at $5–25/km² is the single
largest controllable line. Sentinel-2 optical and Sentinel-1 SAR are free and give a
continuous baseline; commercial tasking fires only when a news or AIS signal says a specific
AOI matters this week. Roughly thirty tasking events a month instead of daily blanket
coverage.

**Text: the cascade is not a cost lever, and treating it as one leads you astray.**
This is worth stating carefully because the intuitive framing is wrong. Running a frontier
model over *every* raw GKG record would cost roughly $170–860/day. Running it only on the
market-relevant survivors costs about **$1.08/day**. The saving is real, but at this scale
neither number threatens the budget, so cost is not why the cascade exists.

The cascade exists for three other reasons:

- **Reproducibility.** A filter decision made by a language model is not replayable. Re-run
  the backtest and you are drawing fresh samples from a distribution you do not control, on
  weights that change under you. Anything whose output must be byte-identical on re-run must
  not be a model.
- **Auditability.** "The model thought it was relevant" is not an answer to a client asking
  why you were long on 14 March. A theme code, a region, a cited figure and three corroborating
  domains is.
- **Blast radius.** 150k model calls a day is a sustained dependency with retries, rate limits
  and a provider outage as a single point of failure. Two dozen calls fails safe.

**Which inverts the obvious recommendation: widen the model gate, do not narrow it.** Sending
all **88** coffee-mentioning documents a day to extraction rather than only the **4.7** that
pass the market filter costs roughly **$700/year** at metered prototype rates, and far less at
production rates. That is recall insurance, and one missed frost story
costs more than the premium. Spend what the cascade saved on more coverage, not less.

**Tokens: prompt caching does not help us, and I initially assumed it would.** The extraction
prompt is a long fixed prefix, which is textbook caching territory — but our calls are fifteen
minutes or more apart. The five-minute cache never hits, and the one-hour cache costs double on
write for roughly 24 writes serving 140 reads. Net effect is noise. It becomes worth enabling
once coverage widens to many commodities and calls become continuous, or if each batch window
is fired as one burst. The **batch tier (~50%)** does apply, and matters most for archive
backfill: five years of coffee history is ~297k documents, about **$6,700 one-off** — the
cheapest moat available here.

**Inference: rent until you are large.** A dedicated GPU beats API pricing somewhere above
roughly 20M tokens/day. This workload is two orders of magnitude below that. Self-hosting
here buys a fixed cost, an ops burden, and a worse model.

---

## 5. What the prototype actually cost

Not an estimate — metered from the runs:

| Item | Measured |
|---|---|
| GDELT ingest | $0 — bulk files are free and unthrottled |
| Extraction, 33 documents, 5 batched calls | **$0.76** |
| Implied per-document | ~$0.023 |
| Projected at the measured 4.7 tradeable docs/day | **~$0.11/day** |
| Projected across 20 commodities at the same rate | **~$2.20/day** |

Roughly **$3/month** to run the text half of this system for one commodity at the measured
volume — and note how small that makes every token-optimisation argument. The AIS licence
costs more than that before lunch on the first day.

A note on the metered figure: $0.021 per document is high for a batched extraction, because
each `claude -p` invocation re-establishes its context. A production deployment sends the
same fixed prompt prefix through prompt caching and the batch tier, which is where the
~$0.0003/document figure behind the table above comes from.

---

## 6. The line that was missing entirely: derived-data licensing

Everything above prices *ingesting* exchange data. None of it prices **publishing a signal
derived from it**, and those are separate licences with a step change between them.

CME's 2026 derived-data schedule is priced **per instrument per annum**:

| Instruments licensed | Annual |
|---|---:|
| 3 | **$102,780** |
| 5 | $171,300 |
| 8 | **$232,860** |
| 12 | $314,940 |

That is CME alone, before ICE (~$25,000 per product per year) and LME. Against a staged
infrastructure bill of ~$21,000/month excluding people, **this is the largest single line in the
business and it was absent from the model.**

**It is decided by product shape, not by negotiation.** Internal signal generation is already
covered by the non-display licence — CME's Category C explicitly names "trading strategy
development, signal processing" at $363/month per exchange. You cross into derived-data
licensing the moment a signal is externally distributed or sold. The industry test asks two
questions: can the output be **reverse-engineered** to recreate the source, and is it a
**substitute** for the source?

- A **daily directional score across ten commodities** passes both comfortably.
- A **continuously-updated fair-value price per contract** fails the substitute test and probably
  the first one too.

Same pipeline, same inputs, roughly **$200,000/year apart** — and the choice is made in a design
meeting long before anyone negotiates. Worse, if the output is classified as a "price assessment,
curve, or analytical reference value," CME's schedule prices it as *available upon request*, with
classification at their sole discretion. ICE's form agreement leaves both the derived-data
definition and the scope of use as **blank templates** to be negotiated per licensee, so it
cannot be priced from any public document.

**Get quotes before fixing the product shape.**

### The AI clause names this use case

Effective 2027-01-01, CME's licence updates prohibit, for **website-sourced** data, inclusion in
"any vector database, index, or knowledge base used for retrieval-augmented generation" and "use
for the automated generation of trade signals, market analysis or sentiment indicators" — with
an EU text-and-data-mining opt-out and stated bot countermeasures.

Read the scope precisely, because both the panic and the complacency are wrong. These terms
govern **public website data**. The same signals built on a licensed feed under the non-display
category are permitted, at $363/month per exchange. So it is a **sourcing constraint**, and the
realistic breach is accidental: someone writes a scraper because the licensed feed has a gap.

The control is architectural and cheap — an **egress allowlist** plus a **licence-provenance tag
on every ingested field**, so an unlicensed source cannot silently enter the pipeline. Nasdaq and
Cboe have adopted comparable positions; ICE currently has none. No exchange publishes a
dollar-denominated AI surcharge, which means this is a negotiation rather than a rate card.

### And the delayed-data lever, which may be a trap

ICE charges **nothing** for data older than 10 minutes; LME waives non-display fees for 30-minute
delayed data. CME does not. A delayed architecture takes the exchange bill from roughly
$43k/year to ~$13k/year, and given a minutes-latency SLO we may already qualify.

But published work shows news-signal Sharpe decaying materially from T+0 to T+2. **This is the
one place in this document where the cheap decision might be the wrong one.** Measure decay on
our own signals before committing; be prepared for the real-time bill to be correct.

---

## 7. Costs this model deliberately excludes

Honest omissions, each of which can dominate:

- **Full-text news licensing.** GDELT metadata and quotations are free; Reuters, Dow Jones or
  LexisNexis full text runs $5k–100k/month. The prototype's free path does not scale into a
  licensed product, and that is a commercial decision, not an engineering one.
- **Derived-data licence fees.** Redistributing a signal computed from ICE or CME prices
  triggers separate published fees. This is a routing constraint inside your own system, and
  it is usually discovered by legal rather than by engineering.
- **Compliance and legal.** MNPI controls, vendor diligence and data-provenance audit are
  real headcount at a regulated client.
- **Egress and lock-in.** A year of imagery on S3 costs roughly **$33,000 to move**, at
  $0.09/GB. That is not a running cost; it is the price of changing your mind.
- **The cost of being wrong.** A bad signal traded at size dwarfs every line above. This is
  why the [failure-mode register](FAILURE_MODES.md) is a cost document too.

### The ratio nobody models

**The evaluation infrastructure costs roughly 19x the inference it governs.**

| Item | Cost |
|---|---|
| Golden set: 1,300 documents, double-annotated with adjudication | **~$28,000 one-off** |
| Drift canary, quarterly re-adjudication, CI eval compute | **~$1,900/month** |
| The LLM tokens all of that governs | **~$100/month** |

That ratio looks absurd and it is correct, because the tokens are not what can hurt you. It is
also the line teams forget, and then quietly stop running evals when someone notices the bill.

Two related corrections to the model above. The workhorse model's price is **$2/$10 per million
tokens, not $3/$15** — an introductory rate that was made permanent, so any figure built on the
higher number is a third too pessimistic. And **fine-tuning is not worth it**: the compute is ~$35,
but 30,000 double-annotated extraction examples cost **~$224,000** in labelling. Against a ~$70/month
inference bill the payback never arrives. The trigger that would change this is not volume — it is
a licence forbidding third-party APIs, which given the clauses above is the likeliest one to fire.
