"""Thin CLI so the Makefile has something to call."""
import argparse
import json

from .store import connect, upsert_documents, insert_claims
from .pipeline import fetch, cluster, extract


def main():
    ap = argparse.ArgumentParser(prog="signals")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ingest"); i.add_argument("--batches", type=int, default=96)
    e = sub.add_parser("extract"); e.add_argument("--backend", default="claude-cli")
    a = ap.parse_args()
    conn = connect()

    if a.cmd == "ingest":
        docs = cluster(fetch(n_batches=a.batches))
        new = upsert_documents(conn, docs)
        for d in docs:
            conn.execute("UPDATE documents SET cluster_id=?, novelty=? WHERE doc_id=?",
                         (d["cluster_id"], d["novelty"], d["doc_id"]))
        conn.commit()
        with open("fixtures/documents.jsonl", "w") as f:
            for d in docs:
                f.write(json.dumps(d) + "\n")
        print(json.dumps({"seen": len(docs), "new": new,
                          "clusters": len({d['cluster_id'] for d in docs})}))

    elif a.cmd == "extract":
        docs = [json.loads(l) for l in open("fixtures/documents.jsonl")]
        claims, meter = extract(docs, backend=a.backend)
        insert_claims(conn, claims)
        with open("fixtures/claims.jsonl", "w") as f:
            for c in claims:
                f.write(json.dumps(c) + "\n")
        print(json.dumps({"claims": len(claims), **meter}))


if __name__ == "__main__":
    main()
