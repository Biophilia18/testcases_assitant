from __future__ import annotations

from dataclasses import dataclass

from src.api.coverage_analyzer import API_COVERAGE_ITEMS
from src.api.models import ApiDocument
from src.api.param_parser import ApiParam, parse_api_params
from src.api.reliability import document_has_auth


API_GENERATION_STRATEGIES = ["精简", "标准", "完整"]


@dataclass
class ApiParamRisk:
    param_name: str
    source: str
    required: bool
    param_type: str
    rule: str
    risk_type: str
    suggested_test_point: str


@dataclass
class ApiBusinessRuleRisk:
    content: str
    risk_type: str
    suggested_test_point: str
    included: bool = True


@dataclass
class ApiPlanItem:
    plan_id: str
    coverage_type: str
    source_type: str
    source_name: str
    risk_type: str
    suggested_test_point: str
    estimated_count: int
    included: bool


@dataclass
class ApiDesignPlan:
    param_risks: list[ApiParamRisk]
    business_rule_risks: list[ApiBusinessRuleRisk]
    db_checks: list[str]
    planned_case_types: list[str]
    estimated_case_count: int
    coverage_types: list[str]
    strategy: str
    plan_items: list[ApiPlanItem]


def build_api_design_plan(
    document: ApiDocument,
    coverage_types: list[str] | None = None,
    strategy: str = "标准",
    included_business_rules: list[str] | None = None,
    included_param_names: list[str] | None = None,
) -> ApiDesignPlan:
    selected_coverage = normalize_api_coverage_types(coverage_types)
    normalized_strategy = normalize_api_strategy(strategy)
    param_risks = analyze_param_risks(document)
    business_rule_risks = analyze_business_rule_risks(document, included_business_rules)
    db_checks = split_api_text_items(document.db_checks)
    plan_items = build_api_plan_items(
        document,
        coverage_types=selected_coverage,
        strategy=normalized_strategy,
        included_business_rules=included_business_rules,
        included_param_names=included_param_names,
    )
    planned_case_types = _planned_case_types(plan_items)
    estimated_case_count = sum(item.estimated_count for item in plan_items if item.included)
    return ApiDesignPlan(
        param_risks=param_risks,
        business_rule_risks=business_rule_risks,
        db_checks=db_checks,
        planned_case_types=planned_case_types,
        estimated_case_count=estimated_case_count,
        coverage_types=selected_coverage,
        strategy=normalized_strategy,
        plan_items=plan_items,
    )


def build_api_plan_items(
    document: ApiDocument,
    coverage_types: list[str] | None = None,
    strategy: str = "标准",
    included_business_rules: list[str] | None = None,
    included_param_names: list[str] | None = None,
) -> list[ApiPlanItem]:
    selected_coverage = set(normalize_api_coverage_types(coverage_types))
    normalized_strategy = normalize_api_strategy(strategy)
    included_rules = _included_set(included_business_rules)
    included_params = _included_set(included_param_names)
    param_risks = analyze_param_risks(document)
    business_rule_risks = analyze_business_rule_risks(document, included_business_rules)
    db_checks = split_api_text_items(document.db_checks)

    items: list[ApiPlanItem] = []
    if "正常请求" in selected_coverage:
        items.append(_fixed_item("PLAN-FIX-001", "正常请求", "基础正向", "主流程", "合法请求验证"))

    if "参数校验" in selected_coverage:
        param_points = _select_param_plan_points(_param_plan_points(param_risks), normalized_strategy)
        for index, (risk, risk_type, test_point) in enumerate(param_points, start=1):
            included = not included_params or risk.param_name in included_params
            items.append(
                ApiPlanItem(
                    plan_id=f"PLAN-PARAM-{index:03d}",
                    coverage_type="参数校验",
                    source_type="param",
                    source_name=risk.param_name,
                    risk_type=risk_type,
                    suggested_test_point=test_point,
                    estimated_count=1,
                    included=included,
                )
            )
        if not param_risks:
            items.append(
                ApiPlanItem(
                    plan_id="PLAN-PARAM-001",
                    coverage_type="参数校验",
                    source_type="fixed",
                    source_name="关键参数",
                    risk_type="参数信息不足",
                    suggested_test_point="接口文档未说明请求参数，需人工补充参数后再生成参数校验用例。",
                    estimated_count=0,
                    included=False,
                )
            )

    if "鉴权校验" in selected_coverage and document_has_auth(document):
        items.append(_fixed_item("PLAN-AUTH-001", "鉴权校验", "鉴权信息", "未鉴权", "移除 Token 或鉴权信息"))

    if "权限校验" in selected_coverage and document_has_auth(document):
        items.append(_fixed_item("PLAN-PERM-001", "权限校验", "权限角色", "权限不足", "使用低权限账号或非授权资源"))

    if "业务规则" in selected_coverage:
        selected_rule_risks = [risk for risk in business_rule_risks if risk.included]
        selected_rule_risks = _select_business_risks(selected_rule_risks, normalized_strategy)
        for index, risk in enumerate(selected_rule_risks, start=1):
            included = not included_rules or risk.content in included_rules
            items.append(
                ApiPlanItem(
                    plan_id=f"PLAN-BIZ-{index:03d}",
                    coverage_type="业务规则",
                    source_type="business_rule",
                    source_name=risk.content,
                    risk_type=risk.risk_type,
                    suggested_test_point=risk.suggested_test_point,
                    estimated_count=1,
                    included=included,
                )
            )

    if "幂等校验" in selected_coverage:
        items.append(_fixed_item("PLAN-IDEMP-001", "幂等校验", "重复请求", "重复提交", "连续提交同一请求并检查数据不重复"))

    if "响应断言" in selected_coverage and document.response_example.strip():
        items.append(_fixed_item("PLAN-RESP-001", "响应断言", "响应示例", "字段断言", "校验状态码、业务码、必返字段和字段类型", source_type="response"))

    if "数据库校验" in selected_coverage:
        for index, db_check in enumerate(db_checks, start=1):
            items.append(
                ApiPlanItem(
                    plan_id=f"PLAN-DB-{index:03d}",
                    coverage_type="数据库校验",
                    source_type="db_check",
                    source_name=db_check,
                    risk_type="数据一致性",
                    suggested_test_point=f"检查数据库变化：{db_check}",
                    estimated_count=1,
                    included=True,
                )
            )
    return items


def analyze_param_risks(document: ApiDocument) -> list[ApiParamRisk]:
    return [_param_to_risk(param) for param in parse_api_params(document)]


def analyze_business_rule_risks(document: ApiDocument, included_rules: list[str] | None = None) -> list[ApiBusinessRuleRisk]:
    selected = {rule.strip() for rule in included_rules or [] if rule.strip()}
    use_selected = included_rules is not None
    risks = []
    for rule in split_api_text_items(document.business_rules):
        risk_type = _business_rule_risk_type(rule)
        risks.append(
            ApiBusinessRuleRisk(
                content=rule,
                risk_type=risk_type,
                suggested_test_point=_business_rule_test_point(rule, risk_type),
                included=(rule in selected) if use_selected else True,
            )
        )
    return risks


def estimate_api_case_count(
    document: ApiDocument,
    coverage_types: list[str] | None = None,
    strategy: str = "标准",
    included_business_rules: list[str] | None = None,
    included_param_names: list[str] | None = None,
) -> int:
    return sum(
        item.estimated_count
        for item in build_api_plan_items(
            document,
            coverage_types=coverage_types,
            strategy=strategy,
            included_business_rules=included_business_rules,
            included_param_names=included_param_names,
        )
        if item.included
    )


def normalize_api_coverage_types(coverage_types: list[str] | None) -> list[str]:
    if coverage_types is None:
        return list(API_COVERAGE_ITEMS)
    return [item for item in API_COVERAGE_ITEMS if item in set(coverage_types)]


def normalize_api_strategy(strategy: str) -> str:
    return strategy if strategy in API_GENERATION_STRATEGIES else "标准"


def split_api_text_items(text: str) -> list[str]:
    items: list[str] = []
    for raw_line in text.splitlines():
        line = _clean_item(raw_line)
        if not line:
            continue
        if "；" in line:
            parts = [_clean_item(part) for part in line.split("；")]
            items.extend(part for part in parts if part)
        else:
            items.append(line)
    return _unique(items)


def param_risks_to_rows(risks: list[ApiParamRisk]) -> list[dict[str, str | bool]]:
    return [
        {
            "参数名": risk.param_name,
            "参数来源": risk.source,
            "是否必填": "是" if risk.required else "否",
            "参数类型": risk.param_type or "-",
            "识别到的规则": risk.rule or "-",
            "风险类型": risk.risk_type,
            "建议测试点": risk.suggested_test_point,
            "是否参与生成": True,
        }
        for risk in risks
    ]


def business_rule_risks_to_rows(risks: list[ApiBusinessRuleRisk]) -> list[dict[str, str | bool]]:
    return [
        {
            "规则内容": risk.content,
            "风险类型": risk.risk_type,
            "建议测试点": risk.suggested_test_point,
            "是否参与生成": risk.included,
        }
        for risk in risks
    ]


def plan_items_to_rows(items: list[ApiPlanItem]) -> list[dict[str, str | int | bool]]:
    return [
        {
            "计划ID": item.plan_id,
            "覆盖项": item.coverage_type,
            "来源类型": item.source_type,
            "来源名称": item.source_name,
            "风险类型": item.risk_type,
            "建议测试点": item.suggested_test_point,
            "预计用例数": item.estimated_count,
            "是否参与生成": item.included,
        }
        for item in items
    ]


def rows_to_plan_items(rows) -> list[ApiPlanItem]:
    if hasattr(rows, "to_dict"):
        rows = rows.to_dict("records")
    items = []
    for row in rows:
        items.append(
            ApiPlanItem(
                plan_id=str(row.get("计划ID", "")).strip(),
                coverage_type=str(row.get("覆盖项", "")).strip(),
                source_type=str(row.get("来源类型", "")).strip(),
                source_name=str(row.get("来源名称", "")).strip(),
                risk_type=str(row.get("风险类型", "")).strip(),
                suggested_test_point=str(row.get("建议测试点", "")).strip(),
                estimated_count=_to_int(row.get("预计用例数", 1), default=1),
                included=bool(row.get("是否参与生成", False)),
            )
        )
    return items


def design_plan_summary_rows(plan: ApiDesignPlan) -> list[dict[str, str | int]]:
    included_items = [item for item in plan.plan_items if item.included]
    return [
        {"项目": "生成策略", "内容": plan.strategy},
        {"项目": "覆盖项", "内容": "、".join(plan.coverage_types)},
        {"项目": "计划生成的用例类型", "内容": "、".join(plan.planned_case_types) or "-"},
        {"项目": "预计生成用例数量", "内容": plan.estimated_case_count},
        {"项目": "计划生成项", "内容": len(included_items)},
        {"项目": "识别到的参数风险", "内容": len(plan.param_risks)},
        {"项目": "识别到的业务规则", "内容": len([rule for rule in plan.business_rule_risks if rule.included])},
        {"项目": "识别到的数据库校验", "内容": len(plan.db_checks)},
    ]


def _fixed_item(
    plan_id: str,
    coverage_type: str,
    source_name: str,
    risk_type: str,
    suggested_test_point: str,
    source_type: str = "fixed",
) -> ApiPlanItem:
    return ApiPlanItem(
        plan_id=plan_id,
        coverage_type=coverage_type,
        source_type=source_type,
        source_name=source_name,
        risk_type=risk_type,
        suggested_test_point=suggested_test_point,
        estimated_count=1,
        included=True,
    )


def _param_to_risk(param: ApiParam) -> ApiParamRisk:
    risks = []
    test_points = []
    if param.required:
        risks.append("必填缺失")
        test_points.append(f"{param.name} 为空或缺失")
    if param.param_type:
        risks.append("类型错误")
        test_points.append(f"{param.name} 传入非 {param.param_type} 类型")
    if _has_enum_rule(param):
        risks.append("非法枚举")
        test_points.append(f"{param.name} 传入枚举外取值")
    if _has_boundary_rule(param):
        risks.append("边界非法值")
        test_points.append(f"{param.name} 使用超范围、超长或过短值")
    if _has_format_rule(param):
        risks.append("格式错误")
        test_points.append(f"{param.name} 使用错误格式")
    if _has_owner_rule(param):
        risks.append("资源归属")
        test_points.append(f"{param.name} 使用非当前用户资源")
    if _has_existence_rule(param):
        risks.append("存在性")
        test_points.append(f"{param.name} 使用不存在的数据")

    if not risks:
        risks.append("基础参数")
        test_points.append(f"{param.name} 使用合法值验证主流程")

    return ApiParamRisk(
        param_name=param.name,
        source=param.source,
        required=param.required,
        param_type=param.param_type,
        rule=param.rule,
        risk_type="、".join(_unique(risks)),
        suggested_test_point="；".join(_unique(test_points)),
    )


def _planned_case_types(plan_items: list[ApiPlanItem]) -> list[str]:
    return _unique([item.coverage_type for item in plan_items if item.included])


def _param_plan_points(risks: list[ApiParamRisk]) -> list[tuple[ApiParamRisk, str, str]]:
    points = []
    for risk in risks:
        risk_types = risk.risk_type.split("、")
        test_points = risk.suggested_test_point.split("；")
        for index, risk_type in enumerate(risk_types):
            test_point = test_points[index] if index < len(test_points) else risk.suggested_test_point
            points.append((risk, risk_type, test_point))
    return points


def _select_param_plan_points(
    points: list[tuple[ApiParamRisk, str, str]],
    strategy: str,
) -> list[tuple[ApiParamRisk, str, str]]:
    if strategy == "完整":
        return points
    high_risks = [
        point
        for point in points
        if any(keyword in point[1] for keyword in ["必填", "类型", "边界", "枚举", "格式", "归属", "存在"])
    ]
    ordered = high_risks + [point for point in points if point not in high_risks]
    if strategy == "精简":
        return ordered[:2]
    return ordered[:6]


def _select_business_risks(risks: list[ApiBusinessRuleRisk], strategy: str) -> list[ApiBusinessRuleRisk]:
    if strategy == "精简":
        return risks[:1]
    if strategy == "完整":
        return risks
    return risks[:2]


def _business_rule_risk_type(rule: str) -> str:
    if any(keyword in rule for keyword in ["权限", "角色", "用户", "归属", "本人", "当前用户"]):
        return "权限/归属"
    if any(keyword in rule for keyword in ["状态", "已取消", "已完成", "在线", "离线", "启用", "禁用"]):
        return "状态流转"
    if any(keyword in rule for keyword in ["库存", "余额", "额度", "次数", "数量"]):
        return "数据边界"
    if any(keyword in rule for keyword in ["重复", "再次", "幂等"]):
        return "幂等重复"
    return "业务约束"


def _business_rule_test_point(rule: str, risk_type: str) -> str:
    suggestions = {
        "权限/归属": "使用无权限账号或非当前用户资源触发拦截。",
        "状态流转": "准备不满足状态的数据，验证接口拒绝并返回明确原因。",
        "数据边界": "构造超出数量、库存、余额或额度限制的数据。",
        "幂等重复": "连续提交同一请求，确认不会重复产生业务数据。",
        "业务约束": "构造不满足该规则的数据，检查错误提示和数据不变。",
    }
    return f"{suggestions.get(risk_type, '构造不满足规则的数据。')}规则：{rule}"


def _has_enum_rule(param: ApiParam) -> bool:
    text = f"{param.rule} {param.name}"
    return any(keyword in text for keyword in ["枚举", "允许值", "取值"])


def _has_boundary_rule(param: ApiParam) -> bool:
    text = f"{param.rule} {param.name}"
    return any(keyword in text for keyword in ["长度", "范围", "大于", "小于", "不大于", "不小于", "最大", "最小"])


def _has_format_rule(param: ApiParam) -> bool:
    text = f"{param.rule} {param.name}"
    return any(keyword in text for keyword in ["格式", "手机号", "电话", "日期", "yyyy", "date", "datetime"])


def _has_owner_rule(param: ApiParam) -> bool:
    text = f"{param.rule} {param.name}"
    return any(keyword in text for keyword in ["当前用户", "归属", "本人", "自己", "所属"])


def _has_existence_rule(param: ApiParam) -> bool:
    text = f"{param.rule} {param.name}"
    return any(keyword in text for keyword in ["必须存在", "存在", "有效ID", "有效 id", "ID", "id"])


def _clean_item(line: str) -> str:
    value = line.strip()
    for prefix in ["-", "*", "•"]:
        if value.startswith(prefix):
            value = value[1:].strip()
    value = value.lstrip("0123456789.、) ").strip()
    return value


def _included_set(items: list[str] | None) -> set[str]:
    return {item.strip() for item in items or [] if item.strip()}


def _to_int(value, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _unique(items: list[str]) -> list[str]:
    result = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result
