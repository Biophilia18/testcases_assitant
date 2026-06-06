from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from src.api_models import ApiDocument


@dataclass
class ApiParam:
    name: str
    required: bool
    param_type: str
    rule: str
    source: str


def parse_api_params(document: ApiDocument) -> list[ApiParam]:
    params: list[ApiParam] = []
    params.extend(_parse_text_params(document.params, "query"))
    params.extend(_parse_body_params(document.body))
    return _merge_params(params)


def _parse_text_params(text: str, source: str) -> list[ApiParam]:
    params: list[ApiParam] = []
    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        if not line or line in {"无", "none", "None"}:
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
                source=source,
            )
        )
    return params


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
    merged: dict[tuple[str, str], ApiParam] = {}
    for param in params:
        key = (param.name, param.source)
        if key not in merged:
            merged[key] = param
            continue

        current = merged[key]
        merged[key] = ApiParam(
            name=current.name,
            required=current.required or param.required,
            param_type=current.param_type or param.param_type,
            rule=_join_unique(current.rule, param.rule),
            source=current.source,
        )
    return list(merged.values())


def _split_name_and_description(line: str) -> tuple[str, str]:
    normalized = line.strip()
    for separator in ["：", ":", "，", ",", "、", " "]:
        if separator in normalized:
            name, description = normalized.split(separator, 1)
            return _clean_name(name), description.strip()
    return _clean_name(normalized), normalized


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
    unique_parts = []
    for part in parts:
        if part not in unique_parts:
            unique_parts.append(part)
    return "\n".join(unique_parts)
