from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlencode

from src.api.models import ApiDocument, ApiTestCase


def build_api_auto_yaml(cases: list[ApiTestCase], document: ApiDocument | None = None) -> str:
    document = document or ApiDocument()
    yaml_cases = [_case_to_api_auto_dict(case, document) for case in cases]
    return _dump_yaml(yaml_cases)


def build_api_auto_preview_rows(cases: list[ApiTestCase]) -> list[dict[str, str]]:
    rows = []
    for case in cases:
        readiness = "可导出" if _is_yaml_ready(case) else "需补充"
        rows.append(
            {
                "用例编号": case.case_id,
                "用例标题": case.case_title,
                "接口": case.api_name,
                "方法": case.method,
                "路径": case.path,
                "自动化就绪": readiness,
                "说明": _readiness_note(case),
            }
        )
    return rows


def _case_to_api_auto_dict(case: ApiTestCase, document: ApiDocument) -> dict[str, Any]:
    request: dict[str, Any] = {
        "method": (case.method or document.method or "GET").lower(),
        "url": _url_with_query(case.path or document.path, case.query_params),
    }
    headers = _parse_mapping(case.headers or document.headers)
    if headers:
        request["headers"] = headers

    body = _parse_json_object(case.request_body)
    if body:
        request["json"] = body

    yaml_case: dict[str, Any] = {
        "feature": case.module or document.module or "接口模块",
        "story": case.api_name or document.api_name or "接口用例",
        "title": case.case_title or f"{case.case_type}-{case.api_name or document.api_name or '接口'}",
        "request": request,
        "validate": _build_validate(case),
    }

    extract = _build_extract(case)
    if extract:
        yaml_case["extract"] = extract
    return yaml_case


def _build_validate(case: ApiTestCase) -> dict[str, Any]:
    expected_status = _to_int(case.expected_status, default=200)
    validate: dict[str, Any] = {
        "equals": {
            f"状态码为{expected_status}": [expected_status, "status_code"],
        }
    }
    contains = _contains_rules(case)
    if contains:
        validate["contains"] = contains

    db_rule = _db_validate_rule(case)
    if db_rule:
        validate["db_validate"] = db_rule
    return validate


def _contains_rules(case: ApiTestCase) -> dict[str, list[str]]:
    text = f"{case.assertions}\n{case.remark}"
    rules: dict[str, list[str]] = {}
    if "success" in text:
        rules["响应包含success"] = ["success", "text"]
    if "id" in text or "ID" in text:
        rules["响应包含id字段"] = ["id", "text"]
    return rules


def _build_extract(case: ApiTestCase) -> dict[str, list[str]]:
    extract_vars = _split_lines(case.extract_vars)
    extract: dict[str, list[str]] = {}
    for item in extract_vars:
        name, path = _parse_extract_item(item)
        if name:
            extract[name] = ["json", path or f"data.{name}"]
    return extract


def _db_validate_rule(case: ApiTestCase) -> dict[str, dict[str, Any]]:
    db_check = case.db_check.strip()
    if not db_check:
        return {}
    if "select" not in db_check.lower():
        return {}
    return {
        "数据库校验": {
            "sql": db_check,
            "expect": [],
        }
    }


def _url_with_query(path: str, query_params: str) -> str:
    path = path.strip() or "/"
    params = _parse_mapping(query_params)
    if not params:
        return path
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}{urlencode(params)}"


def _parse_mapping(text: str) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for raw_line in _split_lines(text):
        line = raw_line.strip().strip(",")
        if not line:
            continue
        if ":" in line:
            key, value = line.split(":", 1)
        elif "=" in line:
            key, value = line.split("=", 1)
        elif "：" in line:
            key, value = line.split("：", 1)
        else:
            continue
        key = key.strip().strip('"').strip("'")
        value = value.strip().strip(",").strip()
        if key:
            mapping[key] = _coerce_scalar(value)
    return mapping


def _parse_json_object(text: str) -> dict[str, Any]:
    value = text.strip()
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return _parse_mapping(value)
    return parsed if isinstance(parsed, dict) else {}


def _parse_extract_item(text: str) -> tuple[str, str]:
    if ":" in text:
        name, path = text.split(":", 1)
        return name.strip(), path.strip()
    if "=" in text:
        name, path = text.split("=", 1)
        return name.strip(), path.strip()
    name = text.strip()
    return name, ""


def _is_yaml_ready(case: ApiTestCase) -> bool:
    return bool(case.case_title.strip() and case.method.strip() and case.path.strip() and case.expected_status.strip())


def _readiness_note(case: ApiTestCase) -> str:
    missing = []
    if not case.case_title.strip():
        missing.append("用例标题")
    if not case.method.strip():
        missing.append("请求方法")
    if not case.path.strip():
        missing.append("接口路径")
    if not case.expected_status.strip():
        missing.append("预期状态码")
    if not missing:
        return "已具备 api_auto 基础 YAML 字段；复杂断言和数据库 SQL 仍建议人工复核。"
    return "缺少：" + "、".join(missing)


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in re.split(r"[\n;；]+", text or "") if line.strip()]


def _coerce_scalar(value: str) -> Any:
    clean = value.strip().strip('"').strip("'")
    if clean.startswith("${") and clean.endswith("}"):
        return clean
    if clean.lower() in {"true", "false"}:
        return clean.lower() == "true"
    number = _to_int(clean, default=None)
    if number is not None:
        return number
    return clean


def _to_int(value: Any, default: int | None = 0) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _dump_yaml(value: Any, indent: int = 0) -> str:
    lines = _dump_yaml_lines(value, indent)
    return "\n".join(lines) + "\n"


def _dump_yaml_lines(value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, list):
        lines: list[str] = []
        for item in value:
            if isinstance(item, (dict, list)):
                item_lines = _dump_yaml_lines(item, indent + 2)
                lines.append(f"{prefix}- {item_lines[0].lstrip()}")
                lines.extend(item_lines[1:])
            else:
                lines.append(f"{prefix}- {_yaml_scalar(item)}")
        return lines
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{prefix}{key}:")
                lines.extend(_dump_yaml_lines(item, indent + 2))
            elif item == {}:
                lines.append(f"{prefix}{key}: {{}}")
            elif item == []:
                lines.append(f"{prefix}{key}: []")
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(item)}")
        return lines
    return [f"{prefix}{_yaml_scalar(value)}"]


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    text = str(value)
    if text.startswith("${") and text.endswith("}"):
        return f'"{text}"'
    if not text or any(char in text for char in [":", "{", "}", "[", "]", "#", ","]) or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    return text
