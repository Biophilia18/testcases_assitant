from src.api.design_plan import analyze_business_rule_risks, analyze_param_risks, build_api_design_plan
from src.api.models import ApiDocument


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
