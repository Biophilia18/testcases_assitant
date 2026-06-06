from src.api.models import ApiTestCase
from src.api.table_adapter import api_cases_to_rows, find_api_case_warnings, rows_to_api_cases


def _api_case() -> ApiTestCase:
    return ApiTestCase(
        case_id="API-01-01",
        module="设备控制",
        api_name="设备控制接口",
        method="POST",
        path="/api/devices/{deviceId}/control",
        headers="Authorization: Bearer token",
        query_params="deviceId=10001",
        request_body='{"action": "open"}',
        precondition="已获取有效 token",
        steps="1. 构造请求\n2. 发送请求",
        expected_status="200",
        assertions="接口返回成功",
        db_check="设备状态记录更新",
        extract_vars="deviceId",
        priority="P1",
        case_type="接口测试",
        remark="示例",
    )


def test_api_cases_to_rows_contains_api_columns():
    rows = api_cases_to_rows([_api_case()])

    assert rows[0]["用例编号"] == "API-01-01"
    assert rows[0]["接口名称"] == "设备控制接口"
    assert rows[0]["请求方法"] == "POST"
    assert rows[0]["接口路径"] == "/api/devices/{deviceId}/control"
    assert rows[0]["请求头"] == "Authorization: Bearer token"
    assert rows[0]["断言点"] == "接口返回成功"
    assert rows[0]["数据库校验"] == "设备状态记录更新"
    assert rows[0]["变量提取"] == "deviceId"


def test_rows_to_api_cases_converts_rows_and_defaults_fields():
    rows = [
        {
            "接口名称": "设备查询接口",
            "接口路径": "/api/devices/10001",
            "断言点": "返回设备详情",
            "请求头": "Authorization: Bearer token",
            "数据库校验": "设备记录存在",
            "变量提取": "deviceId",
            "操作步骤": "1. 发送请求 2. 查看响应",
        }
    ]

    cases = rows_to_api_cases(rows)

    assert cases[0].case_id == "API-EDIT-001"
    assert cases[0].method == "GET"
    assert cases[0].expected_status == "200"
    assert cases[0].steps == "1. 发送请求\n2. 查看响应"
    assert cases[0].headers == "Authorization: Bearer token"
    assert cases[0].assertions == "返回设备详情"
    assert cases[0].db_check == "设备记录存在"
    assert cases[0].extract_vars == "deviceId"


def test_find_api_case_warnings_reports_missing_required_fields():
    case = _api_case()
    case.api_name = ""
    case.path = ""

    warnings = find_api_case_warnings([case])

    assert any("缺少接口名称" in warning for warning in warnings)
    assert any("缺少接口路径" in warning for warning in warnings)
