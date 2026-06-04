from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.models import COLUMN_TO_FIELD, EXCEL_COLUMNS, TestCase


def build_excel(cases: list[TestCase]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "测试用例"

    sheet.append(EXCEL_COLUMNS)

    for case in cases:
        sheet.append([getattr(case, COLUMN_TO_FIELD[column]) for column in EXCEL_COLUMNS])

    _style_sheet(sheet)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _style_sheet(sheet) -> None:
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    wrap_alignment = Alignment(wrap_text=True, vertical="top")

    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    width_by_column = {
        "用例编号": 14,
        "模块": 16,
        "功能点": 20,
        "用例标题": 30,
        "优先级": 10,
        "前置条件": 36,
        "测试数据": 28,
        "操作步骤": 42,
        "预期结果": 42,
        "用例类型": 14,
        "备注": 28,
    }
    for index, column in enumerate(EXCEL_COLUMNS, start=1):
        width = width_by_column.get(column, 18)
        sheet.column_dimensions[get_column_letter(index)].width = width

    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap_alignment

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
