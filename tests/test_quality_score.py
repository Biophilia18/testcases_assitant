from src.models import TestCase
from src.quality_score import calculate_quality_score


def _case(**overrides) -> TestCase:
    data = {
        "case_id": "TC-01-01",
        "module": "订单",
        "feature": "查询订单",
        "title": "查询订单-正常流程",
        "precondition": "用户已登录",
        "test_data": "订单号：A001",
        "steps": "1. 输入订单号\n2. 点击查询",
        "expected_result": "展示订单详情和订单状态",
        "priority": "P1",
        "case_type": "功能测试",
        "remark": "覆盖类型：正常流程",
    }
    data.update(overrides)
    return TestCase(**data)


def test_calculate_quality_score_handles_empty_cases():
    score = calculate_quality_score([])

    assert score.score == 0
    assert "暂无用例" in score.summary


def test_calculate_quality_score_adds_coverage_points():
    cases = [
        _case(remark="覆盖类型：正常流程"),
        _case(case_id="TC-01-02", title="查询订单-异常输入", remark="覆盖类型：异常场景"),
        _case(case_id="TC-01-03", title="查询订单-边界值", remark="覆盖类型：边界/非法输入"),
        _case(case_id="TC-01-04", title="查询订单-权限控制", remark="覆盖类型：权限控制"),
    ]

    score = calculate_quality_score(cases, ["正常流程", "异常场景", "边界/非法输入", "权限控制"])

    assert score.score == 90
    assert len(score.additions) == 4
    assert not score.deductions


def test_calculate_quality_score_applies_content_deductions():
    cases = [
        _case(steps="1. 点击查询", expected_result="成功", test_data=""),
    ]

    score = calculate_quality_score(cases, ["正常流程"])

    assert score.score == 63
    assert any("操作步骤过短" in item.label for item in score.deductions)
    assert any("预期结果过泛" in item.label for item in score.deductions)
    assert any("测试数据为空" in item.label for item in score.deductions)
