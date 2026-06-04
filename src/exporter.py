from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.models import EXCEL_COLUMNS, TestCase


def build_excel(cases: list[TestCase]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "测试用例"

    sheet.append(EXCEL_COLUMNS)

    for case in cases:
        sheet.append(
            [
                case.case_id,
                case.module,
                case.feature,
                case.title,
                case.precondition,
                case.test_data,
                case.steps,
                case.expected_result,
                case.priority,
                case.case_type,
                case.remark,
            ]
        )

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

    widths = [14, 16, 20, 30, 36, 28, 42, 42, 10, 14, 28]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap_alignment

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
