from src.models import TestCase
from src.quality_checker import check_cases, issue_messages


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
        "remark": "示例",
    }
    data.update(overrides)
    return TestCase(**data)


def test_check_cases_reports_duplicate_ids_and_missing_fields():
    cases = [
        _case(case_id="TC-01-01", steps=""),
        _case(case_id="TC-01-01", title="查询订单-异常流程"),
    ]

    messages = issue_messages(cases)

    assert any("用例编号重复" in message for message in messages)
    assert any("缺少操作步骤" in message for message in messages)


def test_check_cases_reports_missing_coverage():
    issues = check_cases([_case(case_type="功能测试")], ["异常场景", "边界/非法输入", "权限控制"])

    assert any("缺少异常场景用例" in issue.message for issue in issues)
    assert any("缺少边界/非法输入用例" in issue.message for issue in issues)
    assert any("缺少权限控制用例" in issue.message for issue in issues)


def test_check_cases_reports_vague_expected_result():
    issues = check_cases([_case(expected_result="成功")])

    assert any("预期结果偏笼统" in issue.message for issue in issues)


def test_check_cases_passes_when_selected_coverage_exists():
    cases = [
        _case(remark="覆盖类型：正常流程"),
        _case(case_id="TC-01-02", title="查询订单-弱网校验", remark="覆盖类型：弱网/超时"),
    ]

    issues = check_cases(cases, ["正常流程", "弱网/超时"])

    assert not any("缺少正常流程用例" in issue.message for issue in issues)
    assert not any("缺少弱网/超时用例" in issue.message for issue in issues)
