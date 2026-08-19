"""SQLite store. Bitemporal by construction: every row records both when the
world changed (event_time) and when we learned about it (ingest_time).

The second clock is the whole point. You can always recompute what happened;
you can never recover *when you knew it* after the fact. Every read path that
claims to be point-in-time filters on ingest_time, never on event_time.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "signals.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id         TEXT PRIMARY KEY,
    url            TEXT NOT NULL,
    title          TEXT,
    domain         TEXT,
    language       TEXT,
    source_country TEXT,
    snippet        TEXT,
    event_time     TEXT NOT NULL,
    ingest_time    TEXT NOT NULL,
    raw            TEXT NOT NULL,
    cluster_id     TEXT,
    novelty        REAL
);
CREATE INDEX IF NOT EXISTS ix_doc_ingest  ON documents(ingest_time);
CREATE INDEX IF NOT EXISTS ix_doc_cluster ON documents(cluster_id);

CREATE TABLE IF NOT EXISTS claims (
    claim_id        TEXT PRIMARY KEY,
    doc_id          TEXT NOT NULL REFERENCES documents(doc_id),
    signal          TEXT NOT NULL,
    direction       INTEGER,
    magnitude       REAL,
    confidence      REAL,
    horizon_days    INTEGER,
    driver          TEXT,
    region          TEXT,
    contract        TEXT,
    evidence_quote  TEXT NOT NULL,
    injection_flag  INTEGER NOT NULL DEFAULT 0,
    verified_number INTEGER NOT NULL DEFAULT 1,
    event_time      TEXT NOT NULL,
    ingest_time     TEXT NOT NULL,
    extractor       TEXT NOT NULL,
    payload         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_claim_ingest ON claims(ingest_time);
CREATE INDEX IF NOT EXISTS ix_claim_signal ON claims(signal);

CREATE TABLE IF NOT EXISTS jobs (
    job_id      TEXT PRIMARY KEY,
    status      TEXT NOT NULL,
    created     TEXT NOT NULL,
    finished    TEXT,
    detail      TEXT
);

"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def doc_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = Path(path) if path else DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_documents(conn, docs: list[dict]) -> int:
    """Insert only. A document already seen keeps its original ingest_time --
    re-ingesting must never move a row forward in the second clock, or every
    point-in-time query silently becomes a lookahead."""
    new = 0
    for d in docs:
        cur = conn.execute(
            """INSERT OR IGNORE INTO documents
               (doc_id,url,title,domain,language,source_country,snippet,
                event_time,ingest_time,raw)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (d["doc_id"], d["url"], d.get("title"), d.get("domain"),
             d.get("language"), d.get("source_country"), d.get("snippet"),
             d["event_time"], d.get("ingest_time") or now(),
             json.dumps(d.get("raw", {}), separators=(",", ":"))),
        )
        new += cur.rowcount
    conn.commit()
    return new


def insert_claims(conn, claims: list[dict]) -> int:
    """Append only. INSERT OR REPLACE was used here and it silently defeated the
    entire bitemporal design: re-running extraction after a prompt change
    overwrote the existing row AND its ingest_time, destroying the record of what
    was known when. Claim ids carry the extractor version, so a re-extraction now
    lands as a NEW row alongside the old one, which is what a correction is."""
    landed = 0
    for c in claims:
        cur = conn.execute(
            """INSERT OR IGNORE INTO claims
               (claim_id,doc_id,signal,direction,magnitude,confidence,horizon_days,
                driver,region,contract,evidence_quote,injection_flag,verified_number,
                event_time,ingest_time,extractor,payload)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (c["claim_id"], c["doc_id"], c["signal"], c.get("direction"),
             c.get("magnitude"), c.get("confidence"), c.get("horizon_days"),
             c.get("driver"), c.get("region"), c.get("contract"),
             c["evidence_quote"], int(c.get("injection_flag", 0)),
             int(c.get("verified_number", 1)), c["event_time"],
             c.get("ingest_time") or now(), c["extractor"],
             json.dumps(c.get("payload", {}), separators=(",", ":"))),
        )
        landed += cur.rowcount
    conn.commit()
    # Return what LANDED, not what was offered. Returning len(claims) reported 13
    # while 12 rows existed, and every downstream count inherited the lie.
    return landed


def claims_as_of(conn, as_of: str | None = None, signal: str | None = None) -> list[sqlite3.Row]:
    """The point-in-time read. Filtering on ingest_time -- not event_time -- is
    what makes a replay honest: it returns exactly what was knowable then."""
    sql = "SELECT * FROM claims WHERE 1=1"
    args: list = []
    if as_of:
        sql += " AND ingest_time <= ?"
        args.append(as_of)
    if signal:
        sql += " AND signal = ?"
        args.append(signal)
    sql += " ORDER BY event_time DESC"
    return conn.execute(sql, args).fetchall()


def docs_as_of(conn, as_of: str | None = None) -> list[sqlite3.Row]:
    if as_of:
        return conn.execute(
            "SELECT * FROM documents WHERE ingest_time <= ? ORDER BY event_time DESC",
            (as_of,)).fetchall()
    return conn.execute("SELECT * FROM documents ORDER BY event_time DESC").fetchall()
