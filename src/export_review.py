from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from src.models import TestCase
from src.quality_checker import QualityIssue, check_cases
from src.requirement_trace import build_requirement_trace


@dataclass(frozen=True)
class ExportReviewItem:
    category: str
    severity: str
    case_ids: list[str]
    message: str
    suggestion: str


def build_export_review(
    cases: list[TestCase],
    coverage_types: list[str] | None = None,
    requirement_text: str = "",
) -> list[ExportReviewItem]:
    review_items: list[ExportReviewItem] = []
    if not cases:
        return [
            ExportReviewItem(
                category="用例数量",
                severity="错误",
                case_ids=[],
                message="当前没有可导出的功能测试用例。",
                suggestion="请先生成用例，或导入历史 JSON 后再导出。",
            )
        ]

    review_items.extend(_quality_issue_review_items(check_cases(cases, coverage_types)))
    review_items.extend(_requirement_trace_review_items(cases, requirement_text))
    review_items.extend(_manual_review_items(cases))
    return review_items


def export_review_summary(items: list[ExportReviewItem]) -> dict[str, int]:
    return {
        "total": len(items),
        "error_count": sum(1 for item in items if item.severity == "错误"),
        "warning_count": sum(1 for item in items if item.severity == "警告"),
        "suggestion_count": sum(1 for item in items if item.severity == "建议"),
    }


def export_review_to_rows(items: list[ExportReviewItem]) -> list[dict[str, str | int]]:
    return [
        {
            "分类": item.category,
            "级别": item.severity,
            "涉及用例": "、".join(item.case_ids) if item.case_ids else "-",
            "问题": item.message,
            "建议": item.suggestion,
        }
        for item in items
    ]


def _quality_issue_review_items(issues: list[QualityIssue]) -> list[ExportReviewItem]:
    grouped: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for issue in issues:
        severity = "错误" if issue.severity == "错误" else "警告"
        category = _issue_category(issue.message)
        grouped[(category, severity, issue.message)].append(issue.case_id)

    return [
        ExportReviewItem(
            category=category,
            severity=severity,
            case_ids=_unique(case_ids),
            message=message,
            suggestion=_category_suggestion(category),
        )
        for (category, severity, message), case_ids in grouped.items()
    ]


def _requirement_trace_review_items(cases: list[TestCase], requirement_text: str) -> list[ExportReviewItem]:
    if not requirement_text.strip():
        return [
            ExportReviewItem(
                category="需求追踪",
                severity="建议",
                case_ids=[],
                message="未找到本次生成的完整需求文本，导出前无法做需求规则覆盖追踪。",
                suggestion="如果是从历史 JSON 导入，建议对照原始需求人工确认验收标准和异常规则是否覆盖。",
            )
        ]

    trace_items = build_requirement_trace(cases, requirement_text)
    missing_items = [item for item in trace_items if not item.covered]
    return [
        ExportReviewItem(
            category="需求规则",
            severity="警告",
            case_ids=[],
            message=f"{item.source_type}未匹配到相关用例：{item.content}",
            suggestion=item.suggestion,
        )
        for item in missing_items
    ]


def _manual_review_items(cases: list[TestCase]) -> list[ExportReviewItem]:
    items: list[ExportReviewItem] = []

    duplicate_titles = _duplicate_titles(cases)
    if duplicate_titles:
        items.append(
            ExportReviewItem(
                category="用例标题",
                severity="建议",
                case_ids=duplicate_titles,
                message="部分用例标题重复，导出后不利于快速判断测试目标。",
                suggestion="建议把标题改成“场景 + 条件 + 预期方向”，例如“预约时间早于当前时间-提交失败”。",
            )
        )

    if not any(case.priority in {"P0", "P1"} for case in cases):
        items.append(
            ExportReviewItem(
                category="优先级",
                severity="建议",
                case_ids=[],
                message="当前用例中没有 P0/P1 优先级。",
                suggestion="建议至少把主流程、核心异常、权限或数据一致性用例标为 P0/P1，方便执行排序。",
            )
        )

    if not any(_has_data_assertion(case) for case in cases):
        items.append(
            ExportReviewItem(
                category="数据校验",
                severity="建议",
                case_ids=[],
                message="未明显识别到数据记录、状态变更或列表详情回显类校验。",
                suggestion="导出前建议确认是否需要补充数据库记录、状态流转、详情页回显或导出结果校验。",
            )
        )

    return items


def _issue_category(message: str) -> str:
    if any(keyword in message for keyword in ["用例编号", "用例标题", "操作步骤", "预期结果", "优先级", "重复"]):
        return "基础字段"
    if "测试数据" in message:
        return "测试数据"
    if "缺少" in message and "用例" in message:
        return "覆盖缺口"
    return "内容质量"


def _category_suggestion(category: str) -> str:
    suggestions = {
        "基础字段": "补齐导出必需字段，优先检查编号、标题、步骤、预期结果和优先级。",
        "测试数据": "补充账号、参数、边界值或业务数据编号，避免执行时无法复现。",
        "覆盖缺口": "根据缺失覆盖项补充对应场景，优先补异常、边界、权限和数据一致性。",
        "内容质量": "导出前抽查步骤和预期结果，避免只写“成功/正常/通过”。",
    }
    return suggestions.get(category, "结合提示逐项复核。")


def _duplicate_titles(cases: list[TestCase]) -> list[str]:
    title_to_ids: dict[str, list[str]] = defaultdict(list)
    for case in cases:
        title = case.title.strip()
        if title:
            title_to_ids[title].append(case.case_id)
    duplicate_ids: list[str] = []
    for case_ids in title_to_ids.values():
        if len(case_ids) > 1:
            duplicate_ids.extend(case_ids)
    return duplicate_ids


def _has_data_assertion(case: TestCase) -> bool:
    text = f"{case.expected_result} {case.steps} {case.remark}"
    return any(keyword in text for keyword in ["数据库", "记录", "状态", "回显", "列表", "详情", "导出", "一致"])


def _unique(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
