"""Retrieval-only benchmark (no LLM): original question as query, top-3 per method.

Context Evidence Rate here uses a fixed retrieval-only context: the top results
packed into a character budget. The agent's own context rate is measured later.

Run from the repo root:  python src/eval_retrieval.py --split dev
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import context_has_evidence, ranking_labels, ratio  # noqa: E402
from retrievers import BM25Retriever, DenseRetriever, HybridRRF, NeighborExpansion, load_chunks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def pack(results: list[dict], budget: int) -> list[dict]:
    """Keep results in rank order while they fit the character budget (text only)."""
    out, used = [], 0
    for r in results:
        if used + len(r["text"]) > budget:
            continue
        out.append(r)
        used += len(r["text"])
    return out


def build(chunks: list[dict]) -> dict:
    dense = DenseRetriever(chunks)
    bm25 = BM25Retriever(chunks)
    hybrid = HybridRRF(dense, bm25)
    return {"dense": dense, "bm25": bm25, "hybrid_rrf": hybrid,
            "dense+nbr1": NeighborExpansion(dense, chunks), "hybrid_rrf+nbr1": NeighborExpansion(hybrid, chunks)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--methods", default="dense,bm25,hybrid_rrf")
    ap.add_argument("--no-filter", action="store_true", help="ignore question filters (ablation)")
    ap.add_argument("--budget", type=int, default=1500, help="retrieval-only context budget (chars)")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    chunks = load_chunks()
    questions = [q for q in json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))
                 if q["split"] == args.split]
    methods = build(chunks)
    summary, traces = {}, []
    for name in args.methods.split(","):
        r = methods[name]
        rows, t0 = [], time.perf_counter()
        for q in questions:
            filt = None if args.no_filter else q.get("filter")
            res = r.search(q["question"], filters=filt, top_k=3)
            lab = ranking_labels([x for x in res if x["rank"] is not None], q)  # neighbors are not ranked
            ctx = pack(res, args.budget)
            rows.append({"method": name, "id": q["id"], "split": q["split"], "query": q["question"],
                         "filter": filt, **lab, "context_ids": [c["id"] for c in ctx],
                         "context_has_evidence": context_has_evidence(ctx, q),
                         "results": [{k: x[k] for k in ("rank", "id", "page", "score")} | {"region": x["metadata"].get("region")}
                                     for x in res]})
        secs = time.perf_counter() - t0
        n = len(rows)
        summary[name] = {"hit_at_1": ratio(sum(x["hit_at_1"] for x in rows), n),
                         "evidence_hit_at_3": ratio(sum(x["hit_at_3"] for x in rows), n),
                         "context_evidence_rate": ratio(sum(x["context_has_evidence"] for x in rows), n),
                         "missed_at_3": [x["id"] for x in rows if not x["hit_at_3"]],
                         "seconds_total": round(secs, 2), "cost_usd": 0}
        traces.extend(rows)
    tag = args.tag or ("nofilter" if args.no_filter else "filter")
    out = ROOT / "results/retrieval" / f"{args.split}_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'method':12} {'Hit@1':>8} {'Hit@3':>8} {'CtxEv':>8}  missed@3")
    for name, s in summary.items():
        f = lambda m: f"{s[m]['n']}/{s[m]['N']}"
        print(f"{name:12} {f('hit_at_1'):>8} {f('evidence_hit_at_3'):>8} {f('context_evidence_rate'):>8}  {s['missed_at_3']}")


if __name__ == "__main__":
    main()
