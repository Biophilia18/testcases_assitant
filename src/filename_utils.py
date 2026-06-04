from __future__ import annotations

import re
from datetime import date


def build_export_filename(project_name: str, business_module: str, generation_type: str) -> str:
    parts = [
        _safe_part(project_name) or "测试项目",
        _safe_part(business_module) or "通用模块",
        _safe_part(generation_type) or "测试用例",
        "测试用例",
        date.today().strftime("%Y%m%d"),
    ]
    return "_".join(parts) + ".xlsx"


def _safe_part(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r'[\\/:*?"<>|]', "", text)
    text = re.sub(r"\s+", "", text)
    return text[:30]
