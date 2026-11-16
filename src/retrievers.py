"""Retrieval methods over the Day 6 corpus. All return the same result shape:
{id, text, source_id, source, page, metadata, score, rank, method}.

- DenseRetriever: Day 6 pgvector index (strategy C) + the same MiniLM query embedding.
- BM25Retriever: lexical BM25 (rank-bm25) over the same exported chunks.
- HybridRRF: Reciprocal Rank Fusion of dense and BM25 candidate lists.
Filters are metadata equality filters supplied with the question (never from gold).
"""
import json
import os
import re
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv

from textnorm import canon

ROOT = Path(__file__).resolve().parents[1]
FILTER_KEYS = {"region", "section"}
STOPWORDS = set("""a an and are as at be by did do does for from has have how in is it its of on or
the this that to was were what when which who with world bank group fiscal according""".split())


def _check_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    filters = filters or {}
    bad = set(filters) - FILTER_KEYS
    if bad:
        raise ValueError(f"filter keys not allowed: {bad}")
    return filters


def load_chunks() -> list[dict[str, Any]]:
    path = ROOT / "starter/data/day6/chunks.json"
    if not path.exists():
        raise FileNotFoundError("Run `python src/export_day6.py` first (needs the Day 6 database).")
    return json.loads(path.read_text(encoding="utf-8"))


def _result(chunk: dict[str, Any], score: float, rank: int, method: str) -> dict[str, Any]:
    return {"id": chunk["id"], "text": chunk["text"], "source_id": chunk["source_id"],
            "source": chunk["source"], "page": chunk["page"], "metadata": chunk["metadata"],
            "score": round(float(score), 6), "rank": rank, "method": method}


class DenseRetriever:
    name = "dense"

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        from sentence_transformers import SentenceTransformer

        load_dotenv(ROOT / ".env")
        self.url = os.environ["DATABASE_URL"]
        self.strategy = os.getenv("DAY6_STRATEGY", "C")
        self.model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.model = SentenceTransformer(self.model_name, device="cpu")
        self.by_id = {c["id"]: c for c in chunks}
        with psycopg.connect(self.url, connect_timeout=5) as conn:
            models = {r[0] for r in conn.execute(
                "SELECT DISTINCT embedding_model FROM chunks_384d WHERE strategy = %s", (self.strategy,))}
        if models != {self.model_name}:
            raise RuntimeError(f"index embedded with {models}, query model is {self.model_name}")

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        filters = _check_filters(filters)
        vec = self.model.encode([query], normalize_embeddings=True)[0]
        lit = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
        where, params = ["strategy = %s"], [self.strategy]
        for k, v in filters.items():
            where.append(f"{k} = %s")
            params.append(v)
        sql = (f"SELECT chunk_id, 1 - (embedding <=> %s::vector) FROM chunks_384d WHERE {' AND '.join(where)} "
               f"ORDER BY embedding <=> %s::vector LIMIT %s")
        with psycopg.connect(self.url, connect_timeout=5) as conn:
            rows = conn.execute(sql, [lit, *params, lit, top_k]).fetchall()
        missing = [r[0] for r in rows if r[0] not in self.by_id]
        if missing:
            raise RuntimeError(f"chunks in DB but not in export (re-run export_day6.py): {missing[:3]}")
        return [_result(self.by_id[cid], s, i + 1, self.name) for i, (cid, s) in enumerate(rows)]


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+(?:[.,][0-9]+)*", canon(text))
    return [t for t in toks if t not in STOPWORDS]


class BM25Retriever:
    name = "bm25"

    def __init__(self, chunks: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> None:
        from rank_bm25 import BM25Okapi

        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks], k1=k1, b=b)

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        filters = _check_filters(filters)
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(self.chunks)), key=lambda i: -scores[i])
        out = []
        for i in order:
            c = self.chunks[i]
            if any(c["metadata"].get(k) != v for k, v in filters.items()):
                continue
            if scores[i] <= 0:
                break
            out.append(_result(c, scores[i], len(out) + 1, self.name))
            if len(out) == top_k:
                break
        return out


class NeighborExpansion:
    """Context selection: after the base retriever's top-k, append the chunk right
    before and after each hit on the same page (deduplicated). Ranking metrics use
    only the base top-k (rank 1..k); neighbors carry rank None and `neighbor_of`."""

    def __init__(self, base, chunks: list[dict[str, Any]], window: int = 1) -> None:
        self.base, self.window = base, window
        self.name = f"{base.name}+nbr{window}"
        self.order: dict[str, tuple[str, int, int]] = {}
        self.by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
        for c in chunks:
            idx = int(c["id"].rsplit(":", 1)[1])
            key = (c["source_id"], c["page"], idx)
            self.order[c["id"]] = key
            self.by_key[key] = c

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        hits = self.base.search(query, filters=filters, top_k=top_k)
        seen = {h["id"] for h in hits}
        out = list(hits)
        for h in hits:
            src, page, idx = self.order[h["id"]]
            for d in [i for i in range(-self.window, self.window + 1) if i]:
                c = self.by_key.get((src, page, idx + d))
                if c and c["id"] not in seen:
                    seen.add(c["id"])
                    r = _result(c, 0.0, None, self.name)
                    r["neighbor_of"] = h["id"]
                    out.append(r)
        return out


class HybridRRF:
    """Reciprocal Rank Fusion: score = sum 1/(k + rank) over the two candidate lists.
    Uses ranks only, so dense cosine and BM25 scores need no normalization."""
    name = "hybrid_rrf"

    def __init__(self, dense: DenseRetriever, bm25: BM25Retriever, candidates: int = 20, k: int = 60) -> None:
        self.dense, self.bm25, self.candidates, self.k = dense, bm25, candidates, k

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        lists = [self.dense.search(query, filters=filters, top_k=self.candidates),
                 self.bm25.search(query, filters=filters, top_k=self.candidates)]
        fused: dict[str, float] = {}
        best: dict[str, dict[str, Any]] = {}
        for results in lists:
            for r in results:
                fused[r["id"]] = fused.get(r["id"], 0.0) + 1.0 / (self.k + r["rank"])
                best.setdefault(r["id"], r)
        order = sorted(fused, key=lambda i: -fused[i])[:top_k]
        return [_result(best[i], fused[i], n + 1, self.name) for n, i in enumerate(order)]
