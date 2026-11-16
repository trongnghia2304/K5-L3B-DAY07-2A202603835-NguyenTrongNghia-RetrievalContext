"""Check the Day 7 benchmark against the exported Day 6 chunks before any run.

- split sizes: dev >= 15 answerable + 2 no-evidence; test >= 5 + 2
- every gold evidence sits wholly inside ONE chunk on its gold source/page
  (at least one alternative per question must satisfy this)
- filter values exist in chunk metadata and include the gold page
- no-evidence cases carry an absence_reason

Run from the repo root:  python src/verify_benchmark.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from textnorm import canon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    chunks = json.loads((ROOT / "starter/data/day6/chunks.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "benchmark/cases.json").read_text(encoding="utf-8"))
    by_page: dict[tuple[str, int], list[dict]] = {}
    for c in chunks:
        by_page.setdefault((c["source_id"], c["page"]), []).append(c)

    errors: list[str] = []
    for q in questions:
        ok_alts = []
        for g in q["gold"]:
            cands = by_page.get((g["source_id"], g["page"]), [])
            holders = [c["id"] for c in cands if canon(g["evidence"]) in canon(c["text"])]
            page_text = canon(" ".join(c["text"] for c in cands))
            status = "single-chunk" if holders else ("split-across-chunks" if canon(g["evidence"]) in page_text else "NOT FOUND")
            print(f"{q['id']:4} p{g['page']:<3} {status:20} {holders[:1]}")
            if holders:
                ok_alts.append(g)
            elif status == "NOT FOUND":
                errors.append(f"{q['id']}: evidence not found on page {g['page']}")
        if not ok_alts:
            errors.append(f"{q['id']}: no gold alternative fits inside a single chunk")
        for key, value in (q.get("filter") or {}).items():
            pages = {c["page"] for c in chunks if c["metadata"].get(key) == value}
            if not pages:
                errors.append(f"{q['id']}: filter {key}={value} matches no chunk")
            elif not {g["page"] for g in q["gold"]} & pages:
                errors.append(f"{q['id']}: gold page outside filter {key}={value}")

    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate case ids")
    qids = {q["id"] for q in questions}
    for c in cases:
        if c["answerable"] and c["id"] not in qids:
            errors.append(f"{c['id']}: answerable case missing from questions.json")
        if not c["answerable"] and not c.get("absence_reason"):
            errors.append(f"{c['id']}: no-evidence case needs absence_reason")
    n = Counter((c["split"], c["answerable"]) for c in cases)
    print(dict(n))
    if n[("dev", True)] < 15 or n[("dev", False)] < 2 or n[("test", True)] < 5 or n[("test", False)] < 2:
        errors.append("split sizes below the Day 7 minimum")

    if errors:
        print("FAILED:\n - " + "\n - ".join(errors))
        sys.exit(1)
    print("Benchmark verified.")


if __name__ == "__main__":
    main()
