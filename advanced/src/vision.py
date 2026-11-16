"""DeepSeek vision helper: render a PDF page and ask deepseek-flash about it."""
import base64
import os
import time
from pathlib import Path

import pymupdf
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "advanced/data/AR2022EN.pdf"
_doc = None


def page_png(page: int, dpi: int | None = None) -> bytes:
    global _doc
    if _doc is None:
        _doc = pymupdf.open(PDF)
    p = _doc[page - 1]
    if dpi is None:
        dpi = 120 if p.rect.width > p.rect.height else 150  # wide spreads: keep image size moderate
    return p.get_pixmap(dpi=dpi).tobytes("png")


class VisionClient:
    def __init__(self) -> None:
        load_dotenv(ROOT / ".env")
        self.url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/") + "/chat/completions"
        self.model = os.getenv("VISION_MODEL", "deepseek-flash")
        self.s = requests.Session()
        self.s.headers["Authorization"] = "Bearer " + os.environ["DEEPSEEK_API_KEY"]

    def ask(self, page: int, prompt: str, *, json_mode: bool = False, attempts: int = 5) -> dict:
        b64 = base64.b64encode(page_png(page)).decode()
        body = {"model": self.model, "temperature": 0, "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        for a in range(attempts):
            try:
                t = time.perf_counter()
                r = self.s.post(self.url, json=body, timeout=(30, 240))
                if r.status_code == 200:
                    d = r.json()
                    return {"content": d["choices"][0]["message"]["content"], "usage": d.get("usage", {}),
                            "model": d.get("model"), "seconds": round(time.perf_counter() - t, 2)}
                if r.status_code not in (429, 500, 502, 503, 504) or a == attempts - 1:
                    raise RuntimeError(f"vision HTTP {r.status_code}: {r.text[:300]}")
            except requests.RequestException as exc:
                if a == attempts - 1:
                    raise RuntimeError(f"vision request failed: {exc!r}") from exc
            time.sleep(min(2 ** a, 20))
        raise RuntimeError("unreachable")
