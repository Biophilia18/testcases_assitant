from __future__ import annotations

from typing import Any

from src.api.models import API_COLUMN_TO_FIELD, API_EXCEL_COLUMNS, ApiTestCase
from src.text_utils import normalize_steps


def api_cases_to_rows(cases: list[ApiTestCase]) -> list[dict[str, str]]:
    rows = []
    for case in cases:
        rows.append({column: getattr(case, API_COLUMN_TO_FIELD[column]) for column in API_EXCEL_COLUMNS})
    return rows


def rows_to_api_cases(rows: Any) -> list[ApiTestCase]:
    normalized_rows = _normalize_rows(rows)
    cases: list[ApiTestCase] = []

    for index, row in enumerate(normalized_rows, start=1):
        api_name = _cell(row, "接口名称")
        path = _cell(row, "接口路径")
        assertions = _cell(row, "断言点")

        if not api_name and not path and not assertions:
            continue

        cases.append(
            ApiTestCase(
                case_id=_cell(row, "用例编号") or f"API-EDIT-{index:03d}",
                module=_cell(row, "模块"),
                api_name=api_name,
                method=_cell(row, "请求方法") or "GET",
                path=path,
                headers=_cell(row, "请求头"),
                query_params=_cell(row, "请求参数"),
                request_body=_cell(row, "请求体"),
                precondition=_cell(row, "前置条件"),
                steps=normalize_steps(_cell(row, "操作步骤")),
                expected_status=_cell(row, "预期状态码") or "200",
                assertions=assertions,
                db_check=_cell(row, "数据库校验"),
                extract_vars=_cell(row, "变量提取"),
                priority=_cell(row, "优先级") or "P2",
                case_type=_cell(row, "用例类型") or "接口测试",
                remark=_cell(row, "备注"),
            )
        )

    return cases


def find_api_case_warnings(cases: list[ApiTestCase]) -> list[str]:
    warnings: list[str] = []
    seen_ids: set[str] = set()

    for case in cases:
        if case.case_id in seen_ids:
            warnings.append(f"{case.case_id}：用例编号重复。")
        seen_ids.add(case.case_id)

        if not case.api_name:
            warnings.append(f"{case.case_id}：缺少接口名称。")
        if not case.method:
            warnings.append(f"{case.case_id}：缺少请求方法。")
        if not case.path:
            warnings.append(f"{case.case_id}：缺少接口路径。")
        if not case.expected_status:
            warnings.append(f"{case.case_id}：缺少预期状态码。")
        if not case.assertions:
            warnings.append(f"{case.case_id}：缺少断言点。")

    return warnings


def _normalize_rows(rows: Any) -> list[dict[str, Any]]:
    if hasattr(rows, "to_dict"):
        return rows.to_dict(orient="records")
    return list(rows or [])


def _cell(row: dict[str, Any], column: str) -> str:
    value = row.get(column, "")
    if value is None:
        return ""
    return str(value).strip()
