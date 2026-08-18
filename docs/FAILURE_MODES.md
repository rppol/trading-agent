# Failure modes

Ordered by how specific they are to *this* system. The first five are the ones a generic
MLOps checklist will not contain, and each was found or confirmed while building the
prototype. The generic-but-real ones follow in a table.

Each entry: **mechanism → detection → mitigation.**

---

## 1. The LLM has already read the future

**Mechanism.** A current model knows how the 2024 Brazil drought resolved, which tariffs
survived, and where prices went. Ask it to score a 2024 article and it is not inferring, it
is recalling. Research on chronologically consistent models measures standard LLMs at
**65–70%** accuracy predicting price direction from historical text versus **50–55%** for
era-matched models. The gap is not skill.

**Why it is the worst one.** Every other leakage bug is a coding error you can find by
reading the query. This one lives in the model weights, produces beautiful backtests, is
invisible to code review, and disappears the moment you trade it.

**Detection.** Run the identical backtest twice — once with the production model, once with a
model whose knowledge cutoff precedes the test window. A large IC gap between them *is* the
contamination, quantified. Also: performance that improves as you go further back in time is
diagnostic, since genuine edge decays backwards, memory does not.

**Mitigation.** Era-matched models for historical evaluation. Where that is impractical,
restrict historical claims to *extraction quality* — did it find the right facts — and refuse
to claim predictive power from any backtest a contaminated model touched. Forward paper
trading is the only clean read.

---

## 2. GDELT rewrites its own history, and fails open when throttled

**Mechanism.** Two separate defects, both measured live.

*Revision.* GDELT's archive is not immutable. Backtesting against today's copy uses records
that did not exist at decision time — a lookahead with no code smell whatsoever.

*Fail-open throttling.* The DOC API is limited to roughly one request per five seconds and
answers violations with **plain text under HTTP 200**:

```
Please limit requests to one every 5 seconds or contact ...
```

A client that calls `.json()` and catches the exception logs "0 articles". Its query grammar
fails the same way: parentheses are legal only around OR-groups, so `coffee (sourcelang:english)`
returns the *error sentence* `Parentheses may only be used around OR'd statements.` — again
with status 200. **A quiet news day and a broken ingest are the same observation.**

**Detection.** Require a payload to begin with `{` before treating it as data. Alert on
*absence* — a coffee corpus that drops to zero documents for two consecutive batches is an
outage until proven otherwise. Track batch-stamp continuity, not just row counts.

**Mitigation.** Ingest the bulk 15-minute files, which are unthrottled and MD5-published,
and snapshot every batch immutably at fetch. Cache by batch name so a rerun reproduces the
same corpus. Treat the query API as exploration only, never a dependency.

---

## 3. Syndication counted as corroboration

**Mechanism.** One wire story appears under forty mastheads. Score them independently and a
single press release produces a signal forty times stronger than a single-sourced exclusive.
The system ends up tracking press-release distribution, which correlates with nothing
tradeable. Worse, the same story landing in both train and test folds inflates every
validation metric.

**Measured here.** Deduplication collapsed a 50-document corpus into **24 clusters**. Half
the corpus was echo.

**Detection.** Cluster-to-document ratio per window. A sudden move toward 1.0 means the
deduplicator has stopped working; a move toward 0.1 means a syndication storm.

**Mitigation.** Near-duplicate collapse before scoring; novelty as a first-class weight;
deduplicate **before** splitting folds, and split by story cluster rather than by row. Track
**time-to-second-source** — a claim that stays single-sourced is either an exclusive or a
fabrication, disambiguated by source reputation and physical corroboration.

---

## 4. Adversarial news, and prompt injection as a market attack

**Mechanism.** Anyone who can get a sentence into a syndicated feed can attempt to steer an
extractor that moves money. Two flavours: classic planted news to move a thin market, and
prompt injection aimed at the model itself — hidden text instructing it to score a document
as maximally bullish. Published work on LLM trading agents shows that corrupting the
market-intelligence stage produces position concentration and severe drawdowns.

**Detection.** Injection heuristics over raw text. Single-source high-magnitude claims held
for review. Divergence between text-derived signals and physical modalities. Sudden
novelty spikes from low-reputation domains.

**Mitigation.** Layered, because no single control is sufficient:

1. Structured-output-only extraction with **no tool access** — the model can describe, not act.
2. **Verbatim span gate** — a claim survives only if its quote appears character-for-character
   in the source and any number it states appears inside that span. An invented figure fails
   both. Tested with a fabricated "40% of its crop".
3. Injection-flagged documents contribute **zero weight**, rather than being trusted or
   silently dropped.
4. **Physical corroboration for high conviction.** An attacker can write an article; they
   cannot move 200,000 tonnes of coffee. Forging AIS *and* imagery *and* text coherently is
   orders of magnitude harder than forging text.

The residual risk is honest: AIS is spoofable and GPS jamming is now routine around
sanctioned terminals. Corroboration raises attack cost; it does not eliminate it.

---

## 5. Optical imagery goes blind exactly when it matters

**Mechanism.** Minas Gerais and the Central Highlands are cloud-covered through the wet
season — the season when weather damage happens. An optical-only pipeline returns scenes on
schedule, and they are cloud. Coverage collapses silently during the only events the
imagery exists to detect, and the monitoring plane sees healthy ingest volume throughout.

**Detection.** Track *usable* observation rate per AOI, not scene arrival rate. A cloud-cover
histogram per region per week makes the seasonal hole obvious. Alert when usable
observations per AOI fall below threshold, even while scene counts look normal.

**Mitigation.** Sentinel-1 SAR, which penetrates cloud and is free, as the wet-season
primary with optical secondary — not optical with radar bolted on. Published Vietnamese
smallholder coffee mapping fuses both for exactly this reason. Where coverage is genuinely
unavailable, the signal must *widen its interval*, not quietly hold its last value.

---

## The rest, in short

Real, and each would hurt — but none is peculiar to this system.

| Failure | Mechanism | Detection | Mitigation |
|---|---|---|---|
| **Cost blowup** | News volume spikes with volatility, so spend peaks exactly when you cannot go dark | $/hour against a rolling budget; cost per signal | Cascade routing, per-source token budgets, breaker that degrades to a cheap model rather than stopping |
| **Overlapping-label leakage** | Triple-barrier labels overlap in time, so neighbouring folds share outcomes | Compare purged and unpurged CV scores | Purged K-fold with embargo |
| **Macro revision leakage** | GDP, crop estimates and stocks are revised; today's value was not knowable then | Backtest against vintages and against current values, compare | ALFRED vintages; never current FRED |
| **Hallucinated numbers** | A model states a figure absent from the source | Verbatim-number gate; sampled human audit | Reject rather than score; the gate is in the pipeline |
| **Model drift** | Feature and population shift as the market regime changes | PSI on features, calibration curves, IC decay | Champion/challenger shadow, scheduled recalibration |
| **GPU starvation** | Batch backfill holds GPUs, interactive inference queues behind it | Queue depth and p99 by priority class | Priority classes with preemption, separate pools, admission control |
| **Entity collisions** | "Santos" the port versus the footballer; a coffee company versus the commodity | Precision audits on the resolver | Type-constrained resolution against a curated entity graph |
| **Timestamp conflation** | Publication, observation and market time silently mixed | Assert `ingest_time >= event_time` on write | Two clocks, everything UTC, explicit per query |
| **Silent schema change** | Upstream adds a column; parsing shifts; fields become empty | Alert on absence and on null-rate jumps | Data contracts with a versioned schema, fail closed |
| **Translation drift** | Meaning shifts across 65 machine-translated languages; extraction is weaker in low-resource ones | Back-translation spot checks; per-language golden set | Per-language quality gates; lower confidence priors for weak languages |
| **Reflexivity** | Your own trading moves the market that generates the news you ingest | Signal-conditional impact analysis | Position-size caps, decay monitoring, kill-switch |
| **AOI survivorship** | AOIs chosen because they mattered historically | Out-of-sample AOI holdout | Freeze AOI selection before the evaluation window |
| **Correlated outage** | The volatility spike that makes signals valuable also breaks ingestion | Chaos drills against the ingest path | Degrade to cached with loud staleness, never silent |
| **Derived-data licensing** | A signal computed from ICE/CME prices and redistributed incurs derived-data fees | Lineage query: which outputs touched licensed inputs | Route licensed prices through a marked lineage boundary; legal review before redistribution |
| **MNPI contamination** | Alt data obtained in breach, or a transcript containing MNPI, creates insider-trading exposure | Provenance audit per source | Lineage as a compliance control; vendor warranties; documented sourcing |

---

## The one that is not a bug

**A Sharpe ratio of 5.87.**

That figure is reported in published work applying sentiment to GDELT — free, public data
that anyone can download. Real macro strategies live between 0.5 and 1.5. Another paper
reports 50.63% returns over 28 months and **never mentions transaction costs or slippage**.

If free public data produced a Sharpe near 6, it would be arbitraged within a quarter. So
the number is not a result, it is a defect report — some combination of unmodelled costs, a
sentiment model trained on data postdating the test window, and GDELT's silent archive
revision.

The practical rule: **an implausibly good backtest is a bug until proven otherwise, and the
burden of proof is on the result.** Treating a suspiciously high Sharpe as good news rather
than as a failing test is, on its own, the most expensive failure mode in this document.
