from __future__ import annotations

from src.api.design_plan import ApiPlanItem, build_api_plan_items
from src.api.models import ApiDocument, ApiTestCase
from src.api.param_parser import ApiParam, parse_api_params


def generate_api_cases(
    document: ApiDocument,
    coverage_types: list[str] | None = None,
    strategy: str = "标准",
    business_rules: list[str] | None = None,
    plan_items: list[ApiPlanItem] | None = None,
) -> list[ApiTestCase]:
    if plan_items is None:
        plan_items = build_api_plan_items(
            document,
            coverage_types=coverage_types,
            strategy=strategy,
            included_business_rules=business_rules,
        )
    return generate_api_cases_from_plan(document, plan_items)


def generate_api_cases_from_plan(document: ApiDocument, plan_items: list[ApiPlanItem]) -> list[ApiTestCase]:
    cases: list[ApiTestCase] = []
    params = parse_api_params(document)

    for item in [plan_item for plan_item in plan_items if plan_item.included]:
        if item.coverage_type == "正常请求":
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
                remark=_plan_remark(item, "基础正向用例。需要结合真实响应字段补充精确断言。"),
            )
        elif item.coverage_type == "参数校验":
            _append_plan_param_case(cases, document, params, item)
        elif item.coverage_type == "鉴权校验":
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
                remark=_plan_remark(item, _auth_remark(document, "未鉴权或 Token 缺失。")),
            )
        elif item.coverage_type == "权限校验":
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
                remark=_plan_remark(item, "权限不足。需要结合角色权限矩阵补充具体账号。"),
            )
        elif item.coverage_type == "业务规则":
            _append_case(
                cases,
                document,
                case_type="业务规则",
                query_params=_valid_params(document),
                request_body=_valid_body(document),
                precondition=f"准备不满足业务规则的数据。\n业务规则：{item.source_name}",
                steps=_steps(document, "构造不满足业务规则的请求数据", "发送请求", "查看业务规则拦截结果"),
                expected_status="400",
                assertions="接口按业务规则拒绝请求，返回明确失败原因，不产生异常业务数据。",
                db_check="确认数据库未写入异常业务记录。",
                extract_vars="",
                priority="P1",
                remark=_plan_remark(item, f"业务规则不满足：{item.source_name}"),
            )
        elif item.coverage_type == "幂等校验":
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
                remark=_plan_remark(item, "重复请求/幂等性。若接口本身允许重复提交，需要调整预期。"),
            )
        elif item.coverage_type == "响应断言":
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
                remark=_plan_remark(item, "响应字段断言。建议补充必须返回字段和字段类型。"),
            )
        elif item.coverage_type == "数据库校验":
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
                db_check=item.source_name or document.db_checks.strip(),
                extract_vars=_extract_vars(document),
                priority="P2",
                remark=_plan_remark(item, "数据库校验。需要测试环境提供可核查的数据表或查询方式。"),
            )
    return cases


def _append_plan_param_case(
    cases: list[ApiTestCase],
    document: ApiDocument,
    params: list[ApiParam],
    item: ApiPlanItem,
) -> None:
    param = _find_param(params, item.source_name)
    if param:
        _append_param_case(
            cases,
            document,
            param,
            case_type=_param_case_type(item),
            action=_param_action(item),
            expected_status="400",
            assertions=_param_assertion(item),
            remark=_plan_remark(item, _param_remark(item)),
        )
        return

    _append_case(
        cases,
        document,
        case_type="参数校验",
        query_params=_invalid_params(document, item.suggested_test_point),
        request_body=_invalid_body(document, item.suggested_test_point),
        precondition=_valid_precondition(document),
        steps=_steps(document, "按计划项构造参数异常数据", "发送请求", "查看错误响应"),
        expected_status="400",
        assertions="接口返回明确参数错误信息；不产生新增、修改或状态变更等业务数据。",
        db_check="确认未产生异常业务数据。",
        extract_vars="",
        priority="P1",
        remark=_plan_remark(item, "接口文档未标明具体参数，需要人工确认关键参数。"),
    )


def build_api_plan_trace_rows(plan_items: list[ApiPlanItem], cases: list[ApiTestCase]) -> list[dict[str, str]]:
    rows = []
    for item in plan_items:
        matched_cases = [case for case in cases if item.plan_id and item.plan_id in case.remark]
        rows.append(
            {
                "计划ID": item.plan_id,
                "覆盖项": item.coverage_type,
                "来源": f"{item.source_type}/{item.source_name}",
                "是否参与": "是" if item.included else "否",
                "是否生成": "是" if matched_cases else "否",
                "对应用例编号": "、".join(case.case_id for case in matched_cases) if matched_cases else "-",
                "覆盖说明": _trace_description(item, matched_cases),
            }
        )
    return rows


def _trace_description(item: ApiPlanItem, matched_cases: list[ApiTestCase]) -> str:
    if not item.included:
        return "该计划项已取消参与生成。"
    if matched_cases:
        return "已根据计划项生成用例，建议继续检查断言和测试数据是否贴合业务。"
    return "未找到对应生成用例，请检查计划项是否被手动删除或生成逻辑是否覆盖该类型。"


def _find_param(params: list[ApiParam], name: str) -> ApiParam | None:
    return next((param for param in params if param.name == name), None)


def _param_action(item: ApiPlanItem) -> str:
    if "必填" in item.risk_type:
        return "置为空"
    if "类型" in item.risk_type:
        return "改为错误类型"
    if "枚举" in item.risk_type:
        return "设置为非法枚举值"
    if "格式" in item.risk_type:
        return "设置为错误格式"
    if "边界" in item.risk_type:
        return "设置为边界或非法值"
    if "归属" in item.risk_type:
        return "设置为非当前用户资源"
    if "存在" in item.risk_type:
        return "设置为不存在的数据"
    return item.suggested_test_point or "设置为异常值"


def _param_case_type(item: ApiPlanItem) -> str:
    return "边界值" if any(keyword in item.risk_type for keyword in ["边界", "枚举", "格式", "归属", "存在"]) else "参数校验"


def _param_assertion(item: ApiPlanItem) -> str:
    if "必填" in item.risk_type:
        return f"接口返回{item.source_name}不能为空、必填或参数缺失相关错误信息；不产生业务数据变更。"
    if "类型" in item.risk_type:
        return f"接口拒绝{item.source_name}错误类型参数，返回明确错误码和错误信息。"
    return f"接口按{item.source_name}字段规则处理{item.risk_type}，返回明确错误信息。"


def _param_remark(item: ApiPlanItem) -> str:
    if "必填" in item.risk_type:
        return f"必填参数为空：{item.source_name}"
    if "类型" in item.risk_type:
        return f"参数类型错误：{item.source_name}"
    if any(keyword in item.risk_type for keyword in ["边界", "枚举", "格式", "归属", "存在"]):
        return f"边界/非法值：{item.source_name}。风险类型：{item.risk_type}"
    return f"{item.risk_type}：{item.source_name}"


def _plan_remark(item: ApiPlanItem, remark: str) -> str:
    return f"{remark}\n计划ID：{item.plan_id}；风险来源：{item.source_type}/{item.source_name}；风险类型：{item.risk_type}"


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
    case_title: str = "",
) -> None:
    case_no = len(cases) + 1
    cases.append(
        ApiTestCase(
            case_id=f"API-01-{case_no:02d}",
            case_title=case_title or _default_case_title(document, case_type, remark),
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


def _default_case_title(document: ApiDocument, case_type: str, remark: str) -> str:
    api_name = document.api_name.strip() or "接口"
    first_remark = remark.splitlines()[0].strip()
    if case_type == "正常请求":
        return f"正常请求-{api_name}成功"
    if case_type == "鉴权校验":
        return "鉴权校验-未鉴权或Token缺失"
    if case_type == "权限校验":
        return "权限校验-低权限用户访问"
    if case_type == "幂等校验":
        return "幂等校验-重复提交请求"
    if case_type == "响应断言":
        return f"响应断言-{api_name}返回字段"
    if case_type == "数据库校验":
        return f"数据库校验-{api_name}数据一致"
    if first_remark:
        return first_remark
    return f"{case_type}-{api_name}"


def _steps(document: ApiDocument, first: str, second: str, third: str) -> str:
    api_name = document.api_name.strip() or "接口"
    return f"1. {first}：{api_name}\n2. {second}\n3. {third}"


def _valid_precondition(document: ApiDocument) -> str:
    if document.auth.strip():
        return f"准备有效鉴权信息：{document.auth.strip()}"
    return "准备接口可访问的测试环境"


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


def _format_param(param: ApiParam) -> str:
    parts = [param.name]
    if param.required:
        parts.append("必填")
    if param.param_type:
        parts.append(param.param_type)
    if param.rule:
        parts.append(param.rule)
    return "，".join(parts)
