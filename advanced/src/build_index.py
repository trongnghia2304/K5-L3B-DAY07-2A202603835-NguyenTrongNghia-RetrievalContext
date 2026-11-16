"""Advanced challenge, step 3: build text + visual chunks and index them.

- Text chunks: paragraphs grouped up to 500 chars per page (same idea as Day 6 strategy C).
- Visual chunks: one per described visual (table/chart/map/diagram/infographic); long
  transcriptions are split into parts, each prefixed with the visual's label + title.
- Index: BM25 in memory (at query time) and dense MiniLM vectors in pgvector table
  adv_chunks_384d (same embedding model and DB as Day 6/Day 7).

Outputs advanced/work/chunks.json (git-ignored).  Run:  python advanced/src/build_index.py
"""
import json
import os
import re
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "advanced/work"
SOURCE_ID = "wb-ar-2022"
SENT_END = re.compile(r"[.!?:;][\"'’”)]*$")


def text_chunks(page: dict, max_size: int = 500) -> list[dict]:
    paras, cur = [], []
    for line in page["text"].split("\n"):
        cur.append(line)
        if SENT_END.search(line):
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    pieces = []
    for p in paras:  # split very long paragraphs at sentence boundaries
        while len(p) > max_size:
            cut = max(p.rfind(". ", 0, max_size), p.rfind(" ", 0, max_size))
            cut = cut + 1 if cut > 0 else max_size
            pieces.append(p[:cut].strip()); p = p[cut:].strip()
        if p:
            pieces.append(p)
    out, buf = [], ""
    for p in pieces:
        if buf and len(buf) + 1 + len(p) > max_size:
            out.append(buf); buf = p
        else:
            buf = f"{buf} {p}".strip()
    if buf:
        out.append(buf)
    return [{"id": f"{SOURCE_ID}:p{page['page']:03d}:t{i:02d}", "kind": "text", "text": t, "source_id": SOURCE_ID,
             "source": "advanced/data/AR2022EN.pdf", "page": page["page"], "metadata": {"modality": "text"}}
            for i, t in enumerate(out)]


def visual_chunks(rec: dict, max_size: int = 1400) -> list[dict]:
    out = []
    for vi, v in enumerate(rec["visuals"]):
        head = f"[{v.get('kind', 'visual').upper()} on page {rec['page']}] {v.get('label', '')} {v.get('title', '')}".strip()
        body = v.get("content", "") + (f" Notes: {v['notes']}" if v.get("notes") else "")
        parts, rest = [], body
        while len(rest) > max_size:
            cut = max(rest.rfind("; ", 0, max_size), rest.rfind(". ", 0, max_size), rest.rfind("\n", 0, max_size))
            cut = cut + 1 if cut > 0 else max_size
            parts.append(rest[:cut].strip()); rest = rest[cut:].strip()
        parts.append(rest)
        for pi, part in enumerate(parts):
            out.append({"id": f"{SOURCE_ID}:p{rec['page']:03d}:v{vi}{'' if len(parts) == 1 else f'.{pi}'}",
                        "kind": "visual", "text": f"{head}\n{part}", "source_id": SOURCE_ID,
                        "source": "advanced/data/AR2022EN.pdf", "page": rec["page"],
                        "metadata": {"modality": v.get("kind"), "label": v.get("label"), "title": v.get("title"),
                                     "described_by": rec.get("model"),
                                     "numbers_not_in_text_layer": v.get("numbers_not_in_text_layer", [])}})
    return out


def main() -> None:
    pages = json.loads((WORK / "pages.json").read_text(encoding="utf-8"))
    chunks = [c for p in pages if p["chars"] >= 40 for c in text_chunks(p)]
    vis_files = sorted((WORK / "visuals").glob("p*.json"))
    failed = []
    for f in vis_files:
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("error"):
            failed.append(rec["page"])
        chunks += visual_chunks(rec)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "duplicate chunk ids"
    (WORK / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")

    from sentence_transformers import SentenceTransformer
    load_dotenv(ROOT / ".env")
    model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    vecs = SentenceTransformer(model_name, device="cpu").encode([c["text"] for c in chunks], batch_size=32,
                                                               normalize_embeddings=True, show_progress_bar=False)
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS adv_chunks_384d (
            chunk_id text PRIMARY KEY, page int NOT NULL, kind text NOT NULL, text text NOT NULL,
            embedding_model text NOT NULL, embedding vector(384) NOT NULL)""")
        conn.execute("DELETE FROM adv_chunks_384d")  # full rebuild: index always matches chunks.json
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO adv_chunks_384d VALUES (%s,%s,%s,%s,%s,%s::vector)",
                            [(c["id"], c["page"], c["kind"], c["text"], model_name,
                              "[" + ",".join(f"{x:.8f}" for x in v) + "]") for c, v in zip(chunks, vecs)])
    kinds = {}
    for c in chunks:
        kinds[c["metadata"]["modality"]] = kinds.get(c["metadata"]["modality"], 0) + 1
    print(f"{len(chunks)} chunks indexed ({kinds}); visual pages described: {len(vis_files)}; failed: {failed}")


if __name__ == "__main__":
    main()
