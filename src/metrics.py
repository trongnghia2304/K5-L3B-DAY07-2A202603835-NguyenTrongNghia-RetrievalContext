"""Shared hit definition for retrieval and context metrics (same as Day 6).

A chunk is a hit when it is on a gold source/page AND contains the whole evidence
of that gold alternative (canonicalized). Any listed alternative counts.
"""
from typing import Any

from textnorm import canon


def is_hit(chunk: dict[str, Any], question: dict[str, Any]) -> bool:
    body = canon(chunk["text"])
    return any(chunk["source_id"] == g["source_id"] and chunk["page"] == g["page"]
               and canon(g["evidence"]) in body for g in question["gold"])


def ranking_labels(results: list[dict[str, Any]], question: dict[str, Any]) -> dict[str, Any]:
    hits = [is_hit(r, question) for r in results]
    return {"hit_at_1": bool(hits[:1] and hits[0]), "hit_at_3": any(hits[:3]),
            "first_hit_rank": next((i + 1 for i, h in enumerate(hits) if h), None), "hits": hits}


def _adjacent_runs(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Join context chunks that are consecutive on the same page (chunk index i, i+1, ...)."""
    keyed = sorted(((c["source_id"], c["page"], int(c["id"].rsplit(":", 1)[1])), c) for c in chunks)
    runs: list[dict[str, Any]] = []
    prev = None
    for key, c in keyed:
        if prev and key[:2] == prev[:2] and key[2] == prev[2] + 1:
            runs[-1]["text"] += " " + c["text"]
        else:
            runs.append({"source_id": c["source_id"], "page": c["page"], "text": c["text"]})
        prev = key
    return runs


def context_has_evidence(context_chunks: list[dict[str, Any]], question: dict[str, Any]) -> bool:
    """Context-level: the evidence may span adjacent chunks that are both in the context."""
    return any(is_hit(r, question) for r in _adjacent_runs(context_chunks))


# deepseek-flash (DeepSeek-V4.1-Flash-1017) PEAK prices, USD per 1M tokens, read from
# https://api-docs.deepseek.com/quick_start/pricing on 2026-11-16. Off-peak is half, so
# costs computed here are an upper bound.
PRICE_PER_M = {"cache_hit": 0.006, "cache_miss": 0.30, "output": 1.20}


def cost_usd(usage: dict[str, int]) -> float:
    hit = usage.get("prompt_cache_hit_tokens", 0)
    miss = usage.get("prompt_tokens", 0) - hit
    return round((hit * PRICE_PER_M["cache_hit"] + miss * PRICE_PER_M["cache_miss"]
                  + usage.get("completion_tokens", 0) * PRICE_PER_M["output"]) / 1e6, 6)


def ratio(n: int, d: int) -> dict[str, Any]:
    return {"n": n, "N": d, "rate": round(n / d, 3) if d else None}
