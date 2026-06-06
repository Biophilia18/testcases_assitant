from __future__ import annotations

from dataclasses import dataclass

from src.api_models import ApiTestCase


API_COVERAGE_ITEMS = [
    "正常请求",
    "参数校验",
    "鉴权校验",
    "权限校验",
    "业务规则",
    "幂等校验",
    "响应断言",
    "数据库校验",
]


@dataclass
class ApiCoverageItem:
    name: str
    covered: bool
    matched_case_ids: list[str]
    suggestion: str


def build_api_coverage_matrix(cases: list[ApiTestCase]) -> list[ApiCoverageItem]:
    matrix: list[ApiCoverageItem] = []
    for name in API_COVERAGE_ITEMS:
        matched_case_ids = _matched_case_ids(cases, name)
        covered = bool(matched_case_ids)
        matrix.append(
            ApiCoverageItem(
            name=name,
                covered=covered,
                matched_case_ids=matched_case_ids,
                suggestion=_coverage_suggestion(name, covered),
            )
        )
    return matrix


def api_coverage_matrix_to_rows(matrix: list[ApiCoverageItem]) -> list[dict[str, str]]:
    return [
        {
            "覆盖项": item.name,
            "是否覆盖": "是" if item.covered else "否",
            "命中用例": "、".join(item.matched_case_ids) if item.matched_case_ids else "-",
            "建议说明": item.suggestion,
        }
        for item in matrix
    ]


def _matched_case_ids(cases: list[ApiTestCase], coverage_name: str) -> list[str]:
    return [case.case_id for case in cases if _case_matches(case, coverage_name)]


def _case_matches(case: ApiTestCase, coverage_name: str) -> bool:
    text = " ".join(
        [
            case.case_type,
            case.steps,
            case.expected_status,
            case.assertions,
            case.remark,
            case.precondition,
            case.query_params,
            case.request_body,
            case.db_check,
        ]
    )
    if coverage_name == "正常请求":
        return "正常" in text or "合法请求" in text or case.expected_status == "200"
    if coverage_name == "参数校验":
        return any(keyword in text for keyword in ["参数校验", "必填", "类型错误", "边界", "非法", "400"])
    if coverage_name == "鉴权校验":
        return any(keyword in text for keyword in ["鉴权", "Token", "未登录", "401"])
    if coverage_name == "权限校验":
        return any(keyword in text for keyword in ["权限", "403", "无权限", "低权限"])
    if coverage_name == "业务规则":
        return any(keyword in text for keyword in ["业务规则", "规则不满足", "不满足业务"])
    if coverage_name == "幂等校验":
        return any(keyword in text for keyword in ["幂等", "重复请求", "重复提交", "连续发送"])
    if coverage_name == "响应断言":
        return any(keyword in text for keyword in ["响应字段", "字段类型", "响应示例", "必返字段", "断言"])
    if coverage_name == "数据库校验":
        return any(keyword in text for keyword in ["数据库", "数据表", "记录更新", "日志写入"])
    return False


def _coverage_suggestion(coverage_name: str, covered: bool) -> str:
    if covered:
        return "已识别到相关用例，仍建议结合接口文档复核断言是否足够明确。"

    suggestions = {
        "正常请求": "补充合法参数、合法请求体、有效鉴权下的主流程接口用例。",
        "参数校验": "补充必填为空、类型错误、枚举非法、边界值或超长值用例。",
        "鉴权校验": "补充未登录、Token 缺失、Token 无效或 Token 过期用例。",
        "权限校验": "补充低权限账号、跨租户、非资源归属者等权限不足用例。",
        "业务规则": "按业务规则逐条补充不满足条件的反向用例。",
        "幂等校验": "补充同一请求重复提交、重复点击或重试场景。",
        "响应断言": "补充状态码、业务码、必返字段、字段类型和值域断言。",
        "数据库校验": "补充接口调用后数据库新增、更新、状态变化或日志写入检查。",
    }
    return suggestions.get(coverage_name, "补充该覆盖项对应的接口测试用例。")
