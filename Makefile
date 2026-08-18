PY := .venv/bin/python
.PHONY: setup ingest extract export serve test all clean

setup:
	uv venv -q .venv && uv pip install -q --python $(PY) -r requirements.txt

ingest:            ## pull GDELT GKG batches into the store (BATCHES=672 for 7 days)
	$(PY) -m signals.cli ingest --batches $(or $(BATCHES),96)

extract:           ## run the LLM over stored documents (BACKEND=claude-cli|replay)
	$(PY) -m signals.cli extract --backend $(or $(BACKEND),claude-cli)

export:            ## emit web/data/*.json and stage docs for the site
	$(PY) -m signals.export
	mkdir -p web/docs && cp docs/*.md web/docs/

serve:             ## API + site on :8000
	.venv/bin/uvicorn signals.api:app --port 8000 --reload

test:
	$(PY) tests/test_pipeline.py

all: ingest extract export test

clean:
	rm -rf data/signals.db web/data web/docs
