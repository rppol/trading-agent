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
| 2 | Working prototype — GDELT → LLM → API | this repo, `make all` |
| 3 | Failure modes, detection and mitigation | [docs/FAILURE_MODES.md](docs/FAILURE_MODES.md) |
| 4 | Back-of-envelope cost estimate | [docs/COST.md](docs/COST.md) + interactive model on the site |

## The short version

**The headline finding is that GDELT does not contain the signal.** Measured over 675,840
documents and 8,383 domains in seven days: Reuters zero, Cecafé zero, Conab zero, ICO zero,
every coffee trade publication zero — while a radio syndication network supplies 7.8% of the
corpus. The ~20 "tradeable" coffee documents a day are the false-positive floor, not thin
signal. This is an acquisition problem, not an NLP one, and no extraction quality fixes it.

**The volumes in the brief are a misdirection.** 10M AIS pings/day is 116 messages a second.
500 documents a day is about $9 of tokens. Only the imagery is genuinely large, and its cost
is the licence, not the compute.

**Extraction is not prediction.** The LLM turns prose into typed, cited claims. Arithmetic
turns claims into signals. The model never emits a price, a direction it invented, or a
probability — which keeps the output auditable and keeps pretraining contamination out of
the predictor.

**Two clocks, from the first row.** Every record stores `event_time` and `ingest_time`.
Point-in-time reads filter on the second. This cannot be retrofitted, and without it no
backtest is honest.

**Physical evidence is expensive to forge.** An attacker can write an article; they cannot
move 200,000 tonnes of coffee. Cross-modal corroboration is both the confidence model and
the defence against planted news.

## Run it

```bash
make setup                 # uv venv + fastapi, uvicorn. Everything else is stdlib
make test                  # 7 assert-based checks, no framework

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

## Things worth reading the code for

- `store.claims_as_of` — point-in-time replay is one predicate on `ingest_time`
- `pipeline.cluster` — syndication collapse and novelty weighting
- `pipeline.extract` — the verbatim-span gate that rejects invented numbers
- `tests/test_leakage_switch` — measures lookahead instead of warning about it
