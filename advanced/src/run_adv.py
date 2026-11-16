"""Run the multimodal agent over one split of the advanced benchmark.

    python advanced/src/run_adv.py --split dev --tag base
Outputs advanced/results/<split>_<tag>/{traces.json, summary.json}.

Auto checks (a PROXY only; the official pass/fail is the manual label):
  answerable: every expected value appears in the answer AND every evidence page is cited
              (for a 'text' question with alternative evidence, any one evidence page suffices)
  no-evidence: status == abstain
"""
import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
from agent import DeepSeekClient  # noqa: E402
from agent_mm import build_retriever, load_chunks, run, visual_catalog  # noqa: E402
from metrics import cost_usd  # noqa: E402
from vision import VisionClient  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"[,$\s]", "", s.lower())


def auto_check(q: dict, out: dict) -> dict:
    if not q["answerable"]:
        return {"auto_pass": out["status"] == "abstain"}
    ans = norm(out.get("answer", ""))
    cited_pages = {int(m) for c in out.get("citations", []) for m in re.findall(r":p(\d{3})", c)}
    ev_pages = [e["page"] for e in q["evidence"]]
    any_mode = q.get("evidence_mode") == "any" or q["group"] == "text"
    if any_mode:  # alternatives: one evidence item (its values + page) is enough
        cands = [e for e in q["evidence"] if e["page"] in cited_pages] or q["evidence"][:1]
        missing = [v for v in cands[0]["values"] if norm(v).rstrip("%") not in ans]
        pages_ok = any(p in cited_pages for p in ev_pages)
    else:
        missing = [v for e in q["evidence"] for v in e["values"] if norm(v).rstrip("%") not in ans]
        pages_ok = all(p in cited_pages for p in ev_pages)
    return {"auto_pass": out["status"] == "answered" and not missing and pages_ok,
            "missing_values": missing, "cited_pages": sorted(cited_pages), "evidence_pages": ev_pages}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--method", default="hybrid_rrf")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--max-views", type=int, default=4)
    ap.add_argument("--only", default="")
    ap.add_argument("--catalog", action="store_true", help="put the table/figure catalog in the system prompt")
    ap.add_argument("--loop-fix", action="store_true", help="drop exhausted tools; reserve last turn for an answer")
    args = ap.parse_args()
    qs = [q for q in json.loads((ROOT / "advanced/benchmark/questions.json").read_text(encoding="utf-8")) if q["split"] == args.split]
    if args.only:
        qs = [q for q in qs if q["id"] in args.only.split(",")]
    chunks = load_chunks()
    retriever = build_retriever(chunks, args.method)
    catalog = visual_catalog(chunks) if args.catalog else None
    client, vision = DeepSeekClient(), VisionClient()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    traces = []
    for q in qs:  # gold fields (expected_answer/evidence) are never passed to run()
        try:
            out = run(q["question"], client, vision, retriever, top_k=args.top_k, max_views=args.max_views,
                      catalog=catalog, loop_fix=args.loop_fix)
        except Exception as exc:
            out = {"status": "error", "error": repr(exc), "answer": "", "citations": [], "events": [],
                   "usage": {}, "vision_usage": {}, "seconds": None, "searches": 0, "views": 0, "context": []}
        chk = auto_check(q, out) if out["status"] != "error" else {"auto_pass": False}
        traces.append({"query_id": q["id"], "split": q["split"], "group": q["group"], "answerable": q["answerable"],
                       "question": q["question"], "config": vars(args), **out, **chk})
        print(f"{q['id']:4} {q['group']:13} {out['status']:8} s={out['searches']} v={out['views']} "
              f"auto={'PASS' if chk['auto_pass'] else 'fail'} {out.get('seconds')}s | {out['answer'][:120]!r}"
              + (f" | missing {chk.get('missing_values')} pages {chk.get('cited_pages')} vs {chk.get('evidence_pages')}"
                 if q["answerable"] and not chk["auto_pass"] else ""))
        time.sleep(0.2)
    ok = [t for t in traces if t["status"] != "error"]
    by_group = defaultdict(lambda: [0, 0])
    for t in traces:
        by_group[t["group"]][0] += t["auto_pass"]
        by_group[t["group"]][1] += 1
    usage = Counter(); vusage = Counter()
    for t in ok:
        usage.update(t["usage"]); vusage.update(t["vision_usage"])
    summary = {"run_started_utc": started, "config": vars(args), "model": sorted({m for t in ok for m in t.get("model", [])}),
               "auto_pass": f"{sum(t['auto_pass'] for t in traces)}/{len(traces)}",
               "auto_pass_by_group": {g: f"{a}/{b}" for g, (a, b) in by_group.items()},
               "errors": [t["query_id"] for t in traces if t["status"] == "error"],
               "agent_usage": dict(usage), "vision_usage": dict(vusage),
               "cost_usd_peak_upper_bound": round(cost_usd(usage) + cost_usd(vusage), 5),
               "seconds_total": round(sum(t["seconds"] or 0 for t in ok), 1),
               "views_distribution": dict(Counter(t["views"] for t in ok)),
               "searches_distribution": dict(Counter(t["searches"] for t in ok))}
    out_dir = ROOT / "advanced/results" / f"{args.split}_{args.tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("auto_pass", "auto_pass_by_group", "errors", "cost_usd_peak_upper_bound", "seconds_total")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
