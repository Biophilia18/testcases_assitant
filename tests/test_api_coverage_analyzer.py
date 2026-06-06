from src.api.coverage_analyzer import API_COVERAGE_ITEMS, api_coverage_matrix_to_rows, build_api_coverage_matrix
from src.api.models import ApiDocument, ApiTestCase
from src.api.rule_generator import generate_api_cases


def _api_case(case_id: str, case_type: str, expected_status: str = "200", remark: str = "") -> ApiTestCase:
    return ApiTestCase(
        case_id=case_id,
        module="设备控制",
        api_name="设备控制接口",
        method="POST",
        path="/api/devices/{deviceId}/control",
        headers="Authorization: Bearer token",
        query_params="deviceId=10001",
        request_body='{"action":"open"}',
        precondition="准备有效 Token",
        steps=f"1. 构造{case_type}请求\n2. 发送请求\n3. 查看响应",
        expected_status=expected_status,
        assertions=f"{case_type}结果符合接口文档，响应字段断言明确。",
        db_check="",
        extract_vars="",
        priority="P1",
        case_type=case_type,
        remark=remark or case_type,
    )


def test_build_api_coverage_matrix_marks_generated_cases() -> None:
    document = ApiDocument(
        auth="Bearer Token",
        params="deviceId：设备ID，必填",
        body='{"action":"open"}',
        response_example='{"code":0}',
        business_rules="设备在线才允许控制",
        db_checks="设备状态记录更新",
    )
    cases = generate_api_cases(document)

    matrix = build_api_coverage_matrix(cases)

    assert [item.name for item in matrix] == API_COVERAGE_ITEMS
    assert all(item.covered for item in matrix)
    assert all(item.matched_case_ids for item in matrix)


def test_build_api_coverage_matrix_reports_missing_items() -> None:
    cases = [_api_case("API-01-01", "正常请求", "200")]

    matrix = build_api_coverage_matrix(cases)
    rows = api_coverage_matrix_to_rows(matrix)

    assert rows[0]["覆盖项"] == "正常请求"
    assert rows[0]["是否覆盖"] == "是"
    assert rows[0]["命中用例"] == "API-01-01"
    assert any(row["覆盖项"] == "数据库校验" and row["是否覆盖"] == "否" for row in rows)
    assert any(row["覆盖项"] == "参数校验" and "必填" in row["建议说明"] for row in rows)
