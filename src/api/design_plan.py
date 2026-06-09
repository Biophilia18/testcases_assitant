from __future__ import annotations

from dataclasses import dataclass

from src.api.coverage_analyzer import API_COVERAGE_ITEMS
from src.api.models import ApiDocument
from src.api.param_parser import ApiParam, parse_api_params


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
class ApiDesignPlan:
    param_risks: list[ApiParamRisk]
    business_rule_risks: list[ApiBusinessRuleRisk]
    db_checks: list[str]
    planned_case_types: list[str]
    estimated_case_count: int
    coverage_types: list[str]
    strategy: str


def build_api_design_plan(
    document: ApiDocument,
    coverage_types: list[str] | None = None,
    strategy: str = "标准",
    included_business_rules: list[str] | None = None,
) -> ApiDesignPlan:
    selected_coverage = normalize_api_coverage_types(coverage_types)
    normalized_strategy = normalize_api_strategy(strategy)
    param_risks = analyze_param_risks(document)
    business_rule_risks = analyze_business_rule_risks(document, included_business_rules)
    db_checks = split_api_text_items(document.db_checks)
    planned_case_types = _planned_case_types(document, param_risks, business_rule_risks, db_checks, selected_coverage)
    estimated_case_count = estimate_api_case_count(document, selected_coverage, normalized_strategy, included_business_rules)
    return ApiDesignPlan(
        param_risks=param_risks,
        business_rule_risks=business_rule_risks,
        db_checks=db_checks,
        planned_case_types=planned_case_types,
        estimated_case_count=estimated_case_count,
        coverage_types=selected_coverage,
        strategy=normalized_strategy,
    )


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
) -> int:
    selected_coverage = normalize_api_coverage_types(coverage_types)
    normalized_strategy = normalize_api_strategy(strategy)
    params = parse_api_params(document)
    business_rules = [
        rule for rule in analyze_business_rule_risks(document, included_business_rules) if rule.included
    ]
    count = 0

    if "正常请求" in selected_coverage:
        count += 1
    if "参数校验" in selected_coverage:
        count += _estimate_param_case_count(params, normalized_strategy)
    if "鉴权校验" in selected_coverage:
        count += 1
    if "权限校验" in selected_coverage and document.auth.strip():
        count += 1
    if "业务规则" in selected_coverage and business_rules:
        count += len(business_rules) if normalized_strategy == "完整" else 1
    if "幂等校验" in selected_coverage:
        count += 1
    if "响应断言" in selected_coverage and document.response_example.strip():
        count += 1
    if "数据库校验" in selected_coverage and document.db_checks.strip():
        count += 1
    return count


def normalize_api_coverage_types(coverage_types: list[str] | None) -> list[str]:
    if coverage_types is None:
        return list(API_COVERAGE_ITEMS)
    selected = [item for item in API_COVERAGE_ITEMS if item in set(coverage_types)]
    return selected


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


def param_risks_to_rows(risks: list[ApiParamRisk]) -> list[dict[str, str]]:
    return [
        {
            "参数名": risk.param_name,
            "参数来源": risk.source,
            "是否必填": "是" if risk.required else "否",
            "参数类型": risk.param_type or "-",
            "识别到的规则": risk.rule or "-",
            "风险类型": risk.risk_type,
            "建议测试点": risk.suggested_test_point,
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


def design_plan_summary_rows(plan: ApiDesignPlan) -> list[dict[str, str | int]]:
    return [
        {"项目": "生成策略", "内容": plan.strategy},
        {"项目": "覆盖项", "内容": "、".join(plan.coverage_types)},
        {"项目": "计划生成的用例类型", "内容": "、".join(plan.planned_case_types) or "-"},
        {"项目": "预计生成用例数量", "内容": plan.estimated_case_count},
        {"项目": "识别到的参数风险", "内容": len(plan.param_risks)},
        {"项目": "识别到的业务规则", "内容": len([rule for rule in plan.business_rule_risks if rule.included])},
        {"项目": "识别到的数据库校验", "内容": len(plan.db_checks)},
    ]


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


def _planned_case_types(
    document: ApiDocument,
    param_risks: list[ApiParamRisk],
    business_rule_risks: list[ApiBusinessRuleRisk],
    db_checks: list[str],
    coverage_types: list[str],
) -> list[str]:
    planned = []
    for coverage in coverage_types:
        if coverage == "参数校验" and not param_risks:
            continue
        if coverage == "权限校验" and not document.auth.strip():
            continue
        if coverage == "业务规则" and not [rule for rule in business_rule_risks if rule.included]:
            continue
        if coverage == "响应断言" and not document.response_example.strip():
            continue
        if coverage == "数据库校验" and not db_checks:
            continue
        planned.append(coverage)
    return planned


def _estimate_param_case_count(params: list[ApiParam], strategy: str) -> int:
    if not params:
        return 1
    per_param_counts = [_param_case_point_count(param) for param in params]
    if strategy == "精简":
        return min(2, max(per_param_counts))
    if strategy == "完整":
        return sum(per_param_counts)
    return min(6, sum(min(2, count) for count in per_param_counts))


def _param_case_point_count(param: ApiParam) -> int:
    count = 0
    if param.required:
        count += 1
    if param.param_type:
        count += 1
    if _has_enum_rule(param):
        count += 1
    if _has_format_rule(param):
        count += 1
    if _has_boundary_rule(param):
        count += 1
    if _has_owner_rule(param):
        count += 1
    if _has_existence_rule(param):
        count += 1
    return count or 1


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


def _unique(items: list[str]) -> list[str]:
    result = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result
