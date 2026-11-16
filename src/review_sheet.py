"""Manual grading for agent runs.

  make:      python src/review_sheet.py make results/agent/test_dense_k3 results/agent/test_hybrid_rrf_k3
             -> results/manual/test_agent_labels.csv (blank label columns; never overwrites)
  summarize: python src/review_sheet.py summarize
             -> per-run reviews.json (starter agent_metrics.py contract) + agent_metrics summary
                + context grade 0/1/2 counts -> results/manual/test_summary.md

Label columns to fill per row:
  context_grade_0_1_2  (answerable only) 0 no evidence, 1 evidence but missing condition/source, 2 enough + source
  answer_grade_0_1_2   (answerable only) 0 wrong/missing evidence (refusal = 0), 1 partly right, 2 right and complete
  citation_support     one y/n per citation, ';'-separated, same order as `citations`
  abstention_correct_y_n (no-evidence only) y if it truly refused without unsupported claims
  reason               why
"""
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "results/manual/test_agent_labels.csv"
LABELS = ["context_grade_0_1_2", "answer_grade_0_1_2", "citation_support", "abstention_correct_y_n", "reason"]


def make(run_dirs: list[str]) -> None:
    if SHEET.exists():
        raise SystemExit(f"{SHEET} exists; refusing to overwrite human labels")
    gold = {q["id"]: q for q in json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))}
    rows = []
    for d in run_dirs:
        for t in json.loads((Path(d) / "traces.json").read_text(encoding="utf-8")):
            ctx = {c["id"]: c for c in t.get("context", [])}
            q = gold.get(t["query_id"], {})
            rows.append({
                "run": Path(d).name, "query_id": t["query_id"], "answerable": t["answerable"],
                "question": t.get("question", ""), "expected_answer": q.get("expected_answer", "(abstain)"),
                "gold_pages": ",".join(str(g["page"]) for g in q.get("gold", [])),
                "status": t["status"], "answer": t.get("answer", t.get("error", "")),
                "citations": ";".join(t.get("citations", [])),
                "cited_text": "\n---\n".join(f"[{c}] " + " ".join(ctx[c]["text"].split()) for c in t.get("citations", []) if c in ctx),
                "searches": " | ".join(e["query"] for e in t.get("events", []) if e["event"] == "search"),
                "context_pages": ",".join(str(c["page"]) for c in t.get("context", [])),
                "auto_context_has_evidence": t.get("context_has_evidence", ""),
                **{k: "" for k in LABELS}})
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    with SHEET.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {SHEET}")


def summarize() -> None:
    with SHEET.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = ["# Test: manual agent labels", "", "Người chấm: tác giả (xem mục phương pháp trong báo cáo).", ""]
    for run in sorted({r["run"] for r in rows}):
        rs = [r for r in rows if r["run"] == run]
        reviews, missing = [], []
        for r in rs:
            if r["status"] == "error":
                continue
            rev = {"query_id": r["query_id"]}
            cits = [c for c in r["citations"].split(";") if c]
            sup = [s.strip().lower() for s in r["citation_support"].split(";") if s.strip()]
            if len(sup) != len(cits):
                missing.append(f"{r['query_id']}: citation_support needs {len(cits)} y/n")
            rev["citation_support"] = [s == "y" for s in sup]
            if r["answerable"] == "True":
                if r["answer_grade_0_1_2"] not in {"0", "1", "2"} or r["context_grade_0_1_2"] not in {"0", "1", "2"}:
                    missing.append(f"{r['query_id']}: answer/context grade")
                    continue
                rev["answer_grade"] = int(r["answer_grade_0_1_2"])
            else:
                if r["abstention_correct_y_n"].lower() not in {"y", "n"}:
                    missing.append(f"{r['query_id']}: abstention_correct")
                    continue
                rev["abstention_correct"] = r["abstention_correct_y_n"].lower() == "y"
            reviews.append(rev)
        if missing:
            raise SystemExit(f"{run}: unlabeled -> {missing}")
        run_dir = ROOT / "results/agent" / run
        (run_dir / "reviews.json").write_text(json.dumps(reviews, ensure_ascii=False, indent=1), encoding="utf-8")
        res = subprocess.run([sys.executable, str(ROOT / "starter/agent_metrics.py"), "--cases", str(run_dir / "cases.json"),
                              "--traces", str(run_dir / "traces.json"), "--reviews", str(run_dir / "reviews.json"),
                              "--split", "test", "--output", str(run_dir / "agent_metrics.json")],
                             capture_output=True, text=True, encoding="utf-8")
        if res.returncode:
            raise SystemExit(res.stderr)
        metrics = json.loads((run_dir / "agent_metrics.json").read_text(encoding="utf-8"))
        ans = [r for r in rs if r["answerable"] == "True"]
        cg = Counter(int(r["context_grade_0_1_2"]) for r in ans)
        ag = Counter(int(r["answer_grade_0_1_2"]) for r in ans)
        out += [f"## {run}", "",
                f"- Context 0/1/2: {cg[0]}/{cg[1]}/{cg[2]} (trung bình {sum(k*v for k, v in cg.items())/len(ans):.2f}/2, n={len(ans)})",
                f"- Grounded answer 0/1/2: {ag[0]}/{ag[1]}/{ag[2]} (trung bình {sum(k*v for k, v in ag.items())/len(ans):.2f}/2)",
                "- agent_metrics.py:", "", "```json", json.dumps(metrics, ensure_ascii=False, indent=2), "```", ""]
    (ROOT / "results/manual/test_summary.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    if sys.argv[1] == "make":
        make(sys.argv[2:])
    else:
        summarize()
