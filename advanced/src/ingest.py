"""Advanced challenge, step 1: per-page text extraction + manifest for AR2022EN.pdf.

Outputs (git-ignored, under advanced/work/):
  pages.json      one record per PDF page: normalized text, visual signals
Committed:
  advanced/manifest.json  source, license, page counts, visual-page list, unprocessed pages

Run from the repo root:  python advanced/src/ingest.py
"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "advanced/data/AR2022EN.pdf"
WORK = ROOT / "advanced/work"
SOURCE_ID = "wb-ar-2022"
HEADER_RE = re.compile(r"^\s*(\d{1,3}\s+)?THE WORLD BANK ANNUAL REPORT 2022(\s+\d{1,3})?\s*$", re.M)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\xad\n", "").replace("\xad", "").replace(" ", " ").replace("\t", " ")
    text = HEADER_RE.sub("", text)
    lines = [re.sub(r"[  ]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln and not re.fullmatch(r"\d{1,3}", ln))


def main() -> None:
    doc = pymupdf.open(PDF)
    pages = []
    for i, p in enumerate(doc, 1):
        raw = p.get_text()
        text = normalize(raw)
        area = p.rect.width * p.rect.height
        big_imgs = [b for b in (p.get_image_bbox(x) for x in p.get_images(full=True))
                    if b.is_valid and b.width * b.height / area > 0.08]
        drawings = len(p.get_drawings())
        tags = sorted(set(re.findall(r"\b(TABLE|FIGURE|MAP)\s*(\d+)", raw)))
        visual = bool(tags) or drawings > 60 or p.rect.width > p.rect.height
        pages.append({"page": i, "text": text, "chars": len(text), "width": p.rect.width, "height": p.rect.height,
                      "big_raster_images": len(big_imgs), "vector_drawings": drawings,
                      "tags": [f"{a} {b}" for a, b in tags], "visual_candidate": visual})
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")

    unprocessed = {p["page"]: "blank page (no text, no informative visual)" for p in pages
                   if p["chars"] < 40 and not p["visual_candidate"] and p["big_raster_images"] == 0}
    photo_only = [p["page"] for p in pages if p["big_raster_images"] and p["chars"] < 120 and not p["tags"]]
    manifest = {
        "source_id": SOURCE_ID,
        "title": "World Bank Annual Report 2022: Helping Countries Adapt to a Changing World",
        "publisher": "International Bank for Reconstruction and Development / The World Bank",
        "source_url": "https://openknowledge.worldbank.org (World Bank Annual Report 2022, file AR2022EN.pdf)",
        "local_path": "advanced/data/AR2022EN.pdf (git-ignored; provided by the student)",
        "sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
        "license": "CC BY-NC-ND 3.0 IGO (stated on the copyright page). Used unmodified, non-commercially; "
                   "rendered page images and model descriptions are kept local (advanced/work/, git-ignored).",
        "pdf_pages": len(pages),
        "text_pages": sum(p["chars"] >= 40 for p in pages),
        "visual_candidate_pages": [p["page"] for p in pages if p["visual_candidate"]],
        "photo_divider_pages": photo_only,
        "unprocessed_pages": unprocessed,
        "extraction": f"PyMuPDF {pymupdf.VersionBind}: text per page (soft hyphens joined, running header removed); "
                      "visual pages additionally described by a vision model (see describe_visuals.py).",
    }
    (ROOT / "advanced/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(pages)} pages; text pages {manifest['text_pages']}; visual candidates "
          f"{len(manifest['visual_candidate_pages'])}: {manifest['visual_candidate_pages']}")
    print("photo/divider pages:", photo_only, "| unprocessed:", list(unprocessed))


if __name__ == "__main__":
    main()
