"""Run the DeepSeek agent over all benchmark cases of one split with one retriever config.

Run from the repo root, e.g.:
    python src/run_agent.py --split dev --method dense --top-k 3 --tag dense_k3
Outputs results/agent/<split>_<tag>/{traces.json, summary.json, cases.json}.
traces.json follows the starter agent_metrics.py contract (query_id, status, events, citations).
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent import DeepSeekClient, run_agent  # noqa: E402
from eval_retrieval import build  # noqa: E402
from metrics import context_has_evidence, cost_usd, ranking_labels, ratio  # noqa: E402
from retrievers import load_chunks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--method", default="dense")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--max-searches", type=int, default=4)
    ap.add_argument("--no-filter", action="store_true")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--only", default="", help="comma list of case ids (debug)")
    args = ap.parse_args()

    cases = [c for c in json.loads((ROOT / "benchmark/cases.json").read_text(encoding="utf-8")) if c["split"] == args.split]
    if args.only:
        cases = [c for c in cases if c["id"] in args.only.split(",")]
    gold = {q["id"]: q for q in json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))}
    retriever = build(load_chunks())[args.method]
    client = DeepSeekClient()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    traces = []
    for c in cases:
        filt = None if args.no_filter else c.get("filter")
        try:
            out = run_agent(c["question"], client, retriever, filters=filt, top_k=args.top_k,
                            max_searches=args.max_searches)
        except Exception as exc:  # provider or vector-store failure: record, never fake
            traces.append({"query_id": c["id"], "split": c["split"], "answerable": c["answerable"], "status": "error",
                           "error": repr(exc), "events": [], "citations": []})
            print(f"{c['id']}: ERROR {exc!r}")
            continue
        ctx = out.pop("_context_chunks")
        row = {"query_id": c["id"], "split": c["split"], "answerable": c["answerable"], "question": c["question"],
               "filter": filt, "config": {"method": args.method, "top_k": args.top_k, "max_searches": args.max_searches},
               **out}
        if c["answerable"]:  # evaluation labels computed AFTER the run, from gold
            q = gold[c["id"]]
            first = next((e for e in out["events"] if e["event"] == "search"), None)
            if first:  # first-search ranking, for comparison with retrieval-only metrics
                by_id = {x["id"]: x for x in ctx}
                row["first_search_labels"] = ranking_labels(
                    [by_id[r["id"]] for r in first["results"] if r["rank"] is not None], q)
            row["context_has_evidence"] = context_has_evidence(ctx, q)
            row["cited_has_evidence"] = context_has_evidence([x for x in ctx if x["id"] in out["citations"]], q)
        row["context"] = [{"id": x["id"], "page": x["page"], "text": x["text"]} for x in ctx]
        traces.append(row)
        print(f"{c['id']}: {out['status']:8} searches={out['searches']} ctx_ev={row.get('context_has_evidence')} "
              f"{out['seconds']}s | {out['answer'][:110]!r}")
        time.sleep(0.2)

    ok = [t for t in traces if t["status"] != "error"]
    ans = [t for t in ok if t["answerable"]]
    una = [t for t in ok if not t["answerable"]]
    usage = {k: sum(t["usage"][k] for t in ok) for k in ("prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "calls")}
    summary = {
        "run_started_utc": started, "split": args.split, "config": vars(args),
        "model": sorted({m for t in ok for m in t["model"]}),
        "errors": [t["query_id"] for t in traces if t["status"] == "error"],
        "tool_use": ratio(sum(t["searches"] > 0 for t in ok), len(ok)),
        "searches_distribution": {str(n): sum(t["searches"] == n for t in ok) for n in sorted({t["searches"] for t in ok})},
        "context_evidence_rate": ratio(sum(t["context_has_evidence"] for t in ans), len(ans)),
        "first_search_hit_at_1": ratio(sum(t.get("first_search_labels", {}).get("hit_at_1", False) for t in ans), len(ans)),
        "first_search_hit_at_3": ratio(sum(t.get("first_search_labels", {}).get("hit_at_3", False) for t in ans), len(ans)),
        "answered_with_citation": ratio(sum(t["status"] == "answered" for t in ok), len(ok)),
        "answerable_refused": ratio(sum(t["status"] == "abstain" for t in ans), len(ans)),
        "unanswerable_abstained": ratio(sum(t["status"] == "abstain" for t in una), len(una)),
        "invalid_citation_ids": sum(len(t["invalid_citations"]) for t in ok),
        "usage": usage, "cost_usd_peak_upper_bound": cost_usd(usage),
        "seconds_total": round(sum(t["seconds"] for t in ok), 1),
        "avg_context_chars": round(sum(t["context_chars"] for t in ok) / max(len(ok), 1)),
    }
    out_dir = ROOT / "results/agent" / f"{args.split}_{args.tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "cases.json").write_text(json.dumps([{k: c[k] for k in ("id", "split", "answerable")} for c in cases],
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("tool_use", "searches_distribution", "context_evidence_rate",
                                              "answerable_refused", "unanswerable_abstained", "usage", "seconds_total")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
