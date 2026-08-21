# trading-agent

Commodity trading signals extracted from unstructured data — architecture, a working
end-to-end slice, a failure-mode register and a cost model.

**Live site: https://rppol.github.io/trading-agent/**

Built for the Mintelligence assignment: ingest heterogeneous commodity data (exchange ticks,
positioning, multilingual news, satellite imagery, AIS, social, macro), extract trading
signals with LLMs and multimodal models, and serve a research platform at sub-second for
cached queries and minutes for fresh inference.

---

## The four deliverables

| # | Deliverable | Where |
|---|---|---|
| 1 | Architecture document with diagrams | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| 2 | Working prototype — GDELT → LLM → API | [the code](#the-code), `make all` |
| 3 | Failure modes, detection and mitigation | [docs/FAILURE_MODES.md](docs/FAILURE_MODES.md) |
| + | What was tested, and what died | [docs/EVIDENCE.md](docs/EVIDENCE.md) |
| 4 | Back-of-envelope cost estimate | [docs/COST.md](docs/COST.md) + interactive model on the site |

## The short version

**Extraction is not prediction.** The LLM turns prose into typed, cited claims. Arithmetic turns
claims into signals. The model never emits a price, an invented direction, or a probability —
which keeps the output auditable and keeps pretraining contamination out of the predictor.

**Two clocks, from the first row.** Every record stores `event_time` and `ingest_time`;
point-in-time reads filter on the second. This cannot be retrofitted — you can always recover
when something happened, never when you learned it.

**Fuse at the claim, never at the tensor.** Text, imagery, AIS and price are commensurable as
*typed claims about a canonical entity*, each carrying a pointer to its own evidence — a character
span, an AOI polygon, a track window. A joint embedding averages a cheap lie with an expensive
fact and is unauditable when the number moves.

**The volumes in the brief are a misdirection.** 10M AIS pings/day is 116 messages a second. Only
imagery is genuinely large, and its cost is the licence, not the compute — **tasking policy alone
is 96% of the gap** between a careless build and a staged one.

**The LLM is 0.2% of the bill.** Licensing and people are 53–76%.

**Most of what we believed did not survive measurement.** A gas→urea→coffee chain where the cause
peaked six months *after* the effect. A "buried" ICE rule Reuters reported the next day. A
positioning hypothesis that was real in magnitude and backwards in mechanism. A parser silently
reading 0% of two years of its own source. [EVIDENCE.md](docs/EVIDENCE.md) is the record, and it
is the part that distinguishes this from a design nobody tried to falsify.

## Run it

```bash
make setup                 # uv venv + deps (uv must be on PATH)
make test                  # 14 assert-based checks, no framework

make export && make serve  # replay the committed fixtures, serve API + site on :8000
```

Then:

```bash
curl -s localhost:8000/v1/signals/coffee | jq         # cached path
curl -s 'localhost:8000/v1/signals/coffee?as_of=2026-08-16T00:00:00+00:00' | jq
curl -s 'localhost:8000/v1/claims?signal=supply_risk' | jq   # evidence ledger
curl -s -XPOST localhost:8000/v1/refresh                     # fresh inference, async
```

To pull fresh data and re-extract (needs the `claude` CLI on PATH — no API key, no spend):

```bash
make ingest BATCHES=672    # 7 days of GDELT 15-minute batches, cached on disk
make extract               # LLM extraction via `claude -p`
make export
```

## Design notes

**No API key anywhere.** Extraction shells out to `claude -p --output-format json`, so it
runs on an existing subscription. A `replay` backend reads committed fixtures, which is what
CI and reviewers use — deterministic and free.

**No scraping.** GDELT's bulk GKG batches supply titles, quotations, entities, geolocations
and figures. Nothing fetches article HTML, so robots.txt, paywalls and CFAA exposure stay out
of scope. Production replaces this with licensed full text — a commercial decision, costed in
[docs/COST.md](docs/COST.md).

**No Docker, no Kafka, no streaming engine.** SQLite is the bronze store and gives
bitemporal columns and dedup keys for free. At 116 messages a second, anything else would be
infrastructure theatre. The distributed design lives in the architecture document, where
ambition costs nothing.

## Layout

```
signals/
  store.py      SQLite schema, bitemporal reads (as_of filters ingest_time)
  pipeline.py   ingest -> dedup/novelty -> LLM extraction -> aggregation
  api.py        FastAPI: cached, point-in-time, evidence, async refresh, metrics
  export.py     static JSON for the site
  cli.py        make targets
docs/           the three written deliverables
web/            static site (also served by the API locally)
fixtures/       real GDELT documents and real LLM extractions, committed
tests/          assert-based checks incl. the leakage switch
```

## The code

Deliverable 2 is ~1,900 lines of Python. The two files that carry it:

| File | What it is |
|---|---|
| **[signals/api.py](signals/api.py)** | The **API**. `GET /v1/signals/{commodity}` (cached, and point-in-time via `?as_of=`), `/history`, `/v1/claims` (evidence ledger), `POST /v1/refresh` + `/v1/jobs/{id}` (async fresh inference), `/v1/metrics`, `/healthz` |
| **[signals/pipeline.py](signals/pipeline.py)** | The **signal extraction**. GDELT ingest → syndication collapse → LLM claim extraction → grounding gate → scoring |
| [signals/store.py](signals/store.py) | Bitemporal SQLite. `as_of` is one predicate on `ingest_time` |
| [signals/cli.py](signals/cli.py) | What the `make` targets call |
| [tests/test_pipeline.py](tests/test_pipeline.py) | 14 assert-based checks, no framework |
| [fixtures/](fixtures/) | Real GDELT documents and real LLM extractions, committed so a reviewer can run it without a key |

Reading it in one pass:

| Where | Why it is the interesting part |
|---|---|
| [`pipeline.extract`](signals/pipeline.py) | The LLM emits typed **claims**, never a price. Every numeric claim must appear verbatim in the cited span or it is rejected — see `pipeline.ground` |
| [`pipeline.score`](signals/pipeline.py) | Claims become the three signals by **arithmetic**, not by a model. This is where "extraction is not prediction" stops being a slogan |
| [`store.claims_as_of`](signals/store.py) | Point-in-time replay is one `WHERE ingest_time <= ?`. Ten lines that prove no lookahead |
| [`pipeline.cluster`](signals/pipeline.py) | Syndication collapse — the 40th reprint carries no information, so novelty is a signal input |
| [`test_leakage_switch`](tests/test_pipeline.py) | Measures lookahead in CI instead of warning about it in prose |

### The three signals

| Signal | Range | Character |
|---|---|---|
| `supply_risk` | 0–100 | Continuous. Severity × certainty, tagged by driver (`weather_frost`, `disease_pest`, `logistics_port`) and origin |
| `price_pressure` | −100…+100 | Directional, derived in code from a stated physical fact — never extracted from the model |
| `policy_shock` | 0–100 | Discontinuous. Export bans, tariffs, EUDR, with jurisdiction and effective date |
