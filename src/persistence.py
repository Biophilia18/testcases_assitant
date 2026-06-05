from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models import GenerationResult, TestCase


OUTPUT_DIR = Path("outputs")
LATEST_PATH = OUTPUT_DIR / "latest_cases.json"


def save_generation_result(result: GenerationResult, export_filename: str = "") -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = generation_result_to_payload(result, export_filename)

    LATEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_path = OUTPUT_DIR / f"cases_{timestamp}.json"
    history_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return LATEST_PATH


def load_latest_generation_result() -> tuple[GenerationResult, str]:
    return load_generation_result_from_path(LATEST_PATH)


def load_generation_result_from_path(path: str | Path) -> tuple[GenerationResult, str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload_to_generation_result(payload)


def load_generation_result_from_text(raw_text: str) -> tuple[GenerationResult, str]:
    payload = json.loads(raw_text)
    return payload_to_generation_result(payload)


def generation_result_to_payload(result: GenerationResult, export_filename: str = "") -> dict[str, Any]:
    return {
        "version": 1,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "export_filename": export_filename,
        "result": {
            "requested_mode": result.requested_mode,
            "actual_mode": result.actual_mode,
            "feature_count": result.feature_count,
            "case_count": result.case_count,
            "provider": result.provider,
            "model": result.model,
            "message": result.message,
            "fallback_reason": result.fallback_reason,
            "cases": [asdict(case) for case in result.cases],
        },
    }


def payload_to_generation_result(payload: dict[str, Any]) -> tuple[GenerationResult, str]:
    result_payload = payload.get("result", payload)
    cases = [TestCase(**case) for case in result_payload.get("cases", [])]
    result = GenerationResult(
        cases=cases,
        requested_mode=result_payload.get("requested_mode", "导入"),
        actual_mode=result_payload.get("actual_mode", "历史导入"),
        feature_count=int(result_payload.get("feature_count", 0) or 0),
        case_count=len(cases),
        provider=result_payload.get("provider", ""),
        model=result_payload.get("model", ""),
        message=result_payload.get("message", "已从本地 JSON 导入测试用例。"),
        fallback_reason=result_payload.get("fallback_reason", ""),
    )
    export_filename = payload.get("export_filename", "测试用例.xlsx")
    return result, export_filename

