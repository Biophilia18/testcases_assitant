from __future__ import annotations

from src.api.design_plan import normalize_api_coverage_types, normalize_api_strategy, split_api_text_items
from src.api.models import ApiDocument, ApiTestCase
from src.api.param_parser import ApiParam, parse_api_params


def generate_api_cases(
    document: ApiDocument,
    coverage_types: list[str] | None = None,
    strategy: str = "标准",
    business_rules: list[str] | None = None,
) -> list[ApiTestCase]:
    cases: list[ApiTestCase] = []
    params = parse_api_params(document)
    selected_coverage = set(normalize_api_coverage_types(coverage_types))
    normalized_strategy = normalize_api_strategy(strategy)
    selected_business_rules = _selected_business_rules(document, business_rules)

    if "正常请求" in selected_coverage:
        _append_case(
            cases,
            document,
            case_type="正常请求",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition=_valid_precondition(document),
            steps=_steps(document, "构造合法请求", "发送请求", "查看状态码、响应体和业务数据"),
            expected_status="200",
            assertions=_success_assertions(document),
            db_check=document.db_checks.strip(),
            extract_vars=_extract_vars(document),
            priority="P1",
            remark="基础正向用例。需要结合真实响应字段补充精确断言。",
        )

    if "参数校验" in selected_coverage:
        required_params = [param for param in params if param.required]
        if required_params:
            for param in _select_params(required_params, normalized_strategy, max_standard=3):
                _append_param_case(
                    cases,
                    document,
                    param,
                    case_type="参数校验",
                    action="置为空",
                    expected_status="400",
                    assertions=f"接口返回{param.name}不能为空、必填或参数缺失相关错误信息；不产生业务数据变更。",
                    remark=f"必填参数为空：{param.name}",
                )
        else:
            _append_case(
                cases,
                document,
                case_type="参数校验",
                query_params=_invalid_params(document, "选择一个关键参数置为空"),
                request_body=_invalid_body(document, "选择一个关键字段置为空"),
                precondition=_valid_precondition(document),
                steps=_steps(document, "将关键参数或请求体字段置为空", "发送请求", "查看错误响应"),
                expected_status="400",
                assertions="接口返回明确参数错误信息；不产生新增、修改或状态变更等业务数据。",
                db_check="确认未产生异常业务数据。",
                extract_vars="",
                priority="P1",
                remark="接口文档未标明必填参数，需要人工确认关键参数。",
            )

        typed_params = [param for param in params if param.param_type]
        for param in _select_params(typed_params, normalized_strategy, max_standard=3):
            _append_param_case(
                cases,
                document,
                param,
                case_type="参数校验",
                action=f"改为错误类型（期望类型：{param.param_type}）",
                expected_status="400",
                assertions=f"接口拒绝{param.name}错误类型参数，返回明确错误码和错误信息。",
                remark=f"参数类型错误：{param.name}，期望类型 {param.param_type}",
            )

        rule_params = [param for param in params if _has_boundary_rule(param)]
        for param in _select_params(rule_params, normalized_strategy, max_standard=3):
            _append_param_case(
                cases,
                document,
                param,
                case_type="边界值",
                action=f"设置为边界或非法值（规则：{param.rule}）",
                expected_status="400",
                assertions=f"接口按{param.name}字段规则处理边界/非法值；非法值返回明确错误信息。",
                remark=f"边界/非法值：{param.name}。规则：{param.rule}",
            )

    if "鉴权校验" in selected_coverage:
        _append_case(
            cases,
            document,
            case_type="鉴权校验",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition="不传鉴权信息或移除 Token。",
            steps=_steps(document, "移除鉴权信息", "发送请求", "查看鉴权失败响应"),
            expected_status="401",
            assertions="接口拒绝访问，返回未鉴权提示，不泄露敏感数据。",
            db_check="确认未产生业务数据变更。",
            extract_vars="",
            priority="P1",
            remark=_auth_remark(document, "未鉴权或 Token 缺失。"),
        )

    if "权限校验" in selected_coverage and document.auth.strip():
        _append_case(
            cases,
            document,
            case_type="权限校验",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition=f"准备已登录但无权限的账号或低权限 Token。鉴权方式：{document.auth.strip()}",
            steps=_steps(document, "使用无权限账号或低权限 Token 构造请求", "发送请求", "查看权限校验结果"),
            expected_status="403",
            assertions="接口拒绝无权限操作，返回权限不足提示，不产生业务数据变更。",
            db_check="确认未产生业务数据变更。",
            extract_vars="",
            priority="P1",
            remark="权限不足。需要结合角色权限矩阵补充具体账号。",
        )

    if "业务规则" in selected_coverage and selected_business_rules:
        for rule in _select_rules(selected_business_rules, normalized_strategy):
            _append_case(
                cases,
                document,
                case_type="业务规则",
                query_params=_valid_params(document),
                request_body=_valid_body(document),
                precondition=f"准备不满足业务规则的数据。\n业务规则：{rule}",
                steps=_steps(document, "构造不满足业务规则的请求数据", "发送请求", "查看业务规则拦截结果"),
                expected_status="400",
                assertions="接口按业务规则拒绝请求，返回明确失败原因，不产生异常业务数据。",
                db_check="确认数据库未写入异常业务记录。",
                extract_vars="",
                priority="P1",
                remark=f"业务规则不满足：{rule}",
            )

    if "幂等校验" in selected_coverage:
        _append_case(
            cases,
            document,
            case_type="幂等校验",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition=_valid_precondition(document),
            steps=_steps(document, "使用同一请求数据连续发送两次", "对比两次响应", "检查业务数据是否重复产生"),
            expected_status="200",
            assertions="接口重复请求处理符合幂等预期；不会重复创建、重复扣减或产生脏数据。",
            db_check="确认数据库没有重复记录或异常状态变更。",
            extract_vars="",
            priority="P2",
            remark="重复请求/幂等性。若接口本身允许重复提交，需要调整预期。",
        )

    if "响应断言" in selected_coverage and document.response_example.strip():
        _append_case(
            cases,
            document,
            case_type="响应断言",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition=_valid_precondition(document),
            steps=_steps(document, "发送合法请求", "对照响应示例检查字段", "确认字段类型和值域"),
            expected_status="200",
            assertions=f"响应字段、字段类型、业务码和消息内容符合接口文档。\n响应示例：{document.response_example.strip()}",
            db_check=document.db_checks.strip(),
            extract_vars=_extract_vars(document),
            priority="P2",
            remark="响应字段断言。建议补充必须返回字段和字段类型。",
        )

    if "数据库校验" in selected_coverage and document.db_checks.strip():
        _append_case(
            cases,
            document,
            case_type="数据库校验",
            query_params=_valid_params(document),
            request_body=_valid_body(document),
            precondition=_valid_precondition(document),
            steps=_steps(document, "发送合法请求", "查询相关数据库记录", "核对数据库变更与接口响应"),
            expected_status="200",
            assertions="接口响应与数据库变更一致。",
            db_check=document.db_checks.strip(),
            extract_vars=_extract_vars(document),
            priority="P2",
            remark="数据库校验。需要测试环境提供可核查的数据表或查询方式。",
        )

    return cases


def _select_params(params: list[ApiParam], strategy: str, max_standard: int) -> list[ApiParam]:
    if strategy == "精简":
        return params[:1]
    if strategy == "完整":
        return params
    return params[:max_standard]


def _select_rules(rules: list[str], strategy: str) -> list[str]:
    if strategy == "精简":
        return rules[:1]
    if strategy == "完整":
        return rules
    return rules[:2]


def _selected_business_rules(document: ApiDocument, business_rules: list[str] | None) -> list[str]:
    if business_rules is not None:
        return [rule.strip() for rule in business_rules if rule.strip()]
    return split_api_text_items(document.business_rules)


def _append_param_case(
    cases: list[ApiTestCase],
    document: ApiDocument,
    param: ApiParam,
    case_type: str,
    action: str,
    expected_status: str,
    assertions: str,
    remark: str,
) -> None:
    _append_case(
        cases,
        document,
        case_type=case_type,
        query_params=_param_case_params(document, param, action),
        request_body=_param_case_body(document, param, action),
        precondition=_valid_precondition(document),
        steps=_steps(document, f"将{param.source}参数 {param.name} {action}", "发送请求", "查看参数校验结果"),
        expected_status=expected_status,
        assertions=assertions,
        db_check="确认未产生异常业务数据。",
        extract_vars="",
        priority="P1",
        remark=remark,
    )


def _append_case(
    cases: list[ApiTestCase],
    document: ApiDocument,
    case_type: str,
    query_params: str,
    request_body: str,
    precondition: str,
    steps: str,
    expected_status: str,
    assertions: str,
    db_check: str,
    extract_vars: str,
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
            headers=document.headers.strip(),
            query_params=query_params,
            request_body=request_body,
            precondition=precondition,
            steps=steps,
            expected_status=expected_status,
            assertions=assertions,
            db_check=db_check,
            extract_vars=extract_vars,
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
    return "\n".join(parts)


def _valid_params(document: ApiDocument) -> str:
    query_params = [param for param in parse_api_params(document) if param.source == "query"]
    if query_params:
        return "\n".join(_format_param(param) for param in query_params)
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


def _param_case_params(document: ApiDocument, param: ApiParam, action: str) -> str:
    if param.source == "query":
        return f"{_valid_params(document)}\n测试处理：{param.name} {action}"
    return _valid_params(document)


def _param_case_body(document: ApiDocument, param: ApiParam, action: str) -> str:
    if param.source == "body":
        return f"{_valid_body(document)}\n测试处理：{param.name} {action}"
    return _valid_body(document)


def _success_assertions(document: ApiDocument) -> str:
    if document.response_example.strip():
        return f"接口返回成功，状态码、业务码和响应字段符合接口文档。\n响应示例：{document.response_example.strip()}"
    return "接口返回成功；状态码、业务码、响应字段和业务数据符合接口文档。"


def _extract_vars(document: ApiDocument) -> str:
    response = document.response_example
    hints = []
    for keyword in ["id", "ID", "token", "Token", "appointmentNo", "orderNo"]:
        if keyword in response:
            hints.append(f"提取 {keyword} 供后续接口使用")
    return "\n".join(hints)


def _auth_remark(document: ApiDocument, fallback: str) -> str:
    if document.auth.strip():
        return f"{fallback}鉴权方式：{document.auth.strip()}"
    return f"{fallback}接口文档未说明鉴权方式，需要人工确认是否适用。"


def _has_boundary_rule(param: ApiParam) -> bool:
    text = f"{param.rule} {param.name}"
    return any(keyword in text for keyword in ["长度", "范围", "大于", "小于", "枚举", "允许值", "取值", "格式", "手机号", "不能早于", "不能晚于"])


def _format_param(param: ApiParam) -> str:
    parts = [param.name]
    if param.required:
        parts.append("必填")
    if param.param_type:
        parts.append(param.param_type)
    if param.rule:
        parts.append(param.rule)
    return "，".join(parts)
