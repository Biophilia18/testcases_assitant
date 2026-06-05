from src.models import GenerationResult, TestCase
from src.persistence import generation_result_to_payload, payload_to_generation_result


def _case() -> TestCase:
    return TestCase(
        case_id="TC-01-01",
        module="订单",
        feature="查询订单",
        title="查询订单-正常流程",
        precondition="用户已登录",
        test_data="订单号：A001",
        steps="1. 输入订单号\n2. 点击查询",
        expected_result="展示订单详情",
        priority="P1",
        case_type="功能测试",
        remark="示例",
    )


def test_generation_result_payload_round_trip():
    result = GenerationResult(
        cases=[_case()],
        requested_mode="规则生成",
        actual_mode="规则生成",
        feature_count=1,
        case_count=1,
        provider="规则生成",
        message="完成",
    )

    payload = generation_result_to_payload(result, "订单系统_测试用例.xlsx")
    loaded, filename = payload_to_generation_result(payload)

    assert filename == "订单系统_测试用例.xlsx"
    assert loaded.cases[0].case_id == "TC-01-01"
    assert loaded.case_count == 1

