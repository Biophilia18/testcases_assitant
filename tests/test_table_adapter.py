from io import BytesIO

from openpyxl import load_workbook

from src.exporter import build_excel
from src.models import TestCase
from src.table_adapter import cases_to_rows, find_case_warnings, rows_to_cases


def test_cases_to_rows_and_rows_to_cases_round_trip():
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

    rows = cases_to_rows([case])
    rows[0]["预期结果"] = "展示编辑后的订单详情"
    rows[0]["操作步骤"] = "1. 输入订单号 2. 查询"
    edited_cases = rows_to_cases(rows)

    assert edited_cases[0].case_id == "TC-01-01"
    assert edited_cases[0].expected_result == "展示编辑后的订单详情"
    assert edited_cases[0].steps == "1. 输入订单号\n2. 查询"


def test_rows_to_cases_ignores_blank_rows_and_fills_defaults():
    rows = [
        {"用例标题": "", "操作步骤": "", "预期结果": ""},
        {"用例标题": "标题", "操作步骤": "步骤", "预期结果": "结果"},
    ]

    cases = rows_to_cases(rows)

    assert len(cases) == 1
    assert cases[0].case_id == "TC-EDIT-002"
    assert cases[0].priority == "P2"


def test_find_case_warnings_reports_duplicate_and_missing_required_fields():
    rows = [
        {"用例编号": "TC-001", "用例标题": "标题", "操作步骤": "", "预期结果": "结果"},
        {"用例编号": "TC-001", "用例标题": "标题2", "操作步骤": "步骤", "预期结果": "结果"},
    ]

    warnings = find_case_warnings(rows_to_cases(rows))

    assert any("缺少操作步骤" in warning for warning in warnings)
    assert any("用例编号重复" in warning for warning in warnings)


def test_edited_cases_are_used_for_excel_export():
    rows = [
        {
            "用例编号": "TC-01-01",
            "模块": "订单",
            "功能点": "查询订单",
            "用例标题": "查询订单-正常流程",
            "前置条件": "用户已登录",
            "测试数据": "订单号：A001",
            "操作步骤": "1. 查询",
            "预期结果": "编辑后的预期结果",
            "优先级": "P1",
            "用例类型": "功能测试",
            "备注": "编辑后导出",
        }
    ]

    excel_bytes = build_excel(rows_to_cases(rows))
    workbook = load_workbook(BytesIO(excel_bytes))
    sheet = workbook["测试用例"]

    assert sheet["H2"].value == "编辑后的预期结果"
    assert sheet["K2"].value == "编辑后导出"

