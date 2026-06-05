from io import BytesIO

from openpyxl import load_workbook

from src.api_exporter import build_api_excel
from src.api_models import API_EXCEL_COLUMNS, ApiTestCase


def test_build_api_excel_contains_api_sheet_and_data():
    case = ApiTestCase(
        case_id="API-01-01",
        module="设备控制",
        api_name="设备控制接口",
        method="POST",
        path="/api/devices/{deviceId}/control",
        query_params="deviceId=10001",
        request_body='{"action": "open"}',
        precondition="已获取有效 token",
        steps="1. 构造请求\n2. 发送请求",
        expected_status="200",
        expected_result="接口返回成功",
        priority="P1",
        case_type="接口测试",
        remark="示例",
    )

    data = build_api_excel([case])
    workbook = load_workbook(BytesIO(data))
    sheet = workbook["接口测试用例"]

    headers = [cell.value for cell in sheet[1]]
    row = [cell.value for cell in sheet[2]]

    assert headers == API_EXCEL_COLUMNS
    assert row[0] == "API-01-01"
    assert row[2] == "设备控制接口"
    assert row[3] == "POST"
    assert row[9] == "200"
