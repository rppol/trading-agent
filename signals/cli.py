"""Thin CLI so the Makefile has something to call."""
import argparse
import json

from .store import connect, upsert_documents, insert_claims, docs_as_of, claims_as_of
from .pipeline import fetch, cluster, extract, EXTRACTOR


def main():
    ap = argparse.ArgumentParser(prog="signals")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ingest"); i.add_argument("--batches", type=int, default=96)
    e = sub.add_parser("extract"); e.add_argument("--backend", default="claude-cli")
    sub.add_parser("restore")
    a = ap.parse_args()
    conn = connect()

    if a.cmd == "ingest":
        docs = cluster(fetch(n_batches=a.batches))
        new = upsert_documents(conn, docs)
        for d in docs:
            conn.execute("UPDATE documents SET cluster_id=?, novelty=? WHERE doc_id=?",
                         (d["cluster_id"], d["novelty"], d["doc_id"]))
        conn.commit()
        # Snapshot the STORE, not this run's fetch. Writing the fetch made the
        # fixtures only as large as the last window: one quiet six-hour pull
        # truncated the committed 33-document replay corpus that the demo, the
        # tests and the published site all read from. The store is append-only
        # by upsert, so this can grow and can never shrink.
        held = [dict(r) for r in docs_as_of(conn)]
        for r in held:
            r["raw"] = json.loads(r["raw"])   # stored as text, fixtures carry the object
        with open("fixtures/documents.jsonl", "w") as f:
            for d in held:
                f.write(json.dumps(d) + "\n")
        print(json.dumps({"seen": len(docs), "new": new, "corpus": len(held),
                          "clusters": len({d['cluster_id'] for d in docs})}))

    elif a.cmd == "restore":
        # A fresh clone has no data/ directory (it is gitignored), so `make export`
        # produced an empty site while the README claimed it replayed the fixtures.
        # The only restore path lived inside the CI workflow. This is that path.
        docs = [json.loads(l) for l in open("fixtures/documents.jsonl")]
        n = upsert_documents(conn, docs)
        for d in docs:
            conn.execute("UPDATE documents SET cluster_id=?, novelty=? WHERE doc_id=?",
                         (d["cluster_id"], d["novelty"], d["doc_id"]))
        conn.commit()
        claims = [json.loads(l) for l in open("fixtures/claims.jsonl")]
        m = insert_claims(conn, claims)
        print(json.dumps({"documents": n, "claims_offered": len(claims), "claims_landed": m}))

    elif a.cmd == "extract":
        docs = [json.loads(l) for l in open("fixtures/documents.jsonl")]
        # Skip what this prompt version already covered. claim_id embeds the
        # extractor semver, so a re-run was idempotent but still paid the model
        # for every document a second time. A prompt bump re-extracts everything,
        # which is the point of pinning the version into the id.
        done = {r["doc_id"] for r in conn.execute(
            "SELECT DISTINCT doc_id FROM claims WHERE extractor = ?", (EXTRACTOR,))}
        todo = [d for d in docs if d["doc_id"] not in done]
        claims, meter = extract(todo, backend=a.backend) if todo else ([], {})
        landed = insert_claims(conn, claims)
        # Snapshot the store, not this run -- the fixtures are the replay corpus,
        # and writing only the new claims would delete every earlier one.
        held = [dict(r) for r in claims_as_of(conn)]
        for r in held:
            r["payload"] = json.loads(r["payload"])
        with open("fixtures/claims.jsonl", "w") as f:
            for c in held:
                f.write(json.dumps(c) + "\n")
        print(json.dumps({"documents": len(docs), "extracted": len(todo),
                          "skipped": len(docs) - len(todo), "claims_new": landed,
                          "claims_total": len(held), **meter}))


if __name__ == "__main__":
    main()
