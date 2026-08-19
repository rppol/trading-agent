# Cost

Back-of-envelope at the brief's stated scale, then what changes at 100x and 1000x.

**The headline: the LLM is 0.2% of the bill.** Licensing and people are 53–76%. A team that
optimises tokens while blanket-tasking commercial imagery has tuned the 0.2% and ignored the rest.

---

## 1. Steady state

Footprint: 200 areas of interest at 4 km² each, 200k text items/day, 1 TB/day imagery,
10 commodities.

**Engineering cost is the largest single line and is a business decision, not a technical one**,
so it is a range rather than a smuggled constant.

| Line | Offshore team | US/UK team |
|---|---:|---:|
| **People — 5 engineers** | **30,000** | **125,000** |
| **Derived-data licensing, 10 commodities** (§3) | **22,825** | 22,825 |
| AIS licence — commercial S-AIS | 20,000 | 20,000 |
| Exchange data, non-display | 12,000 | 12,000 |
| Satellite tasking — 30 triggered events | 6,000 | 6,000 |
| Cloud infra | 4,000 | 4,000 |
| Object storage — 90% tiered | 2,153 | 2,153 |
| Evaluation: golden set upkeep + CI | 1,900 | 1,900 |
| GPU — vision, AOI-scoped | 700 | 700 |
| ASR | 60 | 60 |
| **LLM tokens — every text source** | **196** | **196** |
| **Total** | **~99,800** | **~194,800** |

Two things about this table are counter-intuitive and both are load-bearing.

**Evaluation costs ~10x the inference it governs** ($1,900 against $196) — and that is correct,
not a red flag. The tokens are not what can hurt you; a wrong claim served with confidence is.

**The LLM line assumes the right model per tier.** Triage is a ~1,000-token input with a
~20-token binary output; pricing it at a frontier small model instead of an 8B-class endpoint
costs **~53x more per document** (§4). That single choice, not the hosting decision, dominates
LLM spend at every scale.

---

## 2. The naive version of the identical system

Same footprint, same outputs, three policies chosen carelessly:

| Decision | Naive | Staged | Factor |
|---|---:|---:|---:|
| Satellite — daily blanket commercial vs free baseline + triggered | 240,000 | 6,000 | **40x** |
| Text routing — everything to a frontier model vs a cascade | 3,600 | 196 | **18.4x** |
| Storage — S3 Standard untiered vs 90% tiered | 8,395 | 2,153 | **3.9x** |

**Naive total: $343,480/month against a staged ~$99,800 — a factor of 3.44.**

Scope is held fixed deliberately: every row varies a *decision*, not a requirement. Inflating the
AOI count in the naive column would manufacture a bigger gap by comparing two different systems.

**One line dominates: satellite tasking policy alone is 96% of the $243,600 gap.** The cascade and
the storage tier are real and worth doing, but they are rounding errors beside the tasking
decision.

---

## 3. Derived-data licensing — the line most models omit entirely

The second-largest line, and the one nobody budgets: **a signal computed from licensed exchange
prices and redistributed owes fees to the exchange.** At 10 commodities that is roughly
**$274k/year**.

The decisive question is not the rate card, it is **product shape**:

- Is the output **reverse-engineerable** back to the underlying price?
- Is it a **substitute** for taking the source feed?

Answer yes to either and the derived-data schedule applies. Answer no to both and it may not. The
gap between those two answers is on the order of **$200k/year**, and it is decided at design time
by what the signal exposes — not later, by negotiation.

Two corollaries: the AI clause in current schedules explicitly reaches vector stores and
retrieval indexes built on licensed data; and a **delayed-data architecture** cuts the exchange
bill by roughly 3x, which is free if the product does not need real-time ticks and impossible to
retrofit if it does.

---

## 4. What the model choice is worth, and why self-hosting is not

**Triage priced correctly is ~53x cheaper.** An 8B-class model on a cheap-inference provider is
~$0.02/$0.04 per M against ~$1/$5 for a frontier small model. Because 97%+ of documents never
leave the filter, this choice dominates LLM spend at every volume.

**Self-hosting the cheap tier cannot win, at any volume — and not for utilisation reasons:**

| | $/M tokens |
|---|---|
| Rented H100, 8B model, **100% utilisation** | **$0.22** |
| Hosted, same model class | **$0.02** |
| Rented H100 at realistic utilisation (~4% of a GPU here) | **~$5.60** |

**Eleven times cheaper than your own hardware running perfectly.** It is a pricing-floor problem:
fleet operators reach utilisation a single deployment cannot and price below your marginal
compute cost. Managed 70B endpoints land at $0.90–1.04/M — almost exactly a self-hosted H100's
marginal cost at full utilisation, because that is what fleet hosting *is*.

**Extraction** break-even is ~2,150 docs/day on GPU cost alone, ~3,800 with ops — about 15x the
brief's volume. What arrives sooner is an eval showing an open 70B matches on this schema: ~60%
cheaper, zero infrastructure, no volume threshold.

**Prompt caching is a net loss unless extraction is batched.** The prefix is ideal caching
material, but a request arriving after the TTL is a fresh *write* at 1.25x that no read
amortises. Window extraction into 15–30 minute batches — a design requirement, not a tuning knob.

---

## 5. At 100x and 1000x

Documents per day, with everything else scaled behind it.

**The assumption that breaks first: vectors accumulate at the document rate, not the extraction
rate**, because novelty and dedup embed everything while only extraction is gated.

| Tier | Docs/day | Vectors after 2 years |
|---|---|---|
| 1 | 100,000 | **73M** |
| 2 | 1,000,000 | **730M** |
| 3 | 10,000,000 | **7.3B** |

pgvector's single-node ceiling is ~10M vectors when properly provisioned. **Tier 1 crosses it
inside year one**, despite "only" 100k documents a day — teams size the index off documents they
deeply process and get blindsided by documents they ever saw.

| | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Ingestion | queue table or SQS | **Kafka** — for replayable consumers, not throughput | Kafka, larger |
| Store | single-node Postgres | + read replicas | sharded, plus a lakehouse |
| Vector index | pgvector, migrate in year 1 | managed | sharded, **quantisation mandatory** |
| Filter LLM | hosted | hosted | hosted, or self-host **for capacity** |
| Storage, 2-yr tiered | ~$60–90/mo | ~$600–900/mo | ~$5,900/mo |
| Team | 2–3 | 5–8 | **15–25** |

**Where the money goes:** Tier 1, the LLM (~75%). Tier 2 and 3, **the vector index** — and at
7.3B vectors the spread between object-storage-backed (~$880/mo) and RAM-priced (~$210,000/mo) is
roughly **240x for the same vector count**, exceeding the LLM bill, the Kafka bill and the GPU
fleet combined.

**Costs invisible in a spreadsheet:**

| Trap | Size |
|---|---|
| **S3 request costs** — 4 PUTs/doc at Tier 3 is 1.2B PUTs/month | **~$6,000/mo**, next to a $5,900 storage line |
| **Embedding backfill on a model change** — re-embed the entire corpus, not new documents | Tier 3 year 2: **~$116,800 one-time**, plus 2x index during cutover |
| NAT gateway processing on external calls | ~$2,160/mo at Tier 3 before egress |

**The transitions:** 100k→1M is a *correctness deadline* — move novelty and dedup off pgvector
before the wall, not after. 1M→10M is to price the vector architecture at the count you will
reach, not the one you have.

---

## 6. What this model excludes

Compliance and legal review; data-vendor negotiation time; the cost of being wrong (the largest
excluded item by far); redundancy and failover for the serving path; and any imagery beyond the
200 AOIs, which is the assumption the whole satellite line rests on.

**Measured, not assumed:** the prototype's own extraction ran at **$0.023/document**, which is
where the per-document figures above come from.
