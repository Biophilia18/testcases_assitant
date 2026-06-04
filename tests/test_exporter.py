from io import BytesIO

from openpyxl import load_workbook

from src.exporter import build_excel
from src.models import EXCEL_COLUMNS, TestCase


def test_build_excel_contains_new_columns_and_data():
    case = TestCase(
        case_id="TC-01-01",
        module="订单",
        feature="查询订单",
        title="查询订单-正常流程",
        precondition="用户已登录",
        test_data="订单号：A001",
        steps="1. 输入订单号\n2. 查询",
        expected_result="展示订单详情",
        priority="P1",
        case_type="功能测试",
        remark="示例",
    )

    data = build_excel([case])
    workbook = load_workbook(BytesIO(data))
    sheet = workbook["测试用例"]

    headers = [cell.value for cell in sheet[1]]
    row = [cell.value for cell in sheet[2]]

    assert headers == EXCEL_COLUMNS
    assert row[0] == "TC-01-01"
    assert row[5] == "订单号：A001"
    assert row[10] == "示例"
    assert row[2] == "查询订单-正常流程"
    assert row[9] == "查询订单"
