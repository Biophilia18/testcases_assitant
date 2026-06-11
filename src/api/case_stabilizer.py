from __future__ import annotations

import re
from dataclasses import replace

from src.api.models import ApiTestCase


API_STRATEGY_CASE_LIMITS = {
    "精简": 10,
    "标准": 18,
    "完整": 35,
}


def stabilize_api_cases(cases: list[ApiTestCase], strategy: str = "标准") -> list[ApiTestCase]:
    unique_cases = _deduplicate_cases(cases)
    limited_cases = unique_cases[: API_STRATEGY_CASE_LIMITS.get(strategy, API_STRATEGY_CASE_LIMITS["标准"])]
    return _renumber_cases(limited_cases)


def count_duplicate_api_cases(cases: list[ApiTestCase]) -> int:
    return len(cases) - len(_deduplicate_cases(cases))


def _deduplicate_cases(cases: list[ApiTestCase]) -> list[ApiTestCase]:
    result: list[ApiTestCase] = []
    seen: set[tuple[str, str, str, str]] = set()
    for case in cases:
        key = _case_key(case)
        if key in seen:
            continue
        seen.add(key)
        result.append(case)
    return result


def _case_key(case: ApiTestCase) -> tuple[str, str, str, str]:
    return (
        _normalize_text(case.case_type),
        _normalize_text(_risk_source(case.remark)),
        _normalize_text(_risk_type(case.remark)),
        _normalize_text(case.expected_status),
    )


def _risk_source(remark: str) -> str:
    match = re.search(r"风险来源：([^；\n]+)", remark)
    if match:
        return match.group(1)
    return remark.splitlines()[0] if remark.strip() else ""


def _risk_type(remark: str) -> str:
    match = re.search(r"风险类型：([^；\n]+)", remark)
    if match:
        return match.group(1)
    return remark.splitlines()[0] if remark.strip() else ""


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").lower()


def _renumber_cases(cases: list[ApiTestCase]) -> list[ApiTestCase]:
    return [replace(case, case_id=f"API-01-{index:02d}") for index, case in enumerate(cases, start=1)]
