"""Export the Day 6 chunks (one strategy) from pgvector into the Day 7 JSON schema.

Output: starter/data/day6/chunks.json (git-ignored: the corpus is CC BY-NC-ND,
so the full-text dump is regenerated rather than committed).

Run from the repo root:  python src/export_day6.py
"""
import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_dotenv(ROOT / ".env")
    url = os.environ["DATABASE_URL"]
    strategy = os.getenv("DAY6_STRATEGY", "C")
    with psycopg.connect(url, connect_timeout=5) as conn:
        rows = conn.execute(
            "SELECT chunk_id, document_id, source, page, section, region, text, metadata, embedding_model "
            "FROM chunks_384d WHERE strategy = %s ORDER BY page, chunk_id", (strategy,)).fetchall()
    if not rows:
        raise SystemExit(f"No chunks for strategy {strategy!r}; is the Day 6 database running and ingested?")
    models = {r[8] for r in rows}
    chunks = []
    for chunk_id, doc_id, source, page, section, region, text, meta, _ in rows:
        meta = dict(meta or {})
        meta.update({"section": section, "region": region, "day6_strategy": strategy})
        chunks.append({"id": chunk_id, "text": text, "source_id": doc_id, "source": source,
                       "page": page, "metadata": meta})
    if len({c["id"] for c in chunks}) != len(chunks):
        raise SystemExit("duplicate chunk ids in export")
    out = ROOT / "starter/data/day6"
    out.mkdir(parents=True, exist_ok=True)
    (out / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Exported {len(chunks)} chunks (strategy {strategy}, embedding model {models}) to {out / 'chunks.json'}")


if __name__ == "__main__":
    main()
