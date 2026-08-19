# Failure modes

Every mode below fails **silently**. None throws. Cost blowup looks like a busy day, drift looks
like a quiet market, leakage looks like a good backtest, planted news looks like a scoop, and
starvation looks like latency. So every detector here fires on the *absence or shape* of
something, never on an error.

Each entry is **mechanism → detection → mitigation**. The ones with numbers were found while
building this, not copied from a checklist.

---

## The five the brief names

| Mode | How it manifests here | Detection | Mitigation |
|---|---|---|---|
| **Cost blowup** | Not a bug — a **volume spike arriving exactly when the system is most valuable**, since news volume tracks volatility. Also agentic loops accumulating O(N²) context, where a $0.05 task becomes $5.00 with no error raised | **$/claim, not $/day** — a daily budget alarm fires after the money is gone. Plus cache-hit rate, cascade survival rate, and a hard step and token budget per agentic run | **Governor with graceful degradation, never a kill switch.** Shed components in measured marginal-value order. Going dark during a volatility spike is the worst available outcome |
| **Model drift** | Three things wearing one name: **input** drift (publisher, language, length mix), **vendor** drift (a checkpoint silently updated under a stable name), **concept** drift (identical news, different regime) | Distributional monitors on inputs. **Pin versions and re-run the golden set on a schedule** — a vendor swap is otherwise invisible. IC decay per regime, and the frozen-holdout gap | Version pinning in feature lineage; champion/challenger on shadow traffic; regime-conditioned scoring so a regime change re-weights instead of silently invalidating |
| **Label leakage** | The most dangerous, because it produces **better** numbers. Four routes: syndicated duplicates split across train and test; overlapping label windows at the boundary; **GDELT revising its own archive**; current-vintage macro instead of the vintage that was live | **The one-switch leakage test, in CI** — one flag flips the pipeline between decision-time-correct and leaky, and the IC gap is asserted. Leakage becomes a measured number rather than a warning in prose | Dedup **before** splitting. Time-sliced splits with an embargo equal to the longest label horizon. Snapshot at ingest. Vintage-correct macro. Purged K-fold |
| **Adversarial news** | Two attacks: **manipulation** (plant a plausible story) and **prompt injection** (hide instructions in a document the extractor reads). The second is worse — it turns the pipeline into the attacker's tool | Injection: hidden-text, instruction-span and encoding heuristics, flagged per document. Manipulation: **novelty plus time-to-second-source** — a claim that stays single-sourced past a threshold is either an exclusive or a fabrication | **Break the lethal trifecta:** the extractor is a quarantined reader with **zero tools**, structured-output only, numeric claims gated on a verbatim span. High-conviction signals require **physical** corroboration — an attacker can write an article; they cannot move 200,000 tonnes |
| **GPU starvation** | Hosted: rate limits bind during the same spike. Self-hosted: queue grows unbounded. Either way it presents as latency, then as missing claims — **indistinguishable from a quiet news day** | Queue depth and age. **Claims-per-hour floor with an alert on absence.** Provider 429 rate as a first-class metric. Staleness on every served signal | Batch tier for anything tolerant; keep the fresh path thin. Multi-provider fallback to a cheaper model. Backpressure that sheds lowest-value work. **The payload always carries its own staleness**, so a consumer can tell a quiet market from a stalled pipeline |

**The cross-cutting detector is `alert on absence`.** Every mode above can present as "no signal
today," so the monitors that matter fire on nothing happening: documents-per-batch below a floor,
zero claims for N hours, a publisher gone silent, a scheduled release that never arrived, and —
counter-intuitively — **the gate rejection rate falling to zero**, which almost always means the
gate broke rather than the model became perfect.

---

## Silent absence, found in our own code

**A live instance, found during review.** ICE publishes certified coffee stocks daily at a stable
URL. The parser reads the current text format and **returns `None` for the binary `.xls` format
used before 2024** — without raising. Measured across 1,266 cached files:

| Year | Parsed |
|---|---|
| 2021 | **0%** |
| 2022 | **0%** |
| 2023 | 43% |
| 2024–2026 | ~97% |

`series()` returns only rows it could parse, so a caller requesting 2021–2026 receives 2024
onward **and no indication anything is missing**. Two consequences, both real: a November 2022
figure quoted in the case study cannot have come from this pipeline (which is why two different
values for it appeared in one document), and any finding claiming the full window was computed on
a third of it.

**The general rule this instance proves:** a parser that returns empty on an unrecognised format
is indistinguishable from a world where nothing happened. **Every fetcher must distinguish
`observed_absent` from `not_observed` and fail loudly on an unparsed input** — the same
observation-status discipline the multimodal design requires.

---

## The reference dataset that rewrites its own history

**Mechanism.** USDA's PSD database — the free, canonical source for world coffee production —
serves **only the current vintage**. There is no version, no as-of parameter, and nothing in the
file says it changed.

**Why it manufactures alpha.** Measured on the Colombian rust episode: at the May 2011 price peak,
the published forecast had Colombia recovering to 9.5m bags for 2010/11 and 10.5m for 2011/12.
Actual outturn was 8,525 and **7,655** — the second forecast was **37% too high**. The true figure
did not appear in a USDA table until **November 2013**, a lag of about two and a half years, and
**the price bottomed nine days before it**.

Download the CSV today and the collapse looks plainly observable in 2011. **It was not.** Any
backtest on the current vintage concludes a trader could have seen a shortfall nobody could see,
and books the difference as skill.

**Mitigation.** Snapshot every reference series at ingest and read it bitemporally, exactly like
news. A source without vintages is a source you must vintage yourself.

---

## A lookahead bug wearing the clothes of a bug fix

**Mechanism.** Two document clusters look distinct on Monday. On Wednesday a new article bridges
them and they are genuinely one story. The obvious implementation updates the earlier records to
point at the merged cluster — which is correct for *today's* view and **rewrites what Monday
knew**. A point-in-time read of Monday now returns Wednesday's grouping.

This is the nastiest entry in the register because the change that introduces it looks like
housekeeping, passes review, and improves the present-day output.

**Detection.** Assert that a point-in-time read is **monotone**: re-running an `as_of` query after
new data arrives must return a superset of the same rows, never a *different* grouping of them.

**Mitigation.** Cluster membership is versioned like everything else — a merge writes a new
assertion, it does not update the old one.

---

## The rest, in short

| Mode | Mechanism | Detection | Mitigation |
|---|---|---|---|
| **Fails open under HTTP 200** | GDELT's throttled endpoint returns an *error string* with a 200 status, and a malformed query returns a different error string — both parse as "no news today" | Validate response *shape*, not status code; floor on documents per batch | Bulk files rather than the throttled API; never put a third party on the request path |
| **Syndication counted as corroboration** | The same wire story at forty domains looks like forty sources. Measured dedup ratio 0.121 — **12% is echo** | Cluster before counting; count *independent publishers*, not documents | A publisher-lineage graph; corroboration filters on ownership before it counts |
| **Optical imagery blind when it matters** | The tropical coffee belt is cloud-covered in the wet season — exactly when weather damage happens | Per-AOI observation status; cloud fraction as a first-class field | **SAR primary in wet season**, optical secondary. Where coverage is unavailable the signal **widens its interval** rather than holding its last value |
| **Surprise treated as strength** | A five-sigma outlier is the most informative thing in the stream *if true* — and is also exactly the shape of a fabrication. Scaling conviction with surprise makes the system farmable | Robust distance from trailing consensus using **median and MAD, never mean and standard deviation** — news figures are heavy-tailed and one outlier poisons a mean-based baseline precisely when it matters | **Invert the reflex: high surprise raises review priority, not confidence.** Costs latency on genuine scoops, which is the correct trade |
| **Prompt cache silently stops working** | Minimum cacheable prefix differs by tier (**4,096 tokens on one, 512 on another**) and is **not monotonic across model generations**. Trim a prompt below the threshold and cost silently multiplies | Cache-hit rate as a monitored metric, not a billing surprise | Assert prefix length in CI; alert on hit-rate drop |
| **Wrong instrument** | A regional shock shows up in a **differential**, not flat price. Colombian rust moved the Colombian Milds premium from **+1.5 to +33.6 c/lb** while flat price was noise | Test every signal against the instrument its mechanism implies, before modelling | Instrument selection is part of the claim schema, not an afterthought |
| **A "leading indicator" computed from the thing it leads** | An index derived from the price it is supposed to predict will always appear predictive | Trace every input to a primary source; reject circular derivations | Provenance to source, enforced in the schema |
| **Official record treated as the timely one** | Regulatory publication lags the operative event by days — the gazette is the record, not the news | Compare publication timestamp to effective date | Track the operative event, use the official record only for confirmation |

---

## The one that is not a bug

**A Sharpe ratio of 5.87**, reported in a published study on free public data.

Real macro strategies live between 0.5 and 1.5. A Sharpe near 6 from data anyone can download is
not an edge; it is an un-diagnosed bug — most often leakage, survivorship, or costs omitted.

**Treat any implausibly good backtest as a defect until proven otherwise**, and make that the
default disposition rather than a hopeful investigation. The strongest evidence for this in the
repository is the falsification battery's own verdict: on the measured corpus it **fails its
own K4 gate at 4.2 effective documents/day against a threshold of 5**, and reports that rather
than reaching for a correlation it lacks the power to support.
