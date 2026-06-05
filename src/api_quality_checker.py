from __future__ import annotations

from dataclasses import dataclass

from src.api_models import ApiDocument, ApiTestCase


@dataclass
class ApiQualityIssue:
    category: str
    severity: str
    case_ids: list[str]
    message: str
    suggestion: str


def analyze_api_quality(cases: list[ApiTestCase], document: ApiDocument | None = None) -> list[ApiQualityIssue]:
    issues: list[ApiQualityIssue] = []

    if not cases:
        return [
            ApiQualityIssue(
                category="用例数量",
                severity="错误",
                case_ids=[],
                message="当前没有接口测试用例。",
                suggestion="请先解析接口文档并生成接口测试用例。",
            )
        ]

    issues.extend(_required_field_issues(cases))
    issues.extend(_coverage_issues(cases, document or ApiDocument()))
    return issues


def api_quality_issues_to_rows(issues: list[ApiQualityIssue]) -> list[dict[str, str | int]]:
    return [
        {
            "分类": issue.category,
            "级别": issue.severity,
            "涉及用例": "、".join(issue.case_ids) if issue.case_ids else "-",
            "问题": issue.message,
            "建议": issue.suggestion,
        }
        for issue in issues
    ]


def api_quality_summary(cases: list[ApiTestCase], issues: list[ApiQualityIssue]) -> dict[str, int]:
    error_count = sum(1 for issue in issues if issue.severity == "错误")
    warning_count = sum(1 for issue in issues if issue.severity == "警告")
    covered_categories = len(_covered_categories(cases))
    return {
        "case_count": len(cases),
        "issue_count": len(issues),
        "error_count": error_count,
        "warning_count": warning_count,
        "covered_categories": covered_categories,
    }


def _required_field_issues(cases: list[ApiTestCase]) -> list[ApiQualityIssue]:
    checks = [
        ("接口名称", lambda case: bool(case.api_name.strip()), "补充接口名称，避免导出后无法定位接口。"),
        ("请求方法", lambda case: bool(case.method.strip()), "补充 GET/POST/PUT/PATCH/DELETE 等请求方法。"),
        ("接口路径", lambda case: bool(case.path.strip()), "补充接口路径，例如 /api/orders。"),
        ("操作步骤", lambda case: bool(case.steps.strip()), "补充构造请求、发送请求、检查响应等可执行步骤。"),
        ("预期状态码", lambda case: bool(case.expected_status.strip()), "补充预期 HTTP 状态码或业务状态码。"),
        ("预期结果", lambda case: bool(case.expected_result.strip()), "补充响应字段、错误信息、业务数据或数据库变化。"),
    ]

    issues: list[ApiQualityIssue] = []
    for category, is_valid, suggestion in checks:
        case_ids = [case.case_id for case in cases if not is_valid(case)]
        if case_ids:
            issues.append(
                ApiQualityIssue(
                    category="基础字段",
                    severity="错误",
                    case_ids=case_ids,
                    message=f"存在缺少{category}的接口用例。",
                    suggestion=suggestion,
                )
            )

    duplicate_ids = _duplicate_case_ids(cases)
    if duplicate_ids:
        issues.append(
            ApiQualityIssue(
                category="基础字段",
                severity="错误",
                case_ids=duplicate_ids,
                message="存在重复的接口用例编号。",
                suggestion="保持 API-01-01、API-01-02 这类编号唯一且连续。",
            )
        )
    return issues


def _coverage_issues(cases: list[ApiTestCase], document: ApiDocument) -> list[ApiQualityIssue]:
    issues: list[ApiQualityIssue] = []
    covered = _covered_categories(cases)

    required_checks = [
        ("正常请求", "缺少正常请求用例。", "至少保留一个合法请求，验证接口主流程可用。"),
        ("参数校验", "缺少参数校验用例。", "补充必填为空、类型错误或边界值用例。"),
        ("鉴权校验", "缺少鉴权校验用例。", "补充未登录、Token 缺失或 Token 无效场景。"),
    ]
    for category, message, suggestion in required_checks:
        if category not in covered:
            issues.append(ApiQualityIssue(category=category, severity="警告", case_ids=[], message=message, suggestion=suggestion))

    if document.auth.strip() and "权限校验" not in covered:
        issues.append(
            ApiQualityIssue(
                category="权限校验",
                severity="警告",
                case_ids=[],
                message="接口文档包含鉴权信息，但缺少权限不足用例。",
                suggestion="补充低权限账号、跨租户、非资源归属者等权限不足场景。",
            )
        )

    if document.business_rules.strip() and "业务规则" not in covered:
        issues.append(
            ApiQualityIssue(
                category="业务规则",
                severity="警告",
                case_ids=[],
                message="接口文档包含业务规则，但缺少业务规则不满足用例。",
                suggestion="按业务规则逐条补充不满足条件的反向用例。",
            )
        )

    if document.response_example.strip() and "响应断言" not in covered:
        issues.append(
            ApiQualityIssue(
                category="响应断言",
                severity="警告",
                case_ids=[],
                message="接口文档包含响应示例，但缺少响应字段断言用例。",
                suggestion="补充状态码、业务码、必返字段、字段类型和值域断言。",
            )
        )

    if document.db_checks.strip() and "数据库校验" not in covered:
        issues.append(
            ApiQualityIssue(
                category="数据库校验",
                severity="警告",
                case_ids=[],
                message="接口文档包含数据库校验，但缺少数据库校验用例。",
                suggestion="补充接口调用后数据库记录新增、更新、状态变化或日志写入检查。",
            )
        )

    weak_expected_case_ids = [case.case_id for case in cases if _is_weak_expected_result(case.expected_result)]
    if weak_expected_case_ids:
        issues.append(
            ApiQualityIssue(
                category="响应断言",
                severity="警告",
                case_ids=weak_expected_case_ids,
                message="部分用例预期结果过泛。",
                suggestion="避免只写“成功/失败/正常”，补充状态码、业务码、字段或数据变化。",
            )
        )

    return issues


def _covered_categories(cases: list[ApiTestCase]) -> set[str]:
    covered: set[str] = set()
    for case in cases:
        text = " ".join(
            [
                case.case_type,
                case.steps,
                case.expected_status,
                case.expected_result,
                case.remark,
                case.precondition,
            ]
        )
        if "正常" in text or "合法请求" in text or case.expected_status == "200":
            covered.add("正常请求")
        if any(keyword in text for keyword in ["参数校验", "必填", "类型错误", "边界", "非法"]):
            covered.add("参数校验")
        if any(keyword in text for keyword in ["鉴权", "Token", "未登录", "401"]):
            covered.add("鉴权校验")
        if any(keyword in text for keyword in ["权限", "403", "无权限", "低权限"]):
            covered.add("权限校验")
        if any(keyword in text for keyword in ["业务规则", "规则不满足", "不满足业务"]):
            covered.add("业务规则")
        if any(keyword in text for keyword in ["幂等", "重复请求", "重复提交"]):
            covered.add("幂等校验")
        if any(keyword in text for keyword in ["响应字段", "字段类型", "响应示例", "必返字段", "断言"]):
            covered.add("响应断言")
        if any(keyword in text for keyword in ["数据库", "数据表", "记录更新", "日志写入"]):
            covered.add("数据库校验")
    return covered


def _duplicate_case_ids(cases: list[ApiTestCase]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            duplicates.add(case.case_id)
        seen.add(case.case_id)
    return sorted(duplicates)


def _is_weak_expected_result(expected_result: str) -> bool:
    value = expected_result.strip()
    if not value:
        return False
    return value in {"成功", "失败", "正常", "接口成功", "接口失败", "返回成功", "返回失败"}
