from src.api.design_plan import (
    analyze_business_rule_risks,
    analyze_param_risks,
    build_api_design_plan,
    build_api_plan_items,
)
from src.api.models import ApiDocument
from src.api.rule_generator import build_api_plan_trace_rows, generate_api_cases


def _document() -> ApiDocument:
    return ApiDocument(
        module="设备控制",
        api_name="设备控制接口",
        method="POST",
        path="/api/devices/{deviceId}/control",
        auth="Bearer Token",
        params="\n".join(
            [
                "deviceId：设备ID，必填，integer，范围大于0，必须属于当前用户",
                "action：控制动作，必填，string，枚举 open、close",
            ]
        ),
        response_example='{"code":0,"data":{"id":1}}',
        business_rules="设备在线才允许控制\n用户只能控制自己的设备",
        db_checks="设备状态记录更新",
    )


def test_analyze_param_risks_reports_required_type_boundary_and_owner() -> None:
    risks = analyze_param_risks(_document())
    by_name = {risk.param_name: risk for risk in risks}

    assert "必填缺失" in by_name["deviceId"].risk_type
    assert "类型错误" in by_name["deviceId"].risk_type
    assert "边界非法值" in by_name["deviceId"].risk_type
    assert "资源归属" in by_name["deviceId"].risk_type
    assert "非法枚举" in by_name["action"].risk_type


def test_analyze_business_rule_risks_supports_included_rules() -> None:
    risks = analyze_business_rule_risks(_document(), included_rules=["设备在线才允许控制"])

    by_content = {risk.content: risk for risk in risks}
    assert by_content["设备在线才允许控制"].included is True
    assert by_content["用户只能控制自己的设备"].included is False
    assert by_content["设备在线才允许控制"].risk_type == "状态流转"


def test_build_api_design_plan_respects_coverage_selection_and_strategy() -> None:
    plan = build_api_design_plan(
        _document(),
        coverage_types=["正常请求", "参数校验", "业务规则"],
        strategy="精简",
        included_business_rules=["设备在线才允许控制"],
    )

    assert plan.strategy == "精简"
    assert plan.coverage_types == ["正常请求", "参数校验", "业务规则"]
    assert plan.planned_case_types == ["正常请求", "参数校验", "业务规则"]
    assert plan.estimated_case_count == 4


def test_build_api_design_plan_allows_empty_coverage_selection() -> None:
    plan = build_api_design_plan(_document(), coverage_types=[], strategy="标准")

    assert plan.coverage_types == []
    assert plan.planned_case_types == []
    assert plan.estimated_case_count == 0


def test_build_api_plan_items_creates_param_plan_items() -> None:
    items = build_api_plan_items(_document(), coverage_types=["参数校验"], strategy="完整")

    assert any(item.source_type == "param" and item.source_name == "deviceId" for item in items)
    assert any(item.risk_type == "必填缺失" for item in items)
    assert any(item.risk_type == "非法枚举" and item.source_name == "action" for item in items)


def test_strategy_changes_plan_item_count() -> None:
    compact_items = build_api_plan_items(_document(), coverage_types=["参数校验"], strategy="精简")
    standard_items = build_api_plan_items(_document(), coverage_types=["参数校验"], strategy="标准")
    full_items = build_api_plan_items(_document(), coverage_types=["参数校验"], strategy="完整")

    assert len(compact_items) < len(standard_items) <= len(full_items)


def test_strategy_limit_marks_extra_plan_items_as_not_included() -> None:
    document = ApiDocument(
        api_name="批量校验接口",
        method="POST",
        path="/api/batch",
        params="\n".join([f"field{index}：字段{index}，必填，string，长度1-30" for index in range(1, 10)]),
        auth="Bearer Token",
        response_example='{"code":0}',
        business_rules="\n".join([f"业务规则{index}" for index in range(1, 5)]),
        db_checks="\n".join([f"数据库校验{index}" for index in range(1, 5)]),
    )

    plan = build_api_design_plan(document, strategy="精简")

    assert plan.estimated_case_count <= 10
    assert any(not item.included and item.estimated_count == 0 for item in plan.plan_items)


def test_estimated_count_matches_actual_generated_count() -> None:
    plan = build_api_design_plan(_document(), strategy="标准")
    cases = generate_api_cases(_document(), plan_items=plan.plan_items)

    assert plan.estimated_case_count == len(cases)


def test_excluded_business_rule_does_not_generate_case() -> None:
    plan_items = build_api_plan_items(
        _document(),
        coverage_types=["业务规则"],
        strategy="完整",
        included_business_rules=["设备在线才允许控制"],
    )
    cases = generate_api_cases(_document(), plan_items=plan_items)

    assert any("设备在线才允许控制" in case.remark for case in cases)
    assert not any("用户只能控制自己的设备" in case.remark for case in cases)


def test_generated_cases_can_be_traced_by_plan_id() -> None:
    plan = build_api_design_plan(_document(), coverage_types=["正常请求", "参数校验"], strategy="精简")
    cases = generate_api_cases(_document(), plan_items=plan.plan_items)
    trace_rows = build_api_plan_trace_rows(plan.plan_items, cases)

    included_rows = [row for row in trace_rows if row["是否参与"] == "是"]
    assert included_rows
    assert all(row["是否生成"] == "是" for row in included_rows)
    assert all(row["对应用例编号"] != "-" for row in included_rows)
