# Failure modes

Ordered by how specific they are to *this* system. The first five are the ones a generic
MLOps checklist will not contain, and each was found or confirmed while building the
prototype. The generic-but-real ones follow in a table.

Each entry: **mechanism → detection → mitigation.**

---

## 1. Trusting a model's summary of the evidence — twice, including here

**This entry has now been triggered by its own author on two separate occasions, and the
second one is why the lesson changed.**

**First instance.** An earlier draft asserted that standard LLMs score 65–70% predicting price
direction from historical text against 50–55% for era-matched models, concluding that
pretraining contamination accounts for roughly the whole apparent alpha of a news backtest.
The figure came from a summarising model's reading of the paper. The abstract of He, Lv, Manela
& Wu (2025), [arXiv:2502.21206](https://arxiv.org/abs/2502.21206), says the opposite, verbatim:

> "…ChronoBERT and ChronoGPT's real-time outputs achieve Sharpe ratios comparable to a much
> larger Llama model, **indicating that lookahead bias is modest**."

**Second instance — committed in the very section written to confess the first.** This document
twice stated that Pontes et al., [arXiv:2507.03350](https://arxiv.org/abs/2507.03350), reports
50.63% returns over 28 months and *"never mentions transaction costs or slippage."* Extracting
the PDF's text stream and grepping it returns:

> "…important to note that **in our analysis we assume commission fees of 0.05% of the traded
> value**"

The paper models costs. The claim was false. The abstract omits costs; the methodology does not —
which is exactly the shape of an assertion made from a summary.

**What settled it is the important part.** A fetch-and-summarise pass over that PDF reported "no
mention of transaction costs found." A second reviewer reported the commission sentence. Two
model readings of the same document contradicted each other, and **only a deterministic text
extraction and a `grep` resolved it.** That is the argument for the verbatim-span gate,
demonstrated on the author rather than on the pipeline.

**Why two instances change the conclusion.** One is an error and the remedy is care. Two of the
identical failure, the second inside the paragraph apologising for the first, is a **systemic
defect**, and vigilance demonstrably does not fix it. The remedy has to be mechanical:

- **A citation is a quotation, not a link.** Any number attributed to a source carries a
  verbatim string that a machine can check against the source text.
- **Never assert a negative from an abstract.** "The paper does not address X" requires a
  full-text search, because absence in a summary is not absence in a document.
- **Prefer `grep` to a reader.** Where a claim is checkable mechanically, check it mechanically.
  A model summarising a PDF is a lossy compressor, and the loss is silent.

**The generalised failure.** Anywhere a model summarises and a human acts on the summary without
opening the source, there is an unaudited claim. It is invisible because the summary is fluent,
plausible, and usually directionally right — all three were true here, twice.

**Mitigation for the actual risk this was about.** Contamination remains a **hypothesis to
measure, not a quantity to assume**. Glasserman & Lin
([arXiv:2309.17322](https://arxiv.org/abs/2309.17322)) do document a look-ahead bias and a
distraction effect from named entities across 181,908 headlines, and find anonymisation helps.
So: mask entity names, dates and price levels in extraction, run the backtest era-matched, and
report the gap as a measured number.

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

**Mitigation.** Near-duplicate collapse before scoring; novelty as a first-class weight — **with the sign
treated as an open question**, since the evidence in ARCHITECTURE §1b suggests it should be
inverted;
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

## 9. Prompt caching that silently stops working

**Mechanism.** Cached prefixes require a **minimum length**, and that minimum differs per model —
4,096 tokens on the cheap workhorse tier, 512 on the frontier tier. It is **not monotonic across
generations**, so intuition is no guide. Below the threshold, caching does not error. It
**silently no-ops**: no warning, both cache counters return zero, and every call bills at full
input price indefinitely.

**Why it survives review.** The failure is introduced by an improvement. Someone tightens the
extraction prompt from 4,200 tokens to 3,900, the output quality is unchanged or better, tests
pass, and the inference bill multiplies roughly tenfold on the prefix. Nothing in the diff, the
tests, or the logs mentions caching.

**Detection.** Assert `cache_read_input_tokens > 0` in CI on a representative call, and alert on
it in production. A prefix-length regression test is one line and catches the whole class.

**Mitigation.** Keep the frozen prefix comfortably above the threshold for the *specific* model in
use — deliberately, with a comment saying why — and pin the model. Also, sort every serialised
structure and keep timestamps, request ids and anything else non-deterministic **below** the cache
breakpoint. A `datetime.now()` in a system prompt is the most common cause of a permanent 0% hit
rate, and it presents identically: no error, just a larger bill.

**Related trap in the same family.** A gate-changing feature flag can invalidate the cache
wholesale. Decide such flags once, pipeline-wide, rather than per document.

---

## 10. The reference dataset that silently rewrites its own history

**Mechanism.** USDA's PSD database — the free, canonical, machine-readable source for world
coffee production — serves **only the current vintage**. Historical figures are revised, and the
download gives you today's belief about 2011 rather than 2011's belief about 2011. There is no
version, no as-of parameter, and nothing in the file says it has changed.

**Why it manufactures alpha.** Measured on the Colombian rust episode: at the May 2011 price
peak, the published USDA forecast had Colombia **recovering** to 9.5m bags for 2010/11 and 10.5m
for 2011/12. The actual outturn was 8,525 and **7,655** — the second forecast was **37% too
high**. The true figure did not appear in a USDA table until **November 2013**, a lag of roughly
two and a half years, and the price bottomed nine days before it.

Download the CSV today and the collapse looks plainly observable in 2011. **It was not.** Any
backtest built on the current vintage will conclude a trader could have seen a shortfall that
nobody could see, and will book the resulting edge as skill.

This is the same defect as GDELT rewriting its archive, in a dataset with far more authority —
and it is worse, because a research team is more likely to trust it and less likely to check.

**Detection.** Compare the current vintage against a dated archived report for the same period.
A discrepancy is not an error in either; it is the revision, and its size is the size of the bias
your backtest inherits.

**Mitigation.** The reference series must be reconstructed from **dated archived publications** —
the semi-annual circulars and country reports as published — not from the current bulk download.
That is slower and it is the only version that is point-in-time. It is also precisely what the
two-clock design in ARCHITECTURE §3 exists to enforce: an official estimate is a **claim with an
ingest time**, not a fact, and storing it as a fact destroys the ability to ask what was knowable.

---

## 11. Testing a signal against the wrong instrument

**Mechanism.** An origin-scoped supply claim is a claim about that origin's **differential**, not
about the benchmark future. Flat price is dominated by Brazil, the dollar and macro flows the
claim is silent on. Evaluate an origin signal against flat price and a real effect is discarded
as noise.

**Measured.** Colombian rust moved the Colombian Milds premium from **+1.5 to +33.6 c/lb** with
essentially zero lag, while contributing nothing identifiable to flat price — which rallied on a
general commodity boom in which coffee lagged cotton, wheat and maize, and in which robusta,
untouched by that rust, rallied nearly as much as arabica.

**Detection.** For any signal carrying a `region`, run the evaluation against the differential
and the calendar spread as well as flat price, and report all three. A signal that works only on
flat price for an origin-specific claim should be treated as suspect, not as a finding.

**Mitigation.** Budget for the instrument. Free point-in-time differential and spread series do
not appear to exist, which makes acquiring them a precondition for honest evaluation rather than
an optimisation.

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
that anyone can download. Real macro strategies live between 0.5 and 1.5. It is a single-author
unreviewed preprint, and a replication reports mean accuracy of 51.2% with an AUC of 0.500.

If free public data produced a Sharpe near 6, it would be arbitraged within a quarter. So
the number is not a result, it is a defect report — some combination of unmodelled costs, a
sentiment model trained on data postdating the test window, and GDELT's silent archive
revision.

The practical rule: **an implausibly good backtest is a bug until proven otherwise, and the
burden of proof is on the result.** Treating a suspiciously high Sharpe as good news rather
than as a failing test is, on its own, the most expensive failure mode in this document.
