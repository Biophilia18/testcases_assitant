from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedRequirement:
    project_name: str = ""
    business_module: str = ""
    user_role: str = ""
    precondition: str = ""
    business_flow: str = ""
    acceptance_criteria: str = ""
    constraints: str = ""


FIELD_ALIASES = {
    "project_name": ["项目", "项目名称", "系统", "系统名称", "项目/系统名称", "项目系统名称", "产品", "应用"],
    "business_module": ["模块", "业务模块", "功能模块", "所属模块"],
    "user_role": ["角色", "用户角色", "使用角色", "操作角色", "参与角色"],
    "precondition": ["前置条件", "前提条件", "前置", "准备条件"],
    "business_flow": ["需求", "需求描述", "业务流程", "业务流程/需求描述", "业务流程需求描述", "流程", "功能描述", "用户故事", "场景", "正文"],
    "acceptance_criteria": ["验收标准", "验收条件", "通过标准", "预期结果", "验收"],
    "constraints": ["补充规则", "异常场景", "补充规则/异常场景", "补充规则异常场景", "业务规则", "限制条件", "约束", "注意事项", "边界条件"],
}

BLOCK_FIELDS = {"precondition", "business_flow", "acceptance_criteria", "constraints"}


def parse_requirement_text(raw_text: str) -> ParsedRequirement:
    text = _clean_text(raw_text)
    parsed = ParsedRequirement()
    if not text:
        return parsed

    consumed_lines: set[int] = set()
    lines = text.splitlines()
    current_field = ""
    buffers = {field: [] for field in FIELD_ALIASES}

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        heading_field = _match_heading(stripped)
        if heading_field:
            current_field = heading_field
            consumed_lines.add(index)
            inline_value = _heading_inline_value(stripped)
            if inline_value:
                buffers[current_field].append(_clean_content_line(inline_value))
            continue

        pair = _match_key_value(stripped)
        if pair:
            field, value = pair
            buffers[field].append(_clean_content_line(value))
            current_field = field
            consumed_lines.add(index)
            continue

        if current_field in BLOCK_FIELDS:
            buffers[current_field].append(_clean_content_line(stripped))
            consumed_lines.add(index)

    for field, values in buffers.items():
        setattr(parsed, field, _join_values(values))

    remaining = [line.strip() for index, line in enumerate(lines) if index not in consumed_lines and line.strip()]
    if remaining:
        extra_flow = _join_values(remaining)
        parsed.business_flow = _join_values([parsed.business_flow, extra_flow])

    if not parsed.business_flow and not any(
        [parsed.project_name, parsed.business_module, parsed.user_role, parsed.precondition, parsed.acceptance_criteria, parsed.constraints]
    ):
        parsed.business_flow = _fallback_business_flow(text)

    return parsed


def _clean_text(raw_text: str) -> str:
    text = raw_text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def _match_heading(line: str) -> str:
    normalized = line.strip().strip("#").strip()
    normalized = re.sub(r"^[一二三四五六七八九十\d]+[、.)]\s*", "", normalized)
    normalized = normalized.rstrip("：:")

    normalized_key = _normalize_key(normalized)
    for field, aliases in FIELD_ALIASES.items():
        if normalized_key in {_normalize_key(alias) for alias in aliases}:
            return field
    return ""


def _heading_inline_value(line: str) -> str:
    if "：" in line:
        return line.split("：", 1)[1].strip()
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return ""


def _match_key_value(line: str) -> tuple[str, str] | None:
    match = re.match(r"^[-*•\s]*([^：:]{2,12})[：:]\s*(.+)$", line)
    if not match:
        return None

    key = match.group(1).strip().strip("#").strip()
    value = match.group(2).strip()
    normalized_key = _normalize_key(key)
    for field, aliases in FIELD_ALIASES.items():
        if normalized_key in {_normalize_key(alias) for alias in aliases}:
            return field, value
    return None


def _join_values(values: list[str]) -> str:
    return "\n".join(value for value in values if value).strip()


def _fallback_business_flow(text: str) -> str:
    lines = [_clean_content_line(line.strip()) for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _normalize_key(key: str) -> str:
    return re.sub(r"[\s/_\-|｜]+", "", key.strip())


def _clean_content_line(line: str) -> str:
    cleaned = line.strip()
    cleaned = re.sub(r"^[-*•]\s*", "", cleaned)
    cleaned = re.sub(r"^\d+[.)、]\s*", "", cleaned)
    cleaned = re.sub(r"^[一二三四五六七八九十]+[、.)]\s*", "", cleaned)
    return cleaned.strip()
