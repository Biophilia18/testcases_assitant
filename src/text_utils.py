from __future__ import annotations

import re


def normalize_steps(steps: str) -> str:
    text = str(steps or "").strip()
    if not text:
        return ""

    normalized = re.sub(r"\s+", " ", text)
    normalized = re.sub(r"\s*(?=(?:\d+[.)、]|[一二三四五六七八九十]+[、.])\s*)", "\n", normalized)
    normalized = re.sub(r"\n+", "\n", normalized).strip()

    return normalized

