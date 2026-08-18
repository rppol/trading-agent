# Cost

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
| People — 5 engineers | 30,000 | 39.9% |
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

**Text: the cheap filter, not the cheap model.** Measured on live GKG batches, a word-bounded
keyword filter removes **85% of coffee-mentioning documents** before any model runs — café
openings, campus promotions, a stag shot in a park. The remaining cascade stage sends ~95% of
survivors to a small model. Together these mean the frontier model sees a couple of dozen
documents a day.

**Tokens: the prompt is a fixed prefix.** The extraction prompt is long and identical across
documents, which is close to the ideal case for prompt caching (up to ~90% off the cached
portion) stacked with batch pricing (~50%). The variable part is a short snippet.

**Inference: rent until you are large.** A dedicated GPU beats API pricing somewhere above
roughly 20M tokens/day. This workload is two orders of magnitude below that. Self-hosting
here buys a fixed cost, an ops burden, and a worse model.

---

## 5. What the prototype actually cost

Not an estimate — metered from the runs:

| Item | Measured |
|---|---|
| GDELT ingest | $0 — bulk files are free and unthrottled |
| Extraction, 15 documents, 2 batched calls | **$0.27** |
| Implied per-document | ~$0.018 |
| Projected at 25 tradeable docs/day | **~$0.45/day** |
| Projected with a 10× wider commodity set | **~$4.50/day** |

Roughly **$14/month** to run the text half of this system for one commodity. The AIS licence
costs more than that before lunch on the first day.

A note on the metered figure: $0.021 per document is high for a batched extraction, because
each `claude -p` invocation re-establishes its context. A production deployment sends the
same fixed prompt prefix through prompt caching and the batch tier, which is where the
~$0.0003/document figure behind the table above comes from.

---

## 6. Costs this model deliberately excludes

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
