from src.models import GenerationResult, TestCase
from src import persistence
from src.persistence import generation_result_to_payload, list_history_files, payload_to_generation_result


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
        coverage_types=["正常流程", "异常场景"],
        provider="规则生成",
        message="完成",
    )

    payload = generation_result_to_payload(result, "订单系统_测试用例.xlsx")
    loaded, filename = payload_to_generation_result(payload)

    assert filename == "订单系统_测试用例.xlsx"
    assert loaded.cases[0].case_id == "TC-01-01"
    assert loaded.case_count == 1
    assert loaded.coverage_types == ["正常流程", "异常场景"]


def test_list_history_files_returns_newest_first(tmp_path, monkeypatch):
    older = tmp_path / "cases_20260101_100000.json"
    newer = tmp_path / "cases_20260102_100000.json"
    other = tmp_path / "latest_cases.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")
    other.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(persistence, "OUTPUT_DIR", tmp_path)

    files = list_history_files()

    assert files == [newer, older]
