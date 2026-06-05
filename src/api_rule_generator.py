from __future__ import annotations

from src.api_models import ApiDocument, ApiTestCase


def generate_api_cases(document: ApiDocument) -> list[ApiTestCase]:
    cases: list[ApiTestCase] = []

    _append_case(
        cases,
        document,
        case_type="正常请求",
        query_params=_valid_params(document),
        request_body=_valid_body(document),
        precondition=_valid_precondition(document),
        steps=_steps(document, "构造合法请求", "发送请求", "查看状态码、响应体和业务数据"),
        expected_status="200",
        expected_result=_success_expected_result(document),
        priority="P1",
        remark="基础正向用例。需要结合真实响应字段补充精确断言。",
    )

    _append_case(
        cases,
        document,
        case_type="参数校验",
        query_params=_invalid_params(document, "必填参数置为空"),
        request_body=_invalid_body(document, "必填字段置为空"),
        precondition=_valid_precondition(document),
        steps=_steps(document, "将必填参数或请求体字段置为空", "发送请求", "查看错误响应"),
        expected_status="400",
        expected_result="接口返回明确参数错误信息；不产生新增、修改或状态变更等业务数据。",
        priority="P1",
        remark="必填参数为空。若接口文档没有标明必填字段，需要人工确认。",
    )

    if _has_request_data(document):
        _append_case(
            cases,
            document,
            case_type="参数校验",
            query_params=_invalid_params(document, "参数类型改为非法类型"),
            request_body=_invalid_body(document, "字段类型改为非法类型"),
            precondition=_valid_precondition(document),
            steps=_steps(document, "将参数或请求体字段改为错误类型", "发送请求", "查看参数校验结果"),
            expected_status="400",
            expected_result="接口拒绝错误类型参数，返回明确错误码和错误信息。",
            priority="P1",
            remark="参数类型错误。建议补充具体字段、类型和非法值。",
        )
        _append_case(
            cases,
            document,
            case_type="边界值",
            query_params=_invalid_params(document, "使用边界值或超长值"),
            request_body=_invalid_body(document, "使用边界值或超长值"),
            precondition=_valid_precondition(document),
            steps=_steps(document, "准备边界值、超长值或超出范围的字段", "发送请求", "查看边界处理结果"),
            expected_status="400",
            expected_result="接口按字段规则处理边界值；非法边界值返回明确错误信息，合法边界值正常处理。",
            priority="P2",
            remark="参数边界值。需要结合字段长度、枚举、数值范围细化。",
        )

    _append_case(
        cases,
        document,
        case_type="鉴权校验",
        query_params=_valid_params(document),
        request_body=_valid_body(document),
        precondition="不传鉴权信息或移除 Token。",
        steps=_steps(document, "移除鉴权信息", "发送请求", "查看鉴权失败响应"),
        expected_status="401",
        expected_result="接口拒绝访问，返回未鉴权提示，不泄露敏感数据。",
        priority="P1",
        remark=_auth_remark(document, "未鉴权或 Token 缺失。"),
    )

    if document.auth.strip():
        _append_case(
            cases,
            document,
            case_type="权限校验",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition=f"准备已登录但无权限的账号或低权限 Token。鉴权方式：{document.auth.strip()}",
            steps=_steps(document, "使用无权限账号或低权限 Token 构造请求", "发送请求", "查看权限校验结果"),
            expected_status="403",
            expected_result="接口拒绝无权限操作，返回权限不足提示，不产生业务数据变更。",
            priority="P1",
            remark="权限不足。需要结合角色权限矩阵补充具体账号。",
        )

    if document.business_rules.strip():
        _append_case(
            cases,
            document,
            case_type="业务规则",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition=f"准备不满足业务规则的数据。\n业务规则：{document.business_rules.strip()}",
            steps=_steps(document, "构造不满足业务规则的请求数据", "发送请求", "查看业务规则拦截结果"),
            expected_status="400",
            expected_result="接口按业务规则拒绝请求，返回明确失败原因，不产生异常业务数据。",
            priority="P1",
            remark="业务规则不满足。需要按每条规则拆分更细用例。",
        )

    _append_case(
        cases,
        document,
        case_type="幂等校验",
        query_params=_valid_params(document),
        request_body=_valid_body(document),
        precondition=_valid_precondition(document),
        steps=_steps(document, "使用同一请求数据连续发送两次", "对比两次响应", "检查业务数据是否重复产生"),
        expected_status="200",
        expected_result="接口重复请求处理符合幂等预期；不会重复创建、重复扣减或产生脏数据。",
        priority="P2",
        remark="重复请求/幂等性。若接口本身允许重复提交，需要调整预期。",
    )

    if document.response_example.strip():
        _append_case(
            cases,
            document,
            case_type="响应断言",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition=_valid_precondition(document),
            steps=_steps(document, "发送合法请求", "对照响应示例检查字段", "确认字段类型和值域"),
            expected_status="200",
            expected_result=f"响应字段、字段类型、业务码和消息内容符合接口文档。\n响应示例：{document.response_example.strip()}",
            priority="P2",
            remark="响应字段断言。建议补充必须返回字段和字段类型。",
        )

    if document.db_checks.strip():
        _append_case(
            cases,
            document,
            case_type="数据库校验",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition=_valid_precondition(document),
            steps=_steps(document, "发送合法请求", "查询相关数据库记录", "核对数据库变更与接口响应"),
            expected_status="200",
            expected_result=f"数据库记录与接口处理结果一致。\n数据库校验：{document.db_checks.strip()}",
            priority="P2",
            remark="数据库校验。需要测试环境提供可核查的数据表或查询方式。",
        )

    return cases


def _append_case(
    cases: list[ApiTestCase],
    document: ApiDocument,
    case_type: str,
    query_params: str,
    request_body: str,
    precondition: str,
    steps: str,
    expected_status: str,
    expected_result: str,
    priority: str,
    remark: str,
) -> None:
    case_no = len(cases) + 1
    cases.append(
        ApiTestCase(
            case_id=f"API-01-{case_no:02d}",
            module=document.module.strip() or "接口模块",
            api_name=document.api_name.strip() or "示例接口",
            method=document.method.strip() or "POST",
            path=document.path.strip() or "/api/example",
            query_params=query_params,
            request_body=request_body,
            precondition=precondition,
            steps=steps,
            expected_status=expected_status,
            expected_result=expected_result,
            priority=priority,
            case_type=case_type,
            remark=remark,
        )
    )


def _steps(document: ApiDocument, first: str, second: str, third: str) -> str:
    api_name = document.api_name.strip() or "接口"
    return f"1. {first}：{api_name}\n2. {second}\n3. {third}"


def _valid_precondition(document: ApiDocument) -> str:
    parts = []
    if document.auth.strip():
        parts.append(f"准备有效鉴权信息：{document.auth.strip()}")
    else:
        parts.append("准备接口可访问的测试环境")
    if document.headers.strip():
        parts.append(f"请求头：{document.headers.strip()}")
    return "\n".join(parts)


def _valid_params(document: ApiDocument) -> str:
    return document.params.strip() or "按接口文档填写合法请求参数"


def _valid_body(document: ApiDocument) -> str:
    return document.body.strip()


def _invalid_params(document: ApiDocument, note: str) -> str:
    if document.params.strip():
        return f"{document.params.strip()}\n测试处理：{note}"
    return f"按接口文档选择一个必填参数，测试处理：{note}"


def _invalid_body(document: ApiDocument, note: str) -> str:
    if document.body.strip():
        return f"{document.body.strip()}\n测试处理：{note}"
    return ""


def _success_expected_result(document: ApiDocument) -> str:
    if document.response_example.strip():
        return f"接口返回成功，响应内容符合接口文档。\n响应示例：{document.response_example.strip()}"
    return "接口返回成功；状态码、业务码、响应字段和业务数据符合接口文档。"


def _auth_remark(document: ApiDocument, fallback: str) -> str:
    if document.auth.strip():
        return f"{fallback}鉴权方式：{document.auth.strip()}"
    return f"{fallback}接口文档未说明鉴权方式，需要人工确认是否适用。"


def _has_request_data(document: ApiDocument) -> bool:
    return bool(document.params.strip() or document.body.strip())
