# Model serving: which model, hosted where, and what it costs

Three distinct workloads with different shapes, and the right answer differs for each. The
headline: **hosted APIs win everywhere at this scale, and the model choice matters far more than
the hosting choice.**

---

## 1. The three workloads

| | **A — Triage** | **B — Extraction** | **C — Embeddings** |
|---|---|---|---|
| Volume | everything (1k–5k/day) | ~1–5% survivors (50–250/day) | few thousand/day + 3.6M backfill |
| Shape | ~1,000 in, ~20 out | ~3,000 fixed prefix + ~8,000 doc in, ~800 out | ~750 tokens each |
| Sensitive to | **cost and latency** | **correctness** | nothing much |
| Batch-tolerant | **no** — it gates the pipeline | depends on the real SLO | **yes**, unambiguously |

---

## 2. Triage: the cheapest tier, and self-hosting can never win

**Use an 8B-class model on a cheap-inference provider (~$0.02/$0.04 per M), or a frontier
nano-tier model (~$0.10/$0.40).** At this volume the choice between them is $3–165/month, so pick
on latency and vendor consolidation, not price.

**What must not happen is pricing triage at a frontier small model.** At ~$1/$5 per M it costs
about **53x more per document** than an 8B-class model, for a binary classification with a
20-token output. That single choice dominates the LLM bill at every scale tier (SCALE.md §2).

**Self-hosting loses at any volume**, and the reason is not utilisation:

| | $/M tokens |
|---|---|
| Rented H100, 8B model, **100% utilisation** | **$0.22** |
| Hosted, same model class | **$0.02** |
| Rented H100 at *realistic* utilisation (~4% of a GPU at these volumes) | **~$5.60** |

**Eleven times cheaper than your own hardware running perfectly.** It is a pricing-floor problem:
fleet operators reach utilisation a single deployment cannot and price below your marginal compute
cost.

**Do not build a fine-tuned classifier yet.** The case for it is real — near-zero marginal cost,
single-digit-millisecond latency, no rate-limit exposure. The case against, at this volume: it
needs a labelling pipeline, a retraining cadence and drift monitoring, while commodity-news
vocabulary drifts (new commodities, new shocks, evolving jargon) in a way a prompt absorbs by
editing three lines. LLM triage costs $3–165/month; the classifier pipeline costs more than that
in one engineer-week. **Revisit at 10–100x volume, or if sub-100ms becomes a hard requirement, or
if rate limits bind.**

*(This refines STACK.md §3, which recommended fine-tuning triage on the strength of its free
labels. The labels are still free and the argument still holds at scale — but at the brief's
volume the token cost being optimised is under $200/month, so YAGNI wins until volume moves.)*

---

## 3. Extraction: hosted frontier, and the break-even is 15x away

**Use a frontier mid-tier model** (~$2/$10 per M). Blended for this document shape that is about
**$2.54/M**, or roughly $225/month at 250 docs/day. A self-hosted 70B at 100% utilisation is
$0.93/M, so break-even is ~36.6% utilisation ≈ **2,150 docs/day**, and ~**3,800/day** once
continuous GPU rental and ops labour are counted.

**Do not cheap out here.** The delta between a frontier mid model and a weaker one is $100–300/month
— immaterial against the cost of a wrong claim in a signals pipeline.

**The one change that arrives before volume does:** if an eval shows an open 70B via a managed
provider matches frontier accuracy *on this schema*, switching cuts cost ~60% with zero
infrastructure work and no volume threshold. That is a golden-set question, not a scale question,
and on a correctness-critical path it is not taken on faith.

### Prompt caching only pays if you batch — otherwise it is a net loss

The extraction prompt is the ideal caching shape: a ~3,000-token fixed prefix (schema,
instructions, few-shot) with a variable document suffix. Cache reads are ~90% off; cache **writes**
cost 1.25x.

- **Clustered into batches:** write the prefix once, every subsequent document reads it at 0.1x.
  The prefix portion drops ~90%, worth ~20% of total extraction cost since the 8,000-token document
  cannot be cached.
- **Trickling in one at a time:** if requests are spaced further apart than the 5-minute TTL,
  **every call is a fresh write that no read ever amortises — you pay 1.25x forever.**

**So windowing extraction into 15–30 minute batches is a design requirement, not an optimisation.**
It also composes with the Batch API where the SLO allows: 50% is the standard batch discount, and
at least one provider documents caching and batching stacking multiplicatively to **25% of
standard rate**.

**But do not let a discount override the product requirement.** Batch latency is measured in hours.
If claims must be actionable within minutes of clearing triage — which the volatility argument
implies — batch is wrong for extraction regardless of the saving. $225/month versus $110/month is
not a decision worth compromising the SLO for.

---

## 4. Embeddings: batch the backfill and stop thinking about it

~$0.02/M for a competitive model. **The 3.6M-document backfill costs $50–350 total, one-time**, and
the batch API halves it. Self-hosting an embedding model to save that is not worth any engineering
time.

Ongoing embedding is sync unless a just-ingested document must be immediately retrievable during
the same extraction pass. Model choice is settled in STORAGE.md §2 — multilingual coverage is the
binding constraint, not price.

---

## 5. If self-hosting ever happens: SGLang, not vLLM

| Engine | When |
|---|---|
| **SGLang** | **The right choice for this workload.** RadixAttention caches a shared fixed prefix with a varying suffix automatically via a radix tree — exactly the extraction prompt shape — with no manual cache configuration. It also overlaps grammar-mask generation with inference, so it holds up better under **constrained structured-output decoding**, which is our decoding mode |
| vLLM | Broadest hardware support, best low-concurrency TTFT, biggest ecosystem. The default if the prompt shape were not so prefix-heavy |
| TensorRT-LLM | Only at sustained high throughput on NVIDIA-only infrastructure, and only if a ~28-minute per-model compile step is acceptable |
| llama.cpp | Not relevant — edge, CPU and single-user. At server concurrency vLLM delivers >35x the requests/sec |

Structured output is a solved problem across all of them: **XGrammar is now the default backend in
vLLM, SGLang and TensorRT-LLM alike**, at sub-40µs/token overhead.

---

## 6. Capacity, and degrading instead of failing

At the brief's volume we are nowhere near any provider's ceiling. **The risk is entirely the burst
case** — a volatility spike delivers a flood of documents at exactly the moment the system matters
most (FAILURE_MODES.md §0).

Design for it regardless of hosting:

- **Client-side token bucket** tuned below the actual tier ceiling, exponential backoff on 429.
- **Prioritise triage over extraction under backpressure.** Triage is cheap, fast and gates
  everything; extraction is low-frequency and already correctness-critical, so a few minutes of
  queue is cheap insurance.
- **Cross-provider fallback for extraction.** If the primary rate-limits during a spike, fail over
  to a managed open 70B, and **re-run through the primary once load subsides** to confirm the
  cheaper model's output. Costs nothing in steady state.
- **Capacity, not cost, is what eventually forces self-hosting.** At Tier 3 the filter needs ~5.9M
  tokens/minute sustained; providers cap on concurrency or set dynamic per-org limits, and no
  budget buys past that.

---

## 7. Vision and ASR, when those modalities arrive

**Do not build satellite analysis on a general vision model.** Benchmarks against Earth-observation
imagery find strong captioning but **poor spatial reasoning — hallucinated objects, miscounting,
failed localisation** — and vendor documentation lists the same limits: approximate rather than
exact localisation, unreliable counting of many small objects, degraded accuracy below ~200px.

The pattern that works is to use a general VLM as the **language layer** — turning a request into a
query — and route the pixel-level counting, change detection and localisation to a **purpose-built
geospatial foundation model** (Prithvi, Clay). This reinforces the AOI decision in ARCHITECTURE.md
§8: process areas of interest with the right model, not scenes with a general one.

Rough vision costs for the language layer: **~$0.0065 per 1MP image**, ~$0.024 for a 4K image on a
high-resolution tier.

**ASR is nearly free.** A hosted Whisper-turbo endpoint runs about **$0.04 per hour of audio** —
roughly 9x cheaper than the reference API and already at marginal-cost territory. **Do not stand up
infrastructure for ASR.**

---

## Summary

| Workload | Choice | Why |
|---|---|---|
| **Triage** | hosted 8B-class or nano-tier, no batch | self-hosting is 11x worse at *perfect* utilisation; it gates the pipeline so latency matters |
| **Extraction** | hosted frontier mid-tier, **batched into 15–30 min windows** for caching | break-even for self-hosting is 15x current volume; batching is what makes caching pay at all |
| **Embeddings** | hosted, batch the backfill | $50–350 one-time; not worth engineering |
| **Vision** | general VLM for language, **GFM for pixels** | general VLMs are documented-weak at counting and localisation |
| **ASR** | hosted Whisper-turbo | $0.04/hr is already marginal cost |

**What would change the answer:** extraction past ~2,000–4,000 docs/day; an eval showing an open
70B matches on this schema (no volume threshold — switch immediately); 10–100x triage volume
making a classifier worthwhile; data residency forcing on-prem; or rate limits binding under burst,
which is a capacity problem rather than a cost one.
