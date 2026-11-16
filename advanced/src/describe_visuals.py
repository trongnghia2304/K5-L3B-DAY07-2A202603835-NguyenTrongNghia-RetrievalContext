"""Advanced challenge, step 2: describe every informative visual on the visual-candidate
pages with deepseek-flash vision, as structured JSON. Resumable (skips pages already done).

Each description is checked against the PDF text layer: numeric tokens in the
description that do not occur on the page text are counted ("numbers not in text
layer"), so model-made values on vector pages can be spotted and reviewed. Raster
visuals have no text layer; those need manual spot checks.

Run from the repo root:  python advanced/src/describe_visuals.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vision import VisionClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "advanced/work"
OUT = WORK / "visuals"

PROMPT = """You are indexing one page of the World Bank Annual Report 2022 for a search system.
Extract EVERY informative visual element on this page: tables, charts (pie/bar/line), maps,
diagrams, infographics with figures. SKIP decorative photos and pure page decorations.
Return JSON: {"visuals": [ {
  "kind": "table|chart|map|diagram|infographic",
  "label": "e.g. TABLE 23 or FIGURE 1 (as printed; empty if none)",
  "title": "full printed title incl. units/fiscal year",
  "content": "complete faithful transcription: for tables every row with all column values and units;
              for charts every category with its value and the total/unit; for maps the legend and every
              numbered callout or labelled value; for diagrams every box and how boxes connect;
              for infographics every figure with its label",
  "notes": "footnotes or anything illegible"} ]}
Copy numbers exactly as printed (keep parentheses for negatives). Do not compute or infer values.
If the page has no informative visual, return {"visuals": []}."""

NUM_RE = re.compile(r"\(?\$?\d[\d,]*\.?\d*%?\)?")


def numbers(text: str) -> set[str]:
    return {re.sub(r"[()$%,]", "", n).rstrip(".") for n in NUM_RE.findall(text)} - {""}


_plumber = None


def text_layer_numbers(page: int, pymupdf_text: str) -> set[str]:
    """Numbers from the union of two independent text extractors (PyMuPDF misses some table cells)."""
    global _plumber
    import pdfplumber
    if _plumber is None:
        _plumber = pdfplumber.open(ROOT / "advanced/data/AR2022EN.pdf")
    return numbers(pymupdf_text) | numbers(_plumber.pages[page - 1].extract_text() or "")


def recheck() -> None:
    """Recompute the numbers-not-in-text-layer check for all saved descriptions."""
    pages = {p["page"]: p for p in json.loads((WORK / "pages.json").read_text(encoding="utf-8"))}
    total = flagged = 0
    for f in sorted(OUT.glob("p*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        layer = text_layer_numbers(rec["page"], pages[rec["page"]]["text"])
        for v in rec["visuals"]:
            nums = numbers(v.get("content", "") + " " + v.get("title", ""))
            v["numbers_total"] = len(nums)
            v["numbers_not_in_text_layer"] = sorted(x for x in nums if x not in layer)
            total += len(nums)
            flagged += len(v["numbers_not_in_text_layer"])
            if v["numbers_not_in_text_layer"]:
                print(f"p{rec['page']:03d} {v.get('label')}: {len(v['numbers_not_in_text_layer'])}/{len(nums)} "
                      f"not in text layers: {v['numbers_not_in_text_layer'][:12]}")
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"numbers in descriptions: {total}; not found in either text layer: {flagged}")


def main() -> None:
    if "--recheck" in sys.argv:
        recheck()
        return
    pages = {p["page"]: p for p in json.loads((WORK / "pages.json").read_text(encoding="utf-8"))}
    manifest = json.loads((ROOT / "advanced/manifest.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    client = VisionClient()
    for n in manifest["visual_candidate_pages"]:
        path = OUT / f"p{n:03d}.json"
        if path.exists():
            continue
        try:
            res = client.ask(n, PROMPT, json_mode=True)
            visuals = json.loads(res["content"]).get("visuals", [])
            err = None
        except Exception as exc:  # record, do not fake
            res, visuals, err = {"usage": {}, "model": None, "seconds": None}, [], repr(exc)
        layer = numbers(pages[n]["text"])
        for v in visuals:
            nums = numbers(v.get("content", "") + " " + v.get("title", ""))
            missing = sorted(x for x in nums if x not in layer)
            v["numbers_total"] = len(nums)
            v["numbers_not_in_text_layer"] = missing
        rec = {"page": n, "model": res.get("model"), "usage": res.get("usage"), "seconds": res.get("seconds"),
               "error": err, "visuals": visuals}
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        flag = sum(len(v["numbers_not_in_text_layer"]) for v in visuals)
        print(f"p{n:03d}: {len(visuals)} visuals, {res.get('seconds')}s, "
              f"{(res.get('usage') or {}).get('completion_tokens')} out tok, numbers not in text layer: {flag}"
              + (f" ERROR {err}" if err else ""))


if __name__ == "__main__":
    main()
