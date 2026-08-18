# Failure modes

Ordered by how specific they are to *this* system. The first five are the ones a generic
MLOps checklist will not contain, and each was found or confirmed while building the
prototype. The generic-but-real ones follow in a table.

Each entry: **mechanism → detection → mitigation.**

---

## 1. Trusting a model's summary of the evidence — including our own

**This entry began as a different claim, and correcting it is the most instructive thing in
this document.**

An earlier draft asserted that research on chronologically consistent language models measured
standard LLMs at 65–70% accuracy predicting price direction from historical text against 50–55%
for era-matched models, and concluded that roughly the entire apparent alpha of a news backtest
is pretraining contamination.

**That figure was wrong.** It came from a summarising model's reading of the paper, not from the
paper. The abstract of He, Lv, Manela & Wu (2025), [arXiv:2502.21206](https://arxiv.org/abs/2502.21206),
says the opposite, verbatim:

> "In an asset pricing application predicting next-day stock returns from financial news, we
> find that ChronoBERT and ChronoGPT's real-time outputs achieve Sharpe ratios comparable to a
> much larger Llama model, **indicating that lookahead bias is modest**."

The same paper stresses that lookahead bias is "model and application-specific."

**Why this belongs in a failure-mode register rather than a quiet edit.** The mechanism that
produced the error is exactly the one this system exists to defeat: an unverified paraphrase
from a language model was promoted to a load-bearing conclusion and propagated into two
documents. The verbatim-span gate in the pipeline exists because a model's summary is not
evidence. That standard was applied to the pipeline's inputs and not to its authors.

**The generalised failure.** Anywhere a model summarises a source and a human acts on the
summary without opening the source, you have an unaudited claim. It is invisible because the
summary is fluent, plausible, and directionally reasonable — this one was all three, and it
supported a conclusion that felt sophisticated.

**Detection.** Every quantitative claim in a research artefact carries a citation, and a
citation means a quotation that can be checked, not a link that gestures at a paper. Spot-check
a random sample against primary sources. A claim whose number cannot be found in the cited
document is treated exactly as the pipeline treats an ungrounded extraction: rejected.

**Mitigation, and what the real risk is.** Contamination is a **hypothesis to test, not a
quantity to assume**. Glasserman & Lin ([arXiv:2309.17322](https://arxiv.org/abs/2309.17322))
do document both a look-ahead bias and a *distraction* effect from named entities in model
sentiment over 181,908 Reuters headlines, and find that anonymising company identifiers can
improve performance. So the controls are cheap and worth adopting regardless of effect size:

- **Mask entity names, dates and price levels** in the extraction prompt. If extraction quality
  depends on the model recognising *which* drought this was, that dependence is measurable.
- **Run the backtest twice** — once with the production model, once era-matched — and report the
  gap as a measured quantity rather than asserting it.

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

## 6. Surprise treated as strength, instead of as a reason to look harder

**Mechanism.** A claim far from the running consensus — a crop estimate five standard
deviations below every other forecast — is the most informative thing in the stream *if true*.
The natural implementation weights it heavily. That is also precisely the shape of a fabricated
number, and a system that scales conviction with surprise is a system that can be farmed: get
one outlier number into one syndicated feed and the signal moves for you.

**Detection.** Robust distance from the trailing consensus for that metric, region and crop
year, using **median and median-absolute-deviation, never mean and standard deviation** — news
figures are heavy-tailed and a single outlier poisons a mean-based baseline exactly when you
need it.

**Mitigation.** Invert the reflex: **high surprise raises review priority, not confidence.** An
outlier is held as provisional and requires corroboration from an independent owner group
before it can move a signal. This costs latency on genuine scoops, which is the correct trade —
the scoop is still captured, just a few hours later and with its evidence attached.

---

## 7. Cluster history rewritten on merge

**Mechanism.** Two document clusters look distinct on Monday. On Wednesday a new article
bridges them and they are genuinely one story. The obvious implementation updates the earlier
rows to the surviving cluster id. Every backtest that replays Monday now sees one cluster —
which is not what was known on Monday. Cluster size feeds novelty, corroboration count and
confidence, so the contamination propagates into every signal that depends on them.

**Why it is nasty.** It is invisible. The data is more *correct* after the merge, the code
reads as a tidy-up, and no test fails. It is a lookahead bug wearing the clothes of a bug fix.

**Detection.** Assert that no historical replay ever returns fewer clusters than an earlier
replay over the same window — the same monotonicity property the leakage test already asserts
for claims.

**Mitigation.** Never update membership. Append a merge record carrying its own `ingest_time`
and resolve cluster identity at read time, filtered by the same clock as everything else. The
merge becomes a fact you learned on Wednesday rather than a retroactive correction to Monday.

---

## 8. Believing you can spot a fabrication at first sight

**Mechanism.** The temptation is a credibility model that scores an unsourced single-source
claim at t=0. **From the text alone, at first sighting, you cannot reliably distinguish a
genuine exclusive from a fabrication.** Both are single-sourced, both are surprising, and both
read as confident prose. A system that claims otherwise has encoded a guess as a score.

**Detection and mitigation — make it observable over time instead.**

- **Structural, not judgemental, features.** Whether the claim carries a named speaker whose
  organisation resolves, and whether that organisation is an official statistical source, are
  facts about the document, not opinions about its truth. A checkable claim is a different
  object from an unsourced assertion.
- **A prior earned from outcomes.** Track, per source, how often its exclusives are later
  corroborated. A previously unseen domain gets a low prior by construction rather than by
  someone's judgement.
- **Retroactive resolution.** When the authoritative series prints, score every prior claim
  against it and credit or debit the originating source. After a year this is an empirical
  liar-detector that no amount of first-sighting text analysis can approximate.
- **A policy, not an algorithm, at the boundary:** never emit a tradeable signal from a single
  uncorroborated source. Publish it as provisional with a visible corroboration state, and
  promote it when an independent owner group confirms.

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
