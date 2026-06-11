from __future__ import annotations

from dataclasses import dataclass

from src.api.models import ApiDocument
from src.api.param_parser import parse_api_params


VALID_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


@dataclass
class ApiReliabilityIssue:
    category: str
    severity: str
    message: str
    suggestion: str


def assess_api_document_reliability(document: ApiDocument) -> list[ApiReliabilityIssue]:
    issues: list[ApiReliabilityIssue] = []

    method = document.method.strip().upper()
    path = document.path.strip()
    has_request_data = bool(document.params.strip() or document.body.strip() or parse_api_params(document))
    has_auth = document_has_auth(document)

    if not method:
        issues.append(
            ApiReliabilityIssue(
                category="基础信息",
                severity="错误",
                message="缺少请求方法，暂不建议生成接口用例。",
                suggestion="补充 GET/POST/PUT/PATCH/DELETE 等请求方法后再生成。",
            )
        )
    elif method not in VALID_HTTP_METHODS:
        issues.append(
            ApiReliabilityIssue(
                category="基础信息",
                severity="错误",
                message=f"请求方法 {document.method} 不在常见 HTTP 方法范围内。",
                suggestion="确认是否为 GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS 之一，避免生成错误请求方式。",
            )
        )

    if not path:
        issues.append(
            ApiReliabilityIssue(
                category="基础信息",
                severity="错误",
                message="缺少接口路径，暂不建议生成接口用例。",
                suggestion="补充接口路径，例如 /api/orders/{orderId}。",
            )
        )

    if not document.api_name.strip():
        issues.append(
            ApiReliabilityIssue(
                category="基础信息",
                severity="警告",
                message="缺少接口名称，生成结果可读性会下降。",
                suggestion="补充接口名称，方便用例标题、导出文件和测试计划追踪。",
            )
        )

    if not has_request_data:
        issues.append(
            ApiReliabilityIssue(
                category="参数信息",
                severity="警告",
                message="未识别到请求参数或请求体，不会自动编造参数级用例。",
                suggestion="如接口存在入参，请补充请求参数、字段说明或请求体 JSON。",
            )
        )

    if not has_auth:
        issues.append(
            ApiReliabilityIssue(
                category="鉴权信息",
                severity="建议",
                message="未识别到鉴权方式，不会默认生成 401/403 鉴权权限用例。",
                suggestion="如接口需要登录或权限控制，请补充 Bearer Token、Session、API Key 等说明。",
            )
        )

    if not document.response_example.strip():
        issues.append(
            ApiReliabilityIssue(
                category="响应断言",
                severity="建议",
                message="未提供响应示例，响应字段断言只能停留在通用描述。",
                suggestion="补充成功响应、失败响应、错误码或返回参数说明。",
            )
        )

    if not document.business_rules.strip():
        issues.append(
            ApiReliabilityIssue(
                category="业务规则",
                severity="建议",
                message="未识别到业务规则，业务反向场景覆盖会偏弱。",
                suggestion="补充权限、状态、库存、重复提交、归属关系等业务限制。",
            )
        )

    return issues


def api_reliability_issues_to_rows(issues: list[ApiReliabilityIssue]) -> list[dict[str, str]]:
    return [
        {
            "分类": issue.category,
            "级别": issue.severity,
            "提示": issue.message,
            "建议": issue.suggestion,
        }
        for issue in issues
    ]


def api_document_reliability_level(issues: list[ApiReliabilityIssue]) -> str:
    if any(issue.severity == "错误" for issue in issues):
        return "低"
    if sum(1 for issue in issues if issue.severity == "警告") >= 2:
        return "中"
    return "较高"


def api_document_generation_blockers(document: ApiDocument) -> list[ApiReliabilityIssue]:
    return [issue for issue in assess_api_document_reliability(document) if issue.severity == "错误"]


def document_has_auth(document: ApiDocument) -> bool:
    auth = document.auth.strip().lower()
    if not auth:
        return False
    return auth not in {"无", "none", "no", "无需鉴权", "不需要鉴权", "无需认证"}
