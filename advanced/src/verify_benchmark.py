"""Check the advanced benchmark against the ORIGINAL PDF text layers (PyMuPDF + pdfplumber).

- every evidence quote must occur on its page (canonicalized)
- every evidence value must occur among that page's numbers in the text layers
  (pie-chart label/value pairing and diagram arrows cannot be checked this way: those
   were verified visually on rendered pages and must be re-checked by the reviewer)
- split/group counts meet ADVANCED.md minimums
- no-evidence questions: re-run term searches and print every hit for review
Run:  python advanced/src/verify_benchmark.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pdfplumber
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from textnorm import canon  # noqa: E402

MIN_TEST = {"table": 6, "image_diagram": 5, "chart": 5, "multi_hop": 4, "text": 4}
ABSENCE_TERMS = {"du1": [r"Viet ?Nam"], "du2": [r"FY ?17", r"fiscal 2017"], "du3": [r"Japan"],
                 "tu1": [r"\bGini\b"], "tu2": [r"IFC.{0,40}staff", r"staff.{0,40}IFC"],
                 "tu3": [r"MIGA.{0,80}Ukraine", r"Ukraine.{0,80}MIGA"], "tu4": [r"fiscal 2023", r"FY ?23"],
                 "tu5": [r"fiscal 2021.{0,80}South Asia.{0,80}Health"], "tu6": [r"Nigeria.{0,120}(mortality|under-5)"]}


def norm_num(s: str) -> str:
    return re.sub(r"[()$%,]", "", s).rstrip(".")


def main() -> None:
    pdf = ROOT / "advanced/data/AR2022EN.pdf"
    doc, pl = pymupdf.open(pdf), pdfplumber.open(pdf)
    layers = {i + 1: (doc[i].get_text() + "\n" + (pl.pages[i].extract_text() or "")).replace("\xad\n", "").replace("\xad", "")
              for i in range(doc.page_count)}
    qs = json.loads((ROOT / "advanced/benchmark/questions.json").read_text(encoding="utf-8"))
    errors = []
    for q in qs:
        if not q["answerable"]:
            if not q.get("absence_reason"):
                errors.append(f"{q['id']}: missing absence_reason")
            for term in ABSENCE_TERMS.get(q["id"], []):
                hits = {p: m.group(0) for p, t in layers.items() for m in [re.search(term, " ".join(t.split()), re.I)] if m}
                print(f"{q['id']} absence check /{term}/ -> pages {sorted(hits)}")
            continue
        for e in q["evidence"]:
            t = layers[e["page"]]
            nums = {norm_num(x) for x in re.findall(r"\(?\$?\d[\d,]*\.?\d*%?\)?", t)}
            miss_vals = [v for v in e["values"] if norm_num(v) not in nums]
            quote_ok = canon(e["quote"]) in canon(t) if e.get("quote") else None
            status = "OK" if not miss_vals and quote_ok is not False else "CHECK"
            print(f"{q['id']} p{e['page']:<3} {e['kind']:11} values {e['values']} missing {miss_vals} quote {quote_ok} -> {status}")
            if miss_vals or quote_ok is False:
                errors.append(f"{q['id']}: p{e['page']} missing values {miss_vals} / quote {quote_ok}")
    c = Counter((q["split"], q["group"]) for q in qs)
    test_ans = sum(v for (s, g), v in c.items() if s == "test" and g != "no_evidence")
    dev_ans = sum(v for (s, g), v in c.items() if s == "dev" and g != "no_evidence")
    print(dict(c))
    for g, m in MIN_TEST.items():
        if c[("test", g)] < m:
            errors.append(f"test group {g}: {c[('test', g)]} < {m}")
    if test_ans < 24 or c[("test", "no_evidence")] < 6 or test_ans + c[("test", "no_evidence")] < 30:
        errors.append("test needs >= 30 questions incl. >= 24 answerable and >= 6 no-evidence")
    if dev_ans < 15 or c[("dev", "no_evidence")] < 3:
        errors.append("dev needs >= 15 answerable and >= 3 no-evidence")
    if errors:
        print("FAILED:\n - " + "\n - ".join(errors))
        sys.exit(1)
    print("Advanced benchmark verified against the PDF text layers.")


if __name__ == "__main__":
    main()
