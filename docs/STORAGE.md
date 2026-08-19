# Storage and indexing

The layer under everything else: what gets stored, in what, indexed how, and embedded with what.
Sized for the brief's actual corpus — roughly **1–4M documents and ~3.6M vectors after two
years** — with the thresholds named where a different answer takes over.

---

## 1. No summarisation before indexing, and it is not a close call

A common RAG pattern summarises each chunk before embedding it. **Here that would break the one
property the system depends on**, because the grounding gate verifies a claim's evidence against a
*verbatim* span. A summary is a paraphrase; there is nothing left to check against.

The shipped precedents all point the same way — **compress for matching, never for storage**:

- **Anthropic's contextual retrieval** prepends a 50–100 token generated blurb *in front of* the
  raw chunk and never replaces it. Measured: top-20 retrieval failure **5.7% → 3.7%** with
  contextual embeddings, **→ 2.9%** adding contextual BM25, **→ 1.9%** with reranking. Cost is
  about **$1.02 per million document tokens** with prompt caching.
- **Anthropic's Citations API** chunks at sentence granularity and cites those sentences —
  reporting up to 15% recall improvement over custom implementations, and one customer's
  source-hallucination rate going from 10% to **0%**.
- **LlamaIndex's own summary index** is the instructive case: it embeds summaries only to *route*
  to a document, then returns the **full raw nodes** for synthesis. Even a summarisation-forward
  design does not answer from the summary.

**Propositionalisation** (Dense X Retrieval) is a real retrieval win — Recall@5 rising 34.3% →
46.3% for weak retrievers, with downstream QA up 5–8 points — and it is cheap at production time,
one small-model forward pass per passage rather than an LLM call per proposition. **But
propositions are LLM-paraphrased atomic facts, not verbatim spans**, so as the primary retrieval
unit they reproduce exactly the grounding problem summarisation does. If adopted later, it must be
a *secondary* index that always points back to the source char-offset — never the object the gate
checks.

**Decision: embed raw chunks, optionally with a prepended context blurb. Never summarise-and-replace.**

---

## 2. Embeddings: multilingual is the binding constraint, and it excludes the finance models

At this volume embedding cost is a few dollars a month for every option, so **price is not a
selection criterion.** Language coverage is — sources include Portuguese, Vietnamese and Spanish.

| Option | Dims | Multilingual | Verdict |
|---|---|---|---|
| **Cohere embed-multilingual-v3.0** | 1024 | 100+ languages, real track record | **default** |
| Cohere embed-v4.0 | 256–1536 (MRL) | same claim, multimodal | fine if pricing resolves favourably |
| OpenAI text-embedding-3-large | 3072 | better, but not multilingual-first | acceptable fallback |
| **Qwen3-Embedding-4B/8B** | up to 4096 (MRL) | 100+ languages, Apache-2.0, best open multilingual MTEB | **self-host option if residency demands it** |
| BGE-M3 | 1024 + sparse + multi-vector | 100+ languages, MIT | strong open alternative |
| e5-mistral-7b, nomic-embed-text-v1.5 | — | **English only** | disqualified outright |

**The finance-specific models are real and do not fit.** `voyage-finance-2` and `Fin-E5` both show
genuine finance-retrieval lift over general models. **Neither has demonstrated PT/VI/ES coverage** —
finance specialisation and multilingual coverage pull in opposite directions, and nothing found
satisfies both. So the primary index stays multilingual; if finance-domain lift is wanted, take it
from a **downstream reranker or second-stage retriever**, not by swapping the embedder.

**Matryoshka: real, but PCA is the honest comparison.** An independent benchmark across 8 BEIR
datasets found truncation to 256 dims retains **94–96%** of NDCG@10; 64 dims retains only 71–83%;
32 dims, 46–68%. And **plain post-hoc PCA matched or beat MRL truncation at every tested size** —
MRL's real advantage is needing no fitted projection or calibration data, not better retention.
**Truncate to 256–512 for storage savings; do not go below 128 without measuring your own recall.**

---

## 3. pgvector is right here — and the cliff lands almost exactly on our corpus

The most useful data point comes from a competitor: **Qdrant puts pgvector's practical ceiling at
~10M vectors.** ClickHouse's engineering write-up agrees — comfortable to ~1M untuned, fine to
~10M tuned, reconsider past ~100M. At 3.6M we sit inside the "fine with tuning" band on every
source that named a threshold, including the hostile one.

**But there is a measured cliff, and it is a RAM cliff wearing a vector-count costume.** On a 32GB
box at 1536 dims with HNSW (m=32, ef_construction=128):

| Vectors | Index size | QPS |
|---|---|---|
| ≤2M | — | ~2,100 |
| 2.5M | 19 GB — just over `shared_buffers` | **−45%** |
| 3M | 23 GB | **−95%, down to 102 QPS** |

**The buffer hit ratio stayed above 98% throughout**, which is why this is nasty: nothing looks
wrong in the metric people watch. At 1536 dims our 3.6M vectors are roughly **27GB of index**, so
this is not a hypothetical — it is our configuration.

**Mitigations, in order:** `halfvec` for the index (roughly halves the footprint), `shared_buffers`
provisioned comfortably above the index size (32GB+), and Matryoshka truncation to 512 dims if
recall permits. Index *builds* also stall or OOM when the HNSW graph outgrows
`maintenance_work_mem` mid-build — size it deliberately rather than leaving the default.

**So the two ceilings reconcile: ~10M vectors if provisioned properly, ~3M if not.**

**pgvectorscale is declined**, and the reasons are specific: its headline numbers (28x lower p95,
16x throughput at 50M vectors) are **all measured against Pinecone, never against plain pgvector
HNSW** — the comparison that would justify adopting it does not exist in the primary source, and
no independent reproduction was found. It is also **unavailable on AWS RDS**, and its filtering
requires small-integer labels declared at index-creation time. Revisit only when self-hosting
Postgres and holding a measured wall.

**If we ever outgrow it, the destination is Qdrant** — its filtering is the best-engineered of the
group (filter evaluated *inside* HNSW traversal, with an ACORN fallback) and it is self-hostable
with no lock-in. **Turbopuffer is the wrong tool at this size** regardless of its $16/month floor:
its value is S3-backed tiering at multi-tenant scale, and at ~22GB you get none of that while
paying **444ms p90 on a cold query** against pgvector's sub-20ms.

---

## 4. Filtered vector search, which degrades much worse than expected

Our filters are commodity, date range, publisher and entity — **exactly the selective-AND case
that breaks naive approaches.**

- **Pre-filtering** removes nodes before traversal and fragments the HNSW graph; paths between
  surviving points break and traversal dead-ends short of the true neighbours.
- **Post-filtering** runs ANN first and discards non-matching results from a fixed top-K — under a
  selective filter this returns too few, **or zero, silently**, while matches exist elsewhere in
  the index.

Quantified: a single broad-value filter drops recall to **90.8%**; an **AND over two broad values
drops it to 39.7%**.

**So pgvector 0.8+'s iterative index scans are load-bearing, not optional** — they pull more
candidates until the filter is satisfied instead of filtering a fixed top-K, which is the direct
fix for the silent undercount. Keep the filterable set small and consistently typed: broad filters
degrade toward brute force, over-narrow ones fragment the graph, and speculative filter fields
cost recall for nothing.

### The metadata that earns its place

| Field | Why |
|---|---|
| `document_id`, `claim_key` | linkage, dedup, updateability |
| `publisher`, `publisher_independence_id` | **the corroboration filter** — excludes syndicated re-reports of one primary source |
| `language` | a hard constraint, not a similarity question |
| `event_time`, `ingest_time` | the two clocks, and the two most common filter predicates |
| `entity_ids[]` | the primary selective-AND case |
| `geo`, `document_type`, `section_path` | region scoping, downstream weighting, landing a check in the right part of a long document |
| **`char_start`, `char_end`** | **required** — this is what makes "embed raw, never summarise" usable by the gate |
| `extractor_version`, `prompt_version`, `trace_id` | lineage. Honestly flagged: these are for debugging and reprocessing, **not retrieval quality** |
| `confidence`, `observation_status` | ranking and the multimodal absence semantics (PIPELINE.md §1b) |

---

## 5. Claims live in plain Postgres, with plain SQL bitemporality

**Postgres, and it is not close at this scale.**

- **DuckDB** wins on columnar OLAP scans, which is not this workload — point lookups, a
  point-in-time filter, joins, and vector search in the same transaction. The right pattern is
  Postgres as system of record with DuckDB attached later for analytics, not DuckDB as primary.
- **Iceberg/Delta** differences "only matter at 100TB+", and **frequent small commits are a
  documented failure mode** — small-file proliferation and metadata bloat needing compaction
  tooling. At low tens of GB it is the wrong tool outright.
- **SQLite** is single-writer; not a contender for concurrent ingest plus query plus vector search.

**Bitemporality: use range types, not an extension.** There is no mainstream maintained bitemporal
Postgres extension — `temporal_tables` covers only one axis, and `pg_bitemporal` is a
single-maintainer project, which is too much risk for the most correctness-critical table in the
system. Postgres has no native SQL:2011 system versioning, and PG18's `WITHOUT OVERLAPS` covers a
single axis only.

The shipped pattern is two `tstzrange` columns with a GiST exclusion constraint:

```sql
EXCLUDE USING gist (
  claim_key       WITH =,
  effective_range WITH &&,   -- event_time axis
  asserted_range  WITH &&    -- ingest_time axis
)
```

**Index with a composite B-tree, not BRIN.** `(claim_key, ingest_time DESC)` serves both the
`ingest_time <= :as_of` filter and "latest version per claim." BRIN's benefit appears at tens to
hundreds of millions of rows — one benchmark at ~500M rows had B-tree take a query from 20s to
2ms while BRIN gave no improvement. Revisit past ~50–100M rows.

**Append-only, and budget for its cost.** Never `UPDATE`; insert a new version keyed by
`(claim_key, ingest_time)`. This is what bitemporal correctness requires and it is already how the
prototype behaves. The documented cost is table and index bloat, so build the materialised
"current" view and vacuum monitoring **on day one** — cheap now, expensive to retrofit under bloat.

---

## The stack

**One Postgres instance, 32–64GB RAM**, holding everything:

- **Claims** — append-only, two `tstzrange` axes with a GiST exclusion constraint, composite B-tree
  `(claim_key, ingest_time DESC)`, materialised current view, routine vacuum.
- **Chunks and embeddings** — same database, `pgvector` with `halfvec`, HNSW, **iterative index
  scans enabled**, metadata from §4 on B-tree/GIN, `char_start`/`char_end` for the gate.
- **Embeddings** — Cohere multilingual v3 managed; Qwen3-Embedding-4B self-hosted only if
  residency requires it.
- **Analytics** — `pg_duckdb` or Parquet export *later*, when aggregations actually get slow.

**Declined:** summarise-then-embed, propositions as the primary unit, English-only embedders,
finance-specific embedders as primary, a dedicated vector DB on day one, pgvectorscale,
Turbopuffer, DuckDB/SQLite/Iceberg as primary store, a bitemporal extension, and BRIN on
`ingest_time` at this row count.
