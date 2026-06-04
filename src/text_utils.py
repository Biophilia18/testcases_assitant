from __future__ import annotations

import ast
import re
from typing import Any


def normalize_steps(steps: Any) -> str:
    if isinstance(steps, list):
        return _normalize_step_list(steps)

    text = str(steps or "").strip()
    if not text:
        return ""

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return _normalize_step_list(parsed)
        except (SyntaxError, ValueError):
            pass

    normalized = re.sub(r"\s+", " ", text)
    normalized = re.sub(r"\s*(?=(?:\d+[.)、]|[一二三四五六七八九十]+[、.])\s*)", "\n", normalized)
    normalized = re.sub(r"\n+", "\n", normalized).strip()

    return normalized


def _normalize_step_list(steps: list[Any]) -> str:
    lines: list[str] = []
    for index, step in enumerate(steps, start=1):
        text = str(step or "").strip().strip("'\"")
        if not text:
            continue
        if re.match(r"^(?:\d+[.)、]|[一二三四五六七八九十]+[、.])\s*", text):
            lines.append(text)
        else:
            lines.append(f"{index}. {text}")

    return "\n".join(lines)
