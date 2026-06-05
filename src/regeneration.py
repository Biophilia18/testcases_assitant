from __future__ import annotations

import re

from src.models import TestCase


REGENERATION_FOCUS_OPTIONS = ["综合补全", "异常场景", "边界场景", "权限场景", "数据一致性"]

FOCUS_TO_COVERAGE_TYPES = {
    "综合补全": [],
    "异常场景": ["异常场景", "重复操作", "弱网/超时"],
    "边界场景": ["边界/非法输入"],
    "权限场景": ["权限控制"],
    "数据一致性": ["数据一致性", "状态流转"],
}


def build_regeneration_requirement(
    group_key: str,
    cases: list[TestCase],
    full_requirement_text: str,
    focus: str,
) -> str:
    case = cases[0]
    return "\n".join(
        [
            f"只重新生成这个功能点：{group_key}",
            f"重新生成侧重点：{focus}",
            f"模块：{case.module}",
            f"功能点：{case.feature}",
            "",
            "完整原始需求上下文：",
            full_requirement_text.strip(),
            "",
            "已有用例摘要：",
            *[f"- {item.case_id} {item.title}" for item in cases[:10]],
            "",
            "要求：保留同一功能点语义，结合完整需求上下文重新生成更完整、更可执行的测试用例。",
        ]
    )


def coverage_types_for_focus(focus: str, default_coverage_types: list[str]) -> list[str]:
    focused = FOCUS_TO_COVERAGE_TYPES.get(focus, [])
    return focused or default_coverage_types


def replace_group_preserving_case_ids(
    current_cases: list[TestCase],
    group_key: str,
    regenerated_cases: list[TestCase],
) -> list[TestCase]:
    target_cases = [case for case in current_cases if _group_key(case) == group_key]
    if not target_cases:
        return current_cases

    prefix = _case_id_prefix(target_cases[0].case_id)
    renumbered_regenerated = []
    for index, case in enumerate(regenerated_cases, start=1):
        case.case_id = f"{prefix}-{index:02d}" if prefix else f"TC-RE-{index:02d}"
        renumbered_regenerated.append(case)

    merged: list[TestCase] = []
    inserted = False
    for case in current_cases:
        if _group_key(case) == group_key:
            if not inserted:
                merged.extend(renumbered_regenerated)
                inserted = True
            continue
        merged.append(case)

    return merged


def _group_key(case: TestCase) -> str:
    module = case.module or "未指定模块"
    feature = case.feature or "未指定功能点"
    return f"{module} / {feature}"


def _case_id_prefix(case_id: str) -> str:
    match = re.match(r"^(TC-\d{2})-\d{2}$", case_id or "")
    if match:
        return match.group(1)
    return ""
