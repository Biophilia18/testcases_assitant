from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from src.api.models import ApiDocument


@dataclass
class ApiParam:
    name: str
    required: bool
    param_type: str
    rule: str
    source: str


def parse_api_params(document: ApiDocument) -> list[ApiParam]:
    params: list[ApiParam] = []
    path_param_names = _path_param_names(document.path)
    params.extend(_parse_text_params(document.params, "query", path_param_names=path_param_names))
    params.extend(_parse_body_params(document.body))
    return _merge_params(params)


def _parse_text_params(text: str, source: str, path_param_names: set[str] | None = None) -> list[ApiParam]:
    params: list[ApiParam] = []
    path_param_names = path_param_names or set()
    table_headers: list[str] = []
    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        if not line or line in {"无", "none", "None"}:
            continue
        if _is_markdown_table_separator(line):
            continue
        if _is_markdown_table_row(line):
            cells = _table_cells(line)
            if _looks_like_table_header(cells):
                table_headers = cells
                continue
            table_param = _parse_table_param(cells, table_headers, source, path_param_names)
            if table_param:
                params.append(table_param)
            continue

        name, description = _split_name_and_description(line)
        if not name:
            continue

        params.append(
            ApiParam(
                name=name,
                required=_is_required(description),
                param_type=_detect_type(description),
                rule=_extract_rule(description),
                source=_detect_source(name, description, source, path_param_names),
            )
        )
    return params


def _is_markdown_table_row(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 2


def _is_markdown_table_separator(line: str) -> bool:
    if not _is_markdown_table_row(line):
        return False
    value = line.replace("|", "").replace(":", "").replace("-", "").strip()
    return value == ""


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _looks_like_table_header(cells: list[str]) -> bool:
    joined = " ".join(cells)
    return any(keyword in joined for keyword in ["参数名", "字段名", "字段", "名称"]) and any(
        keyword in joined for keyword in ["类型", "必填", "说明", "描述"]
    )


def _parse_table_param(
    cells: list[str],
    headers: list[str],
    source: str,
    path_param_names: set[str],
) -> ApiParam | None:
    if not cells:
        return None

    field_map = _table_field_map(cells, headers)
    name = _clean_name(field_map.get("name", cells[0] if cells else ""))
    if not name or name in {"参数名", "字段名", "字段", "名称"}:
        return None

    description_parts = [
        field_map.get("required", ""),
        field_map.get("type", ""),
        field_map.get("description", ""),
        " ".join(cells[1:]) if not headers else "",
    ]
    description = "，".join(part for part in description_parts if part).strip()
    required_text = field_map.get("required", "")
    return ApiParam(
        name=name,
        required=_is_required_from_table(required_text, description),
        param_type=_detect_type(description),
        rule=_extract_rule(description),
        source=_detect_source(name, description, source, path_param_names),
    )


def _table_field_map(cells: list[str], headers: list[str]) -> dict[str, str]:
    if not headers:
        return {"name": cells[0], "description": "，".join(cells[1:])}

    result: dict[str, str] = {}
    for index, header in enumerate(headers):
        if index >= len(cells):
            continue
        value = cells[index]
        if any(keyword in header for keyword in ["参数名", "字段名", "名称"]):
            result["name"] = value
        elif "类型" in header:
            result["type"] = value
        elif any(keyword in header for keyword in ["必填", "是否必填", "是否必须", "必需"]):
            result["required"] = value
        elif any(keyword in header for keyword in ["说明", "描述", "规则", "备注"]):
            result["description"] = value
    if "description" not in result:
        result["description"] = "，".join(cells[1:])
    return result


def _is_required_from_table(required_text: str, description: str) -> bool:
    text = f"{required_text} {description}".strip()
    if required_text.strip() in {"否", "N", "n", "No", "no", "false", "False"}:
        return False
    if required_text.strip() in {"是", "Y", "y", "Yes", "yes", "true", "True"}:
        return True
    return _is_required(text)


def _parse_body_params(body: str) -> list[ApiParam]:
    cleaned = _strip_markdown_fences(body)
    if not cleaned.strip():
        return []

    parsed_json = _try_parse_json(cleaned)
    if isinstance(parsed_json, dict):
        return [
            ApiParam(
                name=str(key),
                required=True,
                param_type=_type_from_value(value),
                rule="",
                source="body",
            )
            for key, value in parsed_json.items()
        ]

    return _parse_text_params(cleaned, "body")


def _merge_params(params: list[ApiParam]) -> list[ApiParam]:
    merged_by_source: dict[tuple[str, str], ApiParam] = {}
    for param in params:
        key = (param.name, param.source)
        if key not in merged_by_source:
            merged_by_source[key] = param
            continue

        current = merged_by_source[key]
        merged_by_source[key] = ApiParam(
            name=current.name,
            required=current.required or param.required,
            param_type=current.param_type or param.param_type,
            rule=_join_unique(current.rule, param.rule),
            source=current.source,
        )

    grouped_by_name: dict[str, list[ApiParam]] = {}
    for param in merged_by_source.values():
        grouped_by_name.setdefault(param.name, []).append(param)

    merged: list[ApiParam] = []
    for same_name_params in grouped_by_name.values():
        body_param = next((param for param in same_name_params if param.source == "body"), None)
        if body_param:
            merged.append(_merge_same_name_params(body_param, same_name_params))
        else:
            merged.extend(same_name_params)
    return merged


def _merge_same_name_params(primary: ApiParam, params: list[ApiParam]) -> ApiParam:
    return ApiParam(
        name=primary.name,
        required=any(param.required for param in params),
        param_type=primary.param_type or next((param.param_type for param in params if param.param_type), ""),
        rule="\n".join(_unique_non_empty(param.rule for param in params)),
        source=primary.source,
    )


def _split_name_and_description(line: str) -> tuple[str, str]:
    normalized = line.strip()
    for separator in ["：", ":", "，", ",", "、", " "]:
        if separator in normalized:
            name, description = normalized.split(separator, 1)
            return _clean_name(name), description.strip()
    return _clean_name(normalized), normalized


def _path_param_names(path: str) -> set[str]:
    return {match.strip() for match in re.findall(r"\{([^{}]+)\}", path or "") if match.strip()}


def _detect_source(name: str, description: str, fallback_source: str, path_param_names: set[str]) -> str:
    lowered = description.lower()
    if name in path_param_names or any(keyword in description for keyword in ["路径参数", "路径变量"]) or "path" in lowered:
        return "path"
    if any(keyword in description for keyword in ["请求体", "body", "json"]):
        return "body"
    if any(keyword in description for keyword in ["查询参数", "query"]):
        return "query"
    return fallback_source


def _clean_line(line: str) -> str:
    cleaned = line.strip()
    cleaned = re.sub(r"^[-*•]\s*", "", cleaned)
    cleaned = re.sub(r"^\d+[.)、]\s*", "", cleaned)
    return cleaned.strip()


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    cleaned = re.sub(r"^[\"'`{]+|[\"'`,}]+$", "", cleaned)
    return cleaned.strip()


def _is_required(description: str) -> bool:
    if any(keyword in description for keyword in ["非必填", "选填", "可选", "optional"]):
        return False
    return any(keyword in description for keyword in ["必填", "必传", "不能为空", "required", "Required"])


def _detect_type(description: str) -> str:
    lowered = description.lower()
    type_keywords = [
        ("string", ["string", "str", "字符串", "文本"]),
        ("integer", ["integer", "int", "整数"]),
        ("number", ["number", "float", "double", "decimal", "数字", "数值", "金额"]),
        ("boolean", ["boolean", "bool", "布尔"]),
        ("array", ["array", "list", "数组", "列表"]),
        ("object", ["object", "对象"]),
        ("date", ["date", "日期"]),
        ("datetime", ["datetime", "time", "时间"]),
    ]
    for param_type, keywords in type_keywords:
        if any(keyword in lowered or keyword in description for keyword in keywords):
            return param_type
    return ""


def _extract_rule(description: str) -> str:
    rule_keywords = [
        "长度",
        "范围",
        "大于",
        "小于",
        "不大于",
        "不小于",
        "最大",
        "最小",
        "枚举",
        "允许值",
        "取值",
        "格式",
        "手机号",
        "不能早于",
        "不能晚于",
        "正则",
    ]
    return description.strip() if any(keyword in description for keyword in rule_keywords) else ""


def _strip_markdown_fences(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def _try_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _type_from_value(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def _join_unique(left: str, right: str) -> str:
    parts = [part for part in [left.strip(), right.strip()] if part]
    return "\n".join(_unique_non_empty(parts))


def _unique_non_empty(parts) -> list[str]:
    unique_parts = []
    for part in parts:
        if part and part not in unique_parts:
            unique_parts.append(part)
    return unique_parts
