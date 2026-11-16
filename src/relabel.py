"""Recompute gold-based labels of saved agent traces against the CURRENT benchmark
(e.g. after adding a valid alternative evidence on dev), without calling the API.

Run:  python src/relabel.py results/agent/dev_dense_k3 [more dirs...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import context_has_evidence, cost_usd, ranking_labels, ratio  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def relabel(run_dir: Path) -> dict:
    gold = {q["id"]: q for q in json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))}
    chunks = {c["id"]: c for c in json.loads((ROOT / "starter/data/day6/chunks.json").read_text(encoding="utf-8"))}
    traces = json.loads((run_dir / "traces.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    for t in traces:
        if t["status"] == "error" or not t["answerable"]:
            continue
        q = gold[t["query_id"]]
        ctx = [chunks[c["id"]] for c in t["context"]]
        first = next((e for e in t["events"] if e["event"] == "search"), None)
        if first:
            t["first_search_labels"] = ranking_labels(
                [chunks[r["id"]] for r in first["results"] if r.get("rank") is not None], q)
        t["context_has_evidence"] = context_has_evidence(ctx, q)
        t["cited_has_evidence"] = context_has_evidence([c for c in ctx if c["id"] in t["citations"]], q)
    ok = [t for t in traces if t["status"] != "error"]
    ans = [t for t in ok if t["answerable"]]
    summary["context_evidence_rate"] = ratio(sum(t["context_has_evidence"] for t in ans), len(ans))
    summary["first_search_hit_at_1"] = ratio(sum(t.get("first_search_labels", {}).get("hit_at_1", False) for t in ans), len(ans))
    summary["first_search_hit_at_3"] = ratio(sum(t.get("first_search_labels", {}).get("hit_at_3", False) for t in ans), len(ans))
    summary["cited_chunk_has_evidence"] = ratio(sum(t["cited_has_evidence"] for t in ans), len(ans))
    summary["cost_usd_peak_upper_bound"] = cost_usd(summary["usage"])
    (run_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=1), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    for d in sys.argv[1:]:
        s = relabel(Path(d))
        f = lambda k: f"{s[k]['n']}/{s[k]['N']}"
        print(f"{Path(d).name:24} firstHit@1 {f('first_search_hit_at_1')}  firstHit@3 {f('first_search_hit_at_3')}  "
              f"CER {f('context_evidence_rate')}  cited-has-evidence {f('cited_chunk_has_evidence')}  "
              f"abstain {f('unanswerable_abstained')}  ${s['cost_usd_peak_upper_bound']}")
