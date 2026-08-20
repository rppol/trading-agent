# Failure modes

**34 modes.** Every one fails *silently* — cost blowup looks like a busy day, drift like a quiet
market, leakage like a good backtest, planted news like a scoop, starvation like latency. So every
detector fires on the **absence or shape** of something, never on an error.

Entries with numbers were found while building this.

---

## The five the brief names

| Mode | Mechanism | Detection | Mitigation |
|---|---|---|---|
| **Cost blowup** | Not a bug — a volume spike arriving when the system is most valuable. Also agentic loops accruing O(N²) context: $0.05 → $5.00, no error raised | **$/claim, not $/day** — a daily alarm fires after the money is gone. Cache-hit rate, cascade survival, per-run step and token budgets | Governor that **degrades, never kills**. Shed in marginal-value order; going dark in a spike is the worst outcome |
| **Model drift** | Three things, one name: **input** (publisher/language/length mix), **vendor** (checkpoint swapped under a stable name), **concept** (same news, new regime) | Distributional monitors. **Pin versions, re-run the golden set on a schedule** — a vendor swap is otherwise invisible. IC decay per regime | Version pinning in lineage; champion/challenger on shadow traffic; regime-conditioned scoring |
| **Label leakage** | Produces *better* numbers, which is why it survives. Four routes: syndicated duplicates across the split, overlapping label windows, **GDELT revising its archive**, current-vintage macro | **One-switch leakage test in CI** — a flag flips decision-time correctness and the IC gap is asserted. Leakage becomes a number, not a warning | Dedup **before** splitting; time-sliced splits with an embargo; snapshot at ingest; vintage-correct macro; purged K-fold |
| **Adversarial news** | Manipulation (plant a story) and **injection** (hide instructions in a document the extractor reads). The second is worse — it turns the pipeline into the attacker's tool | Hidden-text and instruction-span heuristics per document. **Novelty + time-to-second-source**: a claim that stays single-sourced is an exclusive or a fabrication | **Break the lethal trifecta** — extractor is a quarantined reader with **zero tools**, structured output only, numbers gated on a verbatim span. High conviction needs **physical** corroboration |
| **GPU starvation** | Rate limits bind during that same spike; queues grow unbounded. Presents as latency, then missing claims — **indistinguishable from a quiet news day** | Queue depth and age. **Claims-per-hour floor, alert on absence.** 429 rate as a first-class metric | Batch tier where tolerable; multi-provider fallback to a cheaper model; shed lowest-value work. **Every payload carries its staleness** |

**Cross-cutting: `alert on absence`.** All five can present as "no signal today". So the monitors
that matter fire on nothing happening — batch size below a floor, zero claims for N hours, a
publisher gone silent, a release that never arrived, and **gate rejection rate hitting zero**,
which nearly always means the gate broke rather than the model became perfect.

---

## Silent absence, in our own code

ICE publishes certified coffee stocks daily at a stable URL. Pre-2024 files are binary OLE `.xls`;
the parser handles the later text format and **returns `None` without raising**. Across 1,266
cached files:

| 2021 | 2022 | 2023 | 2024–26 |
|---|---|---|---|
| **0%** | **0%** | 43% | ~97% |

`series()` returns only what parsed, so a caller asking for 2021–2026 gets 2023 onward **with no
indication anything is missing**. Consequences: a November 2022 figure quoted in an earlier draft
cannot have come from this pipeline (hence two different values for it in one document), and a
regression's stated period was wrong by two years.

**Rule:** a parser returning empty on an unrecognised format is indistinguishable from a world
where nothing happened. **Fail loudly on unparsed input; distinguish `observed_absent` from
`not_observed`.**

---

## The reference dataset that rewrites its own history

USDA's PSD database serves **only the current vintage** — no version, no as-of, nothing in the
file saying it changed.

Measured on the Colombian rust episode: at the May 2011 price peak the published forecast had
Colombia recovering to 9.5m bags for 2010/11 and 10.5m for 2011/12. Actual outturn 8,525 and
**7,655** — the second forecast **37% too high**. The true figure reached a USDA table in
**November 2013**, ~2.5 years later, and **the price bottomed nine days before it**.

Download the CSV today and the collapse looks observable in 2011. **It was not.** Any backtest on
the current vintage books that difference as skill.

**Mitigation:** snapshot every reference series at ingest and read it bitemporally. A source
without vintages is one you must vintage yourself.

---

## A lookahead bug wearing the clothes of a bug fix

Two clusters look distinct on Monday; on Wednesday an article bridges them and they are one story.
The obvious fix updates the earlier records to point at the merged cluster — correct for *today*,
and it **rewrites what Monday knew**.

The nastiest entry here: the change looks like housekeeping, passes review, and improves
present-day output.

**Detection:** assert point-in-time reads are **monotone** — re-running an `as_of` query after new
data must return a superset of the same rows, never a different grouping.
**Mitigation:** cluster membership is versioned; a merge writes a new assertion.

---

## Backfill destroys point-in-time correctness

A backfill re-processes history and writes `ingest_time = now()`, because that is when the row was
created. Every claim is now stamped as known today.

It corrupts nothing visibly — claims correct, spans real, gate passed. It corrupts **the answer to
a different question**: an `as_of` query before the backfill returns nothing, or looks like
foresight. **A backtest run after a backfill measures a system that could not have existed.**

**Detection:** alert on any write whose `ingest_time` is far from wall-clock; a `provenance` column
making backfilled rows countable.
**Mitigation:** write the `ingest_time` the document *would* have had, from the snapshot's fetch
timestamp — which is why snapshots carry one. Never `now()`.

---

## The moat is also a leakage vector

Entity resolution compounds: every resolved mention is written back to the alias table, so the
system gets permanently better. That is the advantage the design rests on.

It is also **lookahead**. Today's alias table knows a mapping learned in 2026. Replay a 2023
document through it and it resolves a mention nothing could resolve in 2023 — and every aggregate
over that entity is inflated for the past.

**The subtlest entry here:** the fix for a real weakness creates the leak, and no individual row is
wrong.

**Detection:** the leakage test must cover **resolution** — run a window with the current alias
table and with the table as it stood then, and assert resolved-mention count does not rise.
**Mitigation:** **the alias table is bitemporal too.** One column, one predicate. Without it the
moat manufactures alpha.

---

## The rest

### Time and lineage

| Mode | Mechanism | Detection → Mitigation |
|---|---|---|
| **Clock skew** | `ingest_time` stamped by a drifting worker reorders events | Monitor per-worker offset → stamp at the **database** |
| **Crop-year / timezone conflation** | Crop year differs by origin; a local date boundary is not UTC. Wrong boundary shifts a series by a day | Reject naive datetimes at the boundary → store UTC, carry the convention as entity metadata |
| **Publisher domain change** | A rename breaks the syndication graph, so copies of one story start counting as **independent corroboration** | Step change in publishers-per-cluster → lineage keyed on a stable id with domain history |

### The model

| Mode | Mechanism | Detection → Mitigation |
|---|---|---|
| **Context truncation** | Document appended after a long prefix. A prompt that fit last month truncates when the schema grows — **and the number is usually near the end** | Assert token count in CI, count truncations → budget the window; chunk rather than clip |
| **Moving alias pin** | `latest` means the model changes under a stable-looking config | Re-run the golden set on a schedule → pin dated identifiers; treat a model change as a deploy |
| **Schema evolution** | A new enum orphans old claims, or is emitted where old semantics applied | Assert claims parse under their own version → additive-only changes, `extractor_version` per row |
| **Normalisation drift** | A source using different quotes or non-breaking spaces fails the span check on a correct claim | **Gate rejection rate by publisher** — a spike in one source is a normalisation bug → normalise identically on write and check |
| **Fixture drift** | Replay fixtures stop matching live code, and replay is the reviewer's view of the system | CI diffs both paths → regenerate only via an explicit reviewed step |

### Operations and cost

| Mode | Mechanism | Detection → Mitigation |
|---|---|---|
| **Retry storms** | A failing downstream triggers retries, each re-sending a long prompt. Cost scales with the failure | Spend per **successful claim**; retry counter → bounded retries with jitter, circuit breaker that sheds |
| **Prompt-cache threshold** | Minimum cacheable prefix differs by tier (**4,096 vs 512 tokens**) and is **not monotonic across generations**. Trim below it and cost silently multiplies | Cache-hit rate as a monitored metric → assert prefix length in CI |
| **Cache key collision** | Two prompt versions sharing a prefix share a cache entry and serve the wrong semantics | — → version string **inside** the cached region |
| **Entity survivorship** | The graph holds entities existing *now*, so backward-looking aggregates are biased upward | Count entities with a closed validity range → entities valid over `[start, end)` |
| **Calibration drift** | Confidence fitted in one regime stays confidently wrong in the next | Calibration curve per regime, not pooled → refit on realised outcomes |

### Sources and signal

| Mode | Mechanism | Detection → Mitigation |
|---|---|---|
| **Fails open under HTTP 200** | A throttled endpoint returns an *error string* with a 200 status; a malformed query returns a different one. Both parse as "no news today" | Validate response *shape*, not status → bulk files; no third party on the request path |
| **Syndication as corroboration** | One wire story at forty domains looks like forty sources. Measured dedup ratio 0.121 — **12% is echo** | Cluster before counting → count independent **publishers**, via a lineage graph |
| **Optical blind when it matters** | The coffee belt is clouded in the wet season — exactly when weather damage happens | Per-AOI observation status, cloud fraction → **SAR primary in wet season**; widen the interval when uncovered |
| **Surprise treated as strength** | A five-sigma outlier is the most informative thing in the stream *if true*, and exactly the shape of a fabrication. Scaling conviction with surprise makes the system farmable | Robust distance using **median and MAD, never mean and σ** — news figures are heavy-tailed → **high surprise raises review priority, not confidence** |
| **Wrong instrument** | A regional shock lives in a **differential**. Colombian rust moved the Milds premium **+1.5 → +33.6 c/lb** while flat price was noise | Test against the instrument the mechanism implies → instrument selection is part of the claim schema |
| **Circular indicator** | An index derived from the price it predicts always looks predictive | Trace inputs to primary source → provenance enforced in the schema |
| **Official record ≠ timely record** | Regulatory publication lags the operative event by days | Compare publication timestamp to effective date → track the event; use the record for confirmation |

### Market and legal

| Mode | Mechanism | Detection → Mitigation |
|---|---|---|
| **Reflexivity** | Once our flow moves the price, realised IC is partly self-fulfilling — then reverses with size | IC against a benchmark excluding own flow → stated capacity limit and kill-switch, decided early |
| **Licence reaches the index** | Current schedules cover vector stores and retrieval indexes built on licensed data — embedding licensed prices is redistribution | Provenance tags on indexed records → route licensed inputs away from the index |
| **MNPI contamination** | A source that turns out non-public contaminates everything downstream | Provenance to primary source — the compliance control is the debugging lineage → allowlist with a public-availability assertion |

---

## The one that is not a bug

**A Sharpe of 5.87**, reported on free public data. Real macro strategies live at 0.5–1.5.

**Treat any implausibly good backtest as a defect until proven otherwise.** The best evidence here
is our own battery: it **fails its own K4 gate at 4.2 effective documents/day against a threshold
of 5**, and reports that rather than reaching for a correlation it lacks the power to support.
