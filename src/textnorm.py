"""Canonical text form shared by evidence matching (same rules as Day 6 evaluation)."""
import re
import unicodedata


def canon(text: str) -> str:
    """Case-folded, whitespace-collapsed, tolerant of PDF kerning/line-wrap artifacts."""
    text = unicodedata.normalize("NFC", text).replace(" ", " ")
    text = re.sub(r"\bT (?=[a-z])", "T", text)
    text = re.sub(r"-\s+", "-", text)
    return re.sub(r"\s+", " ", text).strip().casefold()
