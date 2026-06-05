from __future__ import annotations

from dataclasses import dataclass

from src.coverage_config import COVERAGE_TYPE_OPTIONS, infer_coverage_types, normalize_coverage_types
from src.models import TestCase


@dataclass(frozen=True)
class CoverageItem:
    coverage_type: str
    covered: bool
    case_ids: list[str]
    suggestion: str


SUGGESTIONS = {
    "正常流程": "补充至少一条主流程成功完成的用例。",
    "异常场景": "补充失败、必填缺失、业务规则不满足等异常场景。",
    "边界/非法输入": "补充边界值、非法格式、超长内容或特殊字符校验。",
    "权限控制": "补充无权限、登录态失效或越权访问场景。",
    "重复操作": "补充重复点击、重复提交或幂等性校验。",
    "数据一致性": "补充列表、详情、数据库或刷新后的数据一致性校验。",
    "弱网/超时": "补充弱网、断网、接口超时或加载失败场景。",
    "状态流转": "补充操作前后状态变化和状态回写校验。",
    "兼容性": "补充不同设备、浏览器或屏幕尺寸下的核心流程校验。",
}


def build_coverage_matrix(
    cases: list[TestCase],
    coverage_types: list[str] | None = None,
) -> list[CoverageItem]:
    selected_coverage_types = normalize_coverage_types(coverage_types) if coverage_types is not None else COVERAGE_TYPE_OPTIONS
    matched_cases = {coverage_type: [] for coverage_type in selected_coverage_types}

    for case in cases:
        matched_types = infer_case_coverage_types(case)
        for coverage_type in selected_coverage_types:
            if coverage_type in matched_types:
                matched_cases[coverage_type].append(case.case_id or "-")

    matrix: list[CoverageItem] = []
    for coverage_type in selected_coverage_types:
        case_ids = matched_cases[coverage_type]
        matrix.append(
            CoverageItem(
                coverage_type=coverage_type,
                covered=bool(case_ids),
                case_ids=case_ids,
                suggestion="已覆盖。" if case_ids else SUGGESTIONS.get(coverage_type, "建议补充该覆盖类型的用例。"),
            )
        )

    return matrix


def infer_case_coverage_types(case: TestCase) -> set[str]:
    text = " ".join(
        [
            case.title,
            case.case_type,
            case.remark,
            case.test_data,
            case.steps,
            case.expected_result,
        ]
    )
    return infer_coverage_types(text)


def coverage_matrix_to_rows(matrix: list[CoverageItem]) -> list[dict[str, str]]:
    return [
        {
            "覆盖项": item.coverage_type,
            "是否覆盖": "是" if item.covered else "否",
            "命中用例": "、".join(item.case_ids) if item.case_ids else "-",
            "建议说明": item.suggestion,
        }
        for item in matrix
    ]
