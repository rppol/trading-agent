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

## 2. The other inverted intuition: the cheap tier is the bill

Because 97%+ of documents never leave the filter, **filter spend dominates total LLM cost at every
tier.**

| Tier | Filter/month | Extraction/month (3%) | Total |
|---|---|---|---|
| 1 | $3,150 | $756 | **~$3,900** |
| 2 | $31,500 | $7,560 | **~$39,100** |
| 3 | $315,000 | $75,600 | **~$391,000** |

At the 1%–5% extremes extraction moves between $252 and $1,260 at Tier 1, and $25,200 and $126,000
at Tier 3 — **the filter still dominates regardless**, because the cascade rate only changes the
smaller number.

**Which inverts what to self-host.** The instinct is to self-host the expensive model. The
arithmetic says self-host the *cheap* one first:

| Tier | Filter self-hosted | vs API | Verdict |
|---|---|---|---|
| 1 | <1 GPU | $3,150 API | **stay on API** — one dedicated GPU's fully-loaded cost exceeds the bill |
| 2 | ~3x H100 ≈ $6,458/mo | $31,500 API | **self-host — ~5x cheaper.** This is the crossover |
| 3 | ~30x H100 ≈ $64,584/mo | $315,000 API | **self-host, and it is partly forced** — see below |

**At Tier 3 it stops being a cost decision.** 8.5B filter tokens/day is roughly **5.9M tokens per
minute sustained**, which exceeds standard API rate-limit tiers regardless of budget. Capacity, not
price, makes the decision.

Self-hosting *extraction* is a later and harder call: ~3x cheaper at Tier 3 (~$25,834 vs $75,600),
but open 70B-class models generally trail frontier quality on structured extraction and entity
resolution, and multi-GPU serving is real operational burden. Pilot it against the golden set
before treating the cost arithmetic as the decision.

---

## 3. What each tier needs, and why

| | **Tier 1 — 100k/day** | **Tier 2 — 1M/day** | **Tier 3 — 10M/day** |
|---|---|---|---|
| **Ingestion** | SQS or Postgres-as-queue. 1.16 docs/sec — nowhere near needing Kafka | **Kafka/Redpanda.** Not for throughput — for **≥3–4 independent replayable consumers** (dedup, embed, extract, corroboration) | Kafka, larger cluster, real fan-out and replay |
| **Primary DB** | Single-node Postgres, for years | Postgres + read replicas, Citus-ready | **Citus (sharded).** Single-node write ceiling is a few thousand TPS because everything funnels through one WAL |
| **Corpus storage** | S3, lifecycle-tiered. 11.7 TB | S3 tiered. 116.8 TB | **Iceberg/Delta lakehouse.** 1.17 PB was never going to be Postgres rows |
| **Vector index** | pgvector, **migrate within year 1** | Managed vector DB — 730M vectors puts pgvector out of the question | Sharded + **quantization mandatory** |
| **LLM** | Both tiers on API | **Self-host the filter**, extraction on API | Self-host filter (forced); pilot extraction |
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
  per-GB-of-RAM pricing. Otherwise the self-hosted filter fleet and Kafka dominate.
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
