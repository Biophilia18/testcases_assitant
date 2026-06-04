from __future__ import annotations

from typing import Any

from src.models import COLUMN_TO_FIELD, EXCEL_COLUMNS, TestCase
from src.quality_checker import issue_messages
from src.text_utils import normalize_steps


def cases_to_rows(cases: list[TestCase]) -> list[dict[str, str]]:
    rows = []
    for case in cases:
        rows.append({column: getattr(case, COLUMN_TO_FIELD[column]) for column in EXCEL_COLUMNS})
    return rows


def rows_to_cases(rows: Any) -> list[TestCase]:
    normalized_rows = _normalize_rows(rows)
    cases: list[TestCase] = []

    for index, row in enumerate(normalized_rows, start=1):
        title = _cell(row, "用例标题")
        steps = normalize_steps(_cell(row, "操作步骤"))
        expected_result = _cell(row, "预期结果")

        if not title and not steps and not expected_result:
            continue

        cases.append(
            TestCase(
                case_id=_cell(row, "用例编号") or f"TC-EDIT-{index:03d}",
                module=_cell(row, "模块"),
                feature=_cell(row, "功能点"),
                title=title,
                precondition=_cell(row, "前置条件"),
                test_data=_cell(row, "测试数据"),
                steps=steps,
                expected_result=expected_result,
                priority=_cell(row, "优先级") or "P2",
                case_type=_cell(row, "用例类型") or "功能测试",
                remark=_cell(row, "备注"),
            )
        )

    return cases


def find_case_warnings(cases: list[TestCase]) -> list[str]:
    return issue_messages(cases)


def _normalize_rows(rows: Any) -> list[dict[str, Any]]:
    if hasattr(rows, "to_dict"):
        return rows.to_dict(orient="records")
    return list(rows)


def _cell(row: dict[str, Any], column: str) -> str:
    value = row.get(column, "")
    if value is None:
        return ""
    return str(value).strip()
