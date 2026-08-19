# The stack: FastAPI, LangGraph, LangSmith — and what each actually earns

Stack is pinned: **Python, FastAPI, LangGraph, LangSmith, hosted model APIs.** This document
places each component, says where it genuinely earns its place and where it is a thin wrapper
over a function call, and then covers the two things that make the system improve over time:
observability that reaches all the way to outcomes, and a component-improvement loop with
cost-benefit measured rather than assumed.

---

## 1. Where LangGraph earns its place, and where it does not

Being straight about this matters, because wrapping a deterministic pipeline in a graph
framework buys latency, indirection and a new failure surface if the pipeline was never
branching in the first place.

| Stage | Shape | LangGraph? |
|---|---|---|
| Poll → snapshot → dedup → triage | fixed linear sequence, no branching | **a function.** Model it as a node for uniform tracing, but no state machine is doing work here |
| Extraction → grounding gate → store | linear, with a deterministic reject path | **node, thin.** Value is the trace, not the graph |
| **Corroboration hunt** | step count unknown in advance, needs retries, partial results, budget cap | **genuinely a graph.** Cyclic, checkpointed, interruptible |
| **Contradiction resolution** | branch depends on what the disagreement turns out to be | **genuinely a graph** |
| **Analyst review** | human-in-the-loop interrupt, resumed hours later | **genuinely a graph** — this is what checkpointing is for |

So LangGraph's real earnings are **checkpointing, resumability and human-in-the-loop
interrupts** on the three jobs that need them. Using it for the linear path is acceptable
because it gives one uniform tracing surface — but nobody should pretend the linear path needed
a graph. Where a node is a function call, the design says so.

```mermaid
flowchart LR
  subgraph L[Linear: functions, traced]
    P([Poll GKG]) --> S([Snapshot])
    S --> D([Dedup])
    D --> T([Triage])
    T --> X([Extract])
    X --> G([Gate])
  end
  G --> ST([(Claims<br/>Postgres)])
  subgraph A[Agentic: real graphs]
    C([Corroboration<br/>hunt])
    R([Contradiction<br/>resolution])
    H([Analyst review<br/>interrupt])
  end
  ST --> C
  ST --> R
  ST --> H
  C --> ST
  R --> ST
  H --> ST
  classDef lin fill:#3a4a3a,stroke:#a3be8c,color:#e5e9f0
  classDef ag fill:#4a3b52,stroke:#b48ead,color:#e5e9f0
  classDef store fill:#3b4252,stroke:#81a1c1,color:#e5e9f0
  class P,S,D,T,X,G lin
  class C,R,H ag
  class ST store
```

**Session/memory store: not needed, and adding one is a mistake.** A chat agent needs
conversational memory because the user's earlier turns are not otherwise recoverable. This is a
pipeline: its state is the claims table, which is durable, queryable, bitemporal and already the
source of truth. LangGraph checkpoints carry *in-flight* state for the three agentic jobs — that
is execution state, not memory, and it is discarded on completion. Adding a vector "memory" on
top would create a second, unversioned copy of facts that already exist in Postgres with
point-in-time semantics.

**Tool calls.** The extractor gets **no tools at all** — documents are hostile input, and a model
with tool access over attacker-controlled text is an attack surface with a market position
attached. Tools exist only inside the two agentic graphs, and there they are: an allowlist of
named functions, no arbitrary HTTP, no shell, a hard step budget, a wall-clock cap, and every
call traced. A corroboration agent that cannot finish returns partial results rather than
looping.

---

## 2. Observability, which is four planes and not one

LangSmith supplies the first plane well and none of the other three. That distinction is the
whole section.

| Plane | Question | Where it comes from |
|---|---|---|
| **Trace** | what did this call do, cost, and take? | **LangSmith** — spans, tokens, latency, prompt version, retries |
| **Data** | is the input still the input we designed for? | our own: publisher mix, language mix, batch size, doc-length distribution, **arrival gaps** |
| **Quality** | is the output still correct? | gate rejection rate, calibration curve, nowcast error vs consensus, frozen-holdout gap |
| **Cost** | what is a claim costing, and why did that change? | $/claim, $/signal, cache-hit rate, cascade survival rate |

### The lineage that no vendor gives you

The trace tells you an extraction call happened. The official release six weeks later tells you
whether it was right. **Nothing connects those two unless you write the connection down at
extraction time.**

So every claim row carries: `trace_id`, `prompt_version`, `extractor_version`,
`model_version`, `retriever_version`, `embedding_model_version`, and the `ingest_time`
watermark it was built under. When an outcome lands, it attributes backwards through those keys
to the exact configuration that produced it.

Without that, "the model got worse in March" is unanswerable, because you cannot recover which
model, which prompt, and which retriever were live for the claims that failed.

### Alert on absence, not just on error

The failure mode this system has hit repeatedly is **silent zero**: an upstream schema change,
a throttled feed that fails open, a parser that stops matching. None raise an error; all present
as "no signal today," which is indistinguishable from a quiet market.

So the monitors that matter are the ones that fire on *nothing happening*: documents-per-batch
below a floor, zero claims for N hours, a publisher that has gone silent, a scheduled release
that did not arrive, gate rejection rate falling to zero (which usually means the gate broke,
not that the model got perfect).

---

## 3. Fine-tune, or improve the prompt?

The answer differs by stage, and the asymmetry is the reason.

| | **Triage** | **Extraction** |
|---|---|---|
| Volume | everything | ~1–5% survivors |
| Labels | **abundant and free** — gate and extractor outcomes | scarce, needs review |
| Schema stability | binary, stable | **changes as the product evolves** |
| Latency/cost sensitivity | high — it runs on every document | low |
| **Verdict** | **fine-tune, or use a plain classifier** | **prompt, CI-gated** |

**Fine-tune triage.** It is narrow, high-volume, cost-dominant, and drowning in free labels. A
small fine-tuned model — or an embedding-plus-logistic-regression classifier, which is cheaper
still and often competitive on a binary task — removes the largest per-document cost in the
system. Start with the classifier: it trains in seconds, is trivially explainable, and if it is
close to the fine-tune you have saved the whole training pipeline.

**Do not fine-tune extraction, yet.** The schema is still moving; fine-tuning freezes it. A
prompt change ships as a pull request and can be gated in CI in minutes, while a fine-tune needs
a training run, a new eval, and a rollback story. Fine-tune extraction only when *both* hold: the
prompt has stopped improving on the golden set, **and** volume is high enough that inference cost
dominates iteration cost.

**Prompt improvement is a search, so run it as one.** Golden set becomes a LangSmith dataset;
failures are grouped by error type rather than counted; variants are generated against the
failure clusters, not against intuition; each is scored on a **held-out slice**. This is
automatable — the DSPy-style optimisers do exactly this search — but the gate matters more than
the search: any variant that does not beat champion on data it has not seen does not ship.

---

## 4. Improving the retriever and the reranker

These need labels too, and the trick is that the pipeline already emits them.

| Signal | What it labels | Source |
|---|---|---|
| **Was the retrieved claim used?** | retrieval relevance, implicitly | did it contribute weight to a served signal |
| **Analyst clicked through to it** | usefulness | UI telemetry |
| **"Corroborating" doc turned out syndicated** | a hard negative for corroboration retrieval | publisher-lineage check downstream |
| **Novelty said new, dedup later merged it** | a false negative for novelty | cluster merges |
| **Entity resolution unresolved** | a named gap in the alias table | the resolver's own miss log |

That last one compounds and is the moat: **every unresolved mention is a labelled gap**, and
filling it makes the system permanently better at a class of documents. Alias-table growth is
therefore a health metric (LEARNING.md §7), not a chore.

For the reranker specifically: it is worth having only if it changes the *decision*, not merely
the order. Measure it that way — the fraction of cases where reranking altered which claims
entered the served signal. If that fraction is small, the reranker is paying for cosmetics.

---

## 5. Continuous ablation: every component re-earns its place

Run once at design time, an ablation is a benchmark. Run on a schedule, it is the only thing
stopping a pipeline from accreting stages nobody can justify.

Monthly, for each component, measure both sides:

| Component | Pull it out and measure | Typical question it answers |
|---|---|---|
| Reranker | decision-change rate, quality delta, $ saved | is ordering worth the latency and spend |
| Hybrid lexical leg | recall delta on the four retrieval jobs | is BM25 earning its index |
| Frontier extractor → cheaper model | gate rejection rate, claim precision | how much of the quality is the model |
| Corroboration agent | high-conviction precision | does physical corroboration change outcomes |
| Chunking of long docs | claim recall on the long tail | is the long tail worth its complexity |

**The output is a cost-benefit table with a marginal-value-per-dollar column**, and the rule is
blunt: a component whose removal costs nothing measurable gets removed. The temptation is to keep
a stage because it is sophisticated; the ablation is what makes that decision cost-based instead
of aesthetic.

This composes with the budget governor. When news volume spikes — which happens exactly when
volatility makes the system most valuable — the ablation table is already the **degradation
order**: drop the components with the lowest marginal value per dollar first, so the system
degrades along a measured curve instead of going dark.

---

## 6. What the improvement loop changes, in order

The loop does not improve "the system." It changes named components, cheapest and safest first:

1. **The alias table** — pure accumulation, no risk, compounds, and it is the moat.
2. **The triage classifier** — abundant free labels, biggest cost lever, easy rollback.
3. **Calibration** — refit on realised outcomes; uncalibrated confidence is decoration.
4. **The prompt** — CI-gated search against clustered failures.
5. **Retriever weighting** — slowly, on implicit-usage labels.
6. **The reranker** — kept or cut by its decision-change rate.
7. **A fine-tuned extractor** — last, and only when the prompt has plateaued and volume justifies it.

**And nothing in this list touches the grounding gate, the scoring arithmetic, or the two
clocks.** Those are invariants (LEARNING.md §3). An improvement loop allowed near them would
eventually relax them, because relaxing a constraint always improves the metric being watched.
