from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from src.api.coverage_analyzer import build_api_coverage_matrix
from src.api.models import ApiDocument, ApiTestCase
from src.api.quality_checker import ApiQualityIssue, analyze_api_quality
from src.api.reliability import ApiReliabilityIssue, assess_api_document_reliability


@dataclass(frozen=True)
class ApiExportReviewItem:
    category: str
    severity: str
    case_ids: list[str]
    message: str
    suggestion: str


def build_api_export_review(cases: list[ApiTestCase], document: ApiDocument | None = None) -> list[ApiExportReviewItem]:
    document = document or ApiDocument()
    if not cases:
        return [
            ApiExportReviewItem(
                category="用例数量",
                severity="错误",
                case_ids=[],
                message="当前没有可导出的接口测试用例。",
                suggestion="请先确认接口文档并生成接口测试用例。",
            )
        ]

    review_items: list[ApiExportReviewItem] = []
    review_items.extend(_reliability_review_items(assess_api_document_reliability(document)))
    review_items.extend(_quality_review_items(analyze_api_quality(cases, document)))
    review_items.extend(_coverage_review_items(cases))
    review_items.extend(_manual_review_items(cases, document))
    return _deduplicate_review_items(review_items)


def api_export_review_summary(items: list[ApiExportReviewItem]) -> dict[str, int]:
    return {
        "total": len(items),
        "error_count": sum(1 for item in items if item.severity == "错误"),
        "warning_count": sum(1 for item in items if item.severity == "警告"),
        "suggestion_count": sum(1 for item in items if item.severity == "建议"),
    }


def api_export_review_to_rows(items: list[ApiExportReviewItem]) -> list[dict[str, str | int]]:
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


def _reliability_review_items(issues: list[ApiReliabilityIssue]) -> list[ApiExportReviewItem]:
    return [
        ApiExportReviewItem(
            category=f"文档可信度/{issue.category}",
            severity=_normalize_severity(issue.severity),
            case_ids=[],
            message=issue.message,
            suggestion=issue.suggestion,
        )
        for issue in issues
    ]


def _quality_review_items(issues: list[ApiQualityIssue]) -> list[ApiExportReviewItem]:
    grouped: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
    for issue in issues:
        grouped[(issue.category, _normalize_severity(issue.severity), issue.message, issue.suggestion)].extend(issue.case_ids)

    return [
        ApiExportReviewItem(
            category=category,
            severity=severity,
            case_ids=_unique(case_ids),
            message=message,
            suggestion=suggestion,
        )
        for (category, severity, message, suggestion), case_ids in grouped.items()
    ]


def _coverage_review_items(cases: list[ApiTestCase]) -> list[ApiExportReviewItem]:
    missing = [item for item in build_api_coverage_matrix(cases) if not item.covered]
    return [
        ApiExportReviewItem(
            category="覆盖提示",
            severity="建议",
            case_ids=[],
            message=f"未覆盖：{item.name}。",
            suggestion=item.suggestion,
        )
        for item in missing
    ]


def _manual_review_items(cases: list[ApiTestCase], document: ApiDocument) -> list[ApiExportReviewItem]:
    review_items: list[ApiExportReviewItem] = []

    if document.auth.strip():
        auth_case_ids = [case.case_id for case in cases if "401" in case.expected_status or "403" in case.expected_status]
        if len(auth_case_ids) < 2:
            review_items.append(
                ApiExportReviewItem(
                    category="鉴权权限",
                    severity="警告",
                    case_ids=auth_case_ids,
                    message="接口包含鉴权信息，但 401/403 覆盖可能不足。",
                    suggestion="导出前确认是否同时覆盖 Token 缺失/无效和权限不足两类场景。",
                )
            )

    token_case_ids = [
        case.case_id
        for case in cases
        if any(token in case.headers for token in ["${token}", "{token}", "Bearer Token", "Authorization"])
    ]
    if token_case_ids:
        review_items.append(
            ApiExportReviewItem(
                category="运行数据",
                severity="建议",
                case_ids=token_case_ids,
                message="部分接口用例包含 token 或 Authorization 占位。",
                suggestion="导出后需人工补充真实登录账号、token 获取方式或环境变量，不要直接按草稿执行。",
            )
        )

    if document.db_checks.strip():
        db_case_ids = [case.case_id for case in cases if case.db_check.strip()]
        if not any("select" in case.db_check.lower() for case in cases):
            review_items.append(
                ApiExportReviewItem(
                    category="数据库校验",
                    severity="建议",
                    case_ids=db_case_ids,
                    message="接口文档包含数据库校验，但用例中未识别到可执行 SQL。",
                    suggestion="导出前补充数据表、字段、状态值或 SQL 草稿，至少说明核对目标。",
                )
            )

    weak_assertion_ids = [case.case_id for case in cases if _is_weak_assertion(case.assertions)]
    if weak_assertion_ids:
        review_items.append(
            ApiExportReviewItem(
                category="响应断言",
                severity="警告",
                case_ids=weak_assertion_ids,
                message="部分接口断言过泛，可能无法判断真实业务正确性。",
                suggestion="建议补充 HTTP 状态码、业务 code、message、data 字段和关键业务值断言。",
            )
        )

    return review_items


def _normalize_severity(severity: str) -> str:
    if severity == "错误":
        return "错误"
    if severity == "警告":
        return "警告"
    return "建议"


def _is_weak_assertion(assertions: str) -> bool:
    value = assertions.strip()
    return value in {"成功", "失败", "正常", "接口成功", "接口失败", "返回成功", "返回失败"}


def _deduplicate_review_items(items: list[ApiExportReviewItem]) -> list[ApiExportReviewItem]:
    result: list[ApiExportReviewItem] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        key = (item.category, item.severity, item.message)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _unique(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
