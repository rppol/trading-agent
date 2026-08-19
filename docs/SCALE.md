# Scale: 100k, 1M, 10M documents per day

The brief's stated volume is ~500 documents/day, which is why ARCHITECTURE.md argues the numbers
are a misdirection. This document asks the other question: **what would actually break, and what
would it cost, if the volume were 200x, 2,000x or 20,000x that.**

Assumptions, stated first because everything moves with them: 800 tokens/document; a cascade
sending 100% through a cheap filter and **3%** through expensive extraction; ~160 KB stored per
document (raw + embedding + claims). That last figure is the biggest swing factor in the storage
lines and should be replaced with a measured average before anyone budgets from it.

---

## 1. The assumption that breaks first

**Vectors accumulate at the document rate, not the extraction rate.**

Everything gets embedded, because novelty and dedup run on everything — only extraction is gated
at 3%. So the vector count is a function of *documents ever seen*, not documents deeply processed:

| Tier | Docs/day | Vectors after 2 years |
|---|---|---|
| 1 | 100,000 | **73M** |
| 2 | 1,000,000 | **730M** |
| 3 | 10,000,000 | **7.3B** |

**pgvector's practical single-node ceiling is ~10–20M vectors.** HNSW must hold the full graph in
memory to build, at roughly 2–3x the base vector size — a 1536-dim float32 vector is 6 KB, so
12–18 KB loaded. 10M vectors is ~150 GB RAM (uncomfortable); 100M is ~1.5 TB (beyond economical
single-node); 1B is ~15 TB (not a single-node problem under any configuration).

**So Tier 1 crosses the ceiling inside year one**, despite "only" 100k documents a day. Teams size
the vector index off documents they deeply process and get blindsided by documents they ever saw.

This does not contradict the recommendation in PIPELINE.md §3 — at the brief's actual volume the
corpus is low millions of vectors and pgvector is correct. **The crossover is ~10–20M vectors, and
it is worth naming because it arrives much earlier than document counts suggest.**

### The related trap: it is build time, not query latency

The reason people leave pgvector is rarely p99. It is that **HNSW is not incrementally updatable
in the background**, so the index needs periodic full rebuilds — and once a rebuild takes longer
than the ingest window, you never catch up. If `maintenance_work_mem` is undersized, Postgres
falls back to a disk-based build that is **10–50x slower**, which is how a nightly rebuild
silently becomes a multi-day one.

---

## 2. The cheap tier is the bill — and the model choice matters ~53x more than the hosting choice

Because 97%+ of documents never leave the filter, **filter spend dominates total LLM cost at every
tier.** The cascade rate only moves the smaller number.

**But the first version of this section drew the wrong conclusion from that**, and the error is
instructive. It priced the filter at a frontier-vendor small model (~$1/$5 per M tokens) and
compared *that* against renting GPUs, concluding "self-host the filter at Tier 2, ~5x cheaper."

**The filter should never have been priced at $1/M.** An 8B-class model on a cheap-inference
provider is **$0.02/$0.04 per M** — about **53x cheaper per document** for a task that is a short
input and a ~20-token output. Correcting the model choice changes everything:

| Tier | Filter @ $1/$5 model | Filter @ $0.02/$0.04 model | Self-hosted GPUs |
|---|---|---|---|
| 1 | $3,150/mo | **~$62/mo** | <1 GPU, uneconomic |
| 2 | $31,500/mo | **~$625/mo** | ~$6,458/mo |
| 3 | $315,000/mo | **~$6,240/mo** | ~$64,584/mo |

**So self-hosting the filter loses at every tier — by roughly 10x, not wins by 5x.**

### And it cannot win, at any volume, for a reason that is not about utilisation

A rented H100 at **100% utilisation** costs about **$0.22/M tokens** for an 8B model. The hosted
price is **$0.02/M**. That is 11x cheaper than your own hardware running *perfectly*, before
counting idle time, failover, ops burden or model-update revalidation.

**This is a pricing-floor problem, not a utilisation problem.** Fleet operators run at
utilisation a single deployment cannot reach and price below your marginal compute cost. At
realistic utilisation — Tier 1's filter load is under 4% of one GPU — self-hosting costs
~$5.60/M, worse than a frontier small model.

The general lesson, which holds beyond this system: **managed open-weight providers already sit at
the utilisation ceiling you could only dream of hitting, so DIY self-hosting rarely beats them
economically.** Fireworks/Together price a 70B model at $0.90–1.04/M — almost exactly a
self-hosted H100's marginal cost at 100% utilisation, because that is what fleet-operated hosting
*is*.

### Extraction: hosted too, and the break-even is far away

Blended cost for the extraction shape (~11k input, ~800 output) on a frontier mid model is about
**$2.54/M**. A self-hosted 70B at 100% utilisation is **$0.93/M** — so break-even is ~36.6%
utilisation, which is roughly **2,150 extraction docs/day**. Add ops labour and continuous GPU
rental and it moves to **~3,800/day**. At the brief's volume that is 15x away.

**The one thing that does change the answer sooner:** if an eval shows an open 70B via a managed
provider matches frontier accuracy on the extraction schema, switching cuts cost ~60% with **zero
infrastructure work** and no volume threshold at all. That is an eval question, not a scale
question — and on a correctness-critical path it should not be taken on faith.

### Where self-hosting genuinely does become forced

**Rate limits, at Tier 3.** 8.5B filter tokens/day is ~5.9M tokens/minute sustained. Cheap-inference
providers cap differently — one caps concurrency (200 concurrent requests per model) rather than
RPM, another sets dynamic per-org limits with no published tiers. At 116 docs/sec average and
several times that at burst, **capacity becomes the constraint before cost does**, and a dedicated
deployment may be the only way to guarantee throughput.

There is also an honest secondary benefit: because baseline utilisation would be so low, a
self-hosted GPU has enormous burst headroom by construction, absorbing a 10–20x spike through
queueing (latency degrades) rather than rejection (requests fail). That is not a reason to
self-host today. It is a side benefit if volume forces the decision anyway.

---

## 3. What each tier needs, and why

| | **Tier 1 — 100k/day** | **Tier 2 — 1M/day** | **Tier 3 — 10M/day** |
|---|---|---|---|
| **Ingestion** | SQS or Postgres-as-queue. 1.16 docs/sec — nowhere near needing Kafka | **Kafka/Redpanda.** Not for throughput — for **≥3–4 independent replayable consumers** (dedup, embed, extract, corroboration) | Kafka, larger cluster, real fan-out and replay |
| **Primary DB** | Single-node Postgres, for years | Postgres + read replicas, Citus-ready | **Citus (sharded).** Single-node write ceiling is a few thousand TPS because everything funnels through one WAL |
| **Corpus storage** | S3, lifecycle-tiered. 11.7 TB | S3 tiered. 116.8 TB | **Iceberg/Delta lakehouse.** 1.17 PB was never going to be Postgres rows |
| **Vector index** | pgvector, **migrate within year 1** | Managed vector DB — 730M vectors puts pgvector out of the question | Sharded + **quantization mandatory** |
| **LLM** | Both tiers on API, cheap-inference filter | Both on API — self-hosting loses ~10x | Filter may be **self-hosted for capacity, not cost**; pilot extraction |
| **Team** | 2–3 engineers | 5–8 | **15–25** — the jump is not linear in volume; it is the GPU fleet and distributed storage turning a team into a platform division |

**Storage costs, and the one checkbox that matters:**

| Tier | 2-year corpus | All S3 Standard | Lifecycle-tiered |
|---|---|---|---|
| 1 | 11.7 TB | $269/mo | **~$60–90** |
| 2 | 116.8 TB | $2,686/mo | **~$600–900** |
| 3 | 1.17 PB | $26,864/mo | **~$5,900** |

A 4–5x gap at every tier, and it is a lifecycle policy rather than an architecture change — the
most controllable line in the whole system.

---

## 4. Where the money actually goes, per tier

- **Tier 1: LLM API spend, ~75% of total.** Everything else is nearly free at this volume.
- **Tier 2: the vector index, if you pick a RAM-priced product.** 730M vectors punishes
  per-GB-of-RAM pricing. With the filter correctly priced, LLM spend is ~$625/mo and Kafka is the
  next line, so **the vector index is the whole decision at this tier**.
- **Tier 3: the vector index, decisively — and it can dwarf everything else.** At 7.3B vectors the
  spread between object-storage-backed (~$880/mo storage) and RAM-priced quantized (~$210,000/mo)
  is roughly **240x for the same vector count.** Get this wrong and it exceeds the LLM bill, the
  Kafka bill and the GPU fleet combined.

**Quantization stops being optional past Tier 1.** Binary quantization (1 bit/dim) gives ~32x
memory reduction for 5–10% recall loss, recoverable to near-parity with a float rescore over the
top-K. Scalar int8 gives 4x for ~1–2%. At Tier 3 the unquantized index is simply unaffordable on
every option.

---

## 5. The costs that are invisible in a spreadsheet

Each of these is real, sizeable, and absent from the line item people budget:

| Trap | Where it bites | Size |
|---|---|---|
| **S3 request costs, not storage** | 4 PUTs per document (raw, processed, extract, metadata) at Tier 3 is 1.2B PUTs/month | **~$6,000/mo** — invisible next to the $5,900 storage line. Fix: batch small objects, or keep structured records in a database rather than one object each |
| **Embedding backfill on a model change** | Changing embedding models means re-embedding the **entire accumulated corpus**, not new documents | Tier 3 year-2: 5.84 **trillion** tokens ≈ **$116,800 one-time**, plus 2x index storage during cutover and a multi-day rebuild. People budget ongoing embedding cost and miss this entirely |
| **NAT gateway processing** | Private-subnet workers calling external APIs pay per-GB processing on top of egress | ~**$2,160/mo** at Tier 3 before egress. Fix: VPC gateway endpoints for AWS-internal traffic |
| **Connection pool exhaustion** | 50 service instances x pool of 10 = 500 connections against a default `max_connections` of 100–300 | Needs PgBouncer well before CPU or RAM suggests trouble |
| **Vacuum and index bloat** | The `SKIP LOCKED` dequeue pattern is UPDATE-heavy; autovacuum falls behind at Tier 3 write rates | Dead tuples, slowing index scans, and eventually transaction-ID wraparound risk. Fix: per-table autovacuum tuning, or time-partition and drop rather than vacuum |
| **Rate limits as a hard wall** | Tier 3's ~5.9M TPM sustained | Exceeds standard tiers regardless of budget — a capacity constraint masquerading as a cost one |

---

## 6. The one decision that matters at each transition

**100k → 1M: move novelty and dedup off pgvector *before* hitting the wall.** 730M vectors by year
two makes the single-node ceiling a certainty rather than a risk, and the migration is far cheaper
planned than as an incident. Everything else at this transition — adopting Kafka, self-hosting the
filter — is cost optimisation. This one is a correctness deadline.

**1M → 10M: choose the vector architecture priced at the vector count you will reach, not the one
you have.** The 240x spread between object-storage-backed and RAM-priced only appears at
billion-vector scale. Choosing the RAM-priced option because it was fine at Tier 2 is the single
most expensive mistake available here.

---

## 7. What does not break, and should not be over-engineered

**Dedup.** Naive pairwise is O(n²) and dead on arrival at 10M/day — but MinHash/SimHash with LSH
banding handles it comfortably on a handful of cores, and signatures are ~512 bytes/document
against 6 KB for an embedding, 12x cheaper to keep resident. Even Tier 3's full-corpus signature
set is ~3.65 TB, which is real but trivial beside the vector index.

Run it **upstream of the cascade**, where it cuts LLM spend by killing near-duplicates before they
cost a token. Then reuse the retrieval index for a tight-threshold semantic pass to catch what
hashing misses. Dedup throughput is not what breaks at any tier — the vector index and the cheap
filter dominate by one to two orders of magnitude.
