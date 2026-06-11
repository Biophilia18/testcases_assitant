from src.api.case_stabilizer import count_duplicate_api_cases, stabilize_api_cases
from src.api.models import ApiTestCase


def _case(case_id: str, case_type: str, remark: str) -> ApiTestCase:
    return ApiTestCase(
        case_id=case_id,
        case_title=f"{case_type}-{case_id}",
        module="模块",
        api_name="接口",
        method="POST",
        path="/api/demo",
        headers="",
        query_params="",
        request_body="{}",
        precondition="准备测试数据",
        steps="1. 发送请求\n2. 检查响应",
        expected_status="400",
        assertions="返回明确错误",
        db_check="",
        extract_vars="",
        priority="P1",
        case_type=case_type,
        remark=remark,
    )


def test_stabilize_api_cases_removes_duplicate_risk_cases_and_renumbers() -> None:
    cases = [
        _case("API-01-01", "参数校验", "必填参数为空：name\n计划ID：PLAN-PARAM-001；风险来源：param/name；风险类型：必填缺失"),
        _case("API-01-02", "参数校验", "必填参数为空：name\n计划ID：PLAN-PARAM-999；风险来源：param/name；风险类型：必填缺失"),
        _case("API-01-03", "参数校验", "参数类型错误：name\n计划ID：PLAN-PARAM-002；风险来源：param/name；风险类型：类型错误"),
    ]

    stabilized = stabilize_api_cases(cases)

    assert count_duplicate_api_cases(cases) == 1
    assert [case.case_id for case in stabilized] == ["API-01-01", "API-01-02"]
    assert [case.remark for case in stabilized] == [cases[0].remark, cases[2].remark]


def test_stabilize_api_cases_applies_strategy_case_limit() -> None:
    cases = [
        _case(f"API-01-{index:02d}", "数据库校验", f"数据库校验 {index}\n计划ID：PLAN-DB-{index:03d}；风险来源：db_check/{index}；风险类型：数据一致性")
        for index in range(1, 15)
    ]

    stabilized = stabilize_api_cases(cases, strategy="精简")

    assert len(stabilized) == 10
    assert stabilized[-1].case_id == "API-01-10"
