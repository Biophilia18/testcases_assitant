from __future__ import annotations

from dataclasses import dataclass
import re

from src.api.document_parser import parse_api_document
from src.api.models import ApiDocument
from src.api.param_parser import parse_api_params


INTERFACE_NAME_PATTERN = re.compile(r"^\s*(?:#{1,6}\s*)?接口名称\s*[:：]\s*(.+?)\s*$", re.IGNORECASE)
METHOD_PATTERN = re.compile(r"^\s*(?:#{1,6}\s*)?(请求方法|请求方式|Method|HTTP Method)\s*[:：]\s*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s*$", re.IGNORECASE)
PATH_PATTERN = re.compile(r"^\s*(?:#{1,6}\s*)?(接口路径|请求路径|接口地址|请求地址|API地址|URL)\s*[:：]\s*(/.+?)\s*$", re.IGNORECASE)
COMMON_TITLE_PATTERN = re.compile(r"^\s*(?:#{1,6}\s*)?(项目/系统名称|项目名称|系统名称|业务模块|模块)\s*[:：]")


@dataclass
class ApiDocumentCandidate:
    index: int
    display_name: str
    document: ApiDocument
    source_text: str


def extract_api_document_candidates(text: str) -> list[ApiDocumentCandidate]:
    lines = text.splitlines()
    starts = _interface_start_lines(lines)
    if len(starts) <= 1:
        document = parse_api_document(text)
        return [_candidate(1, document, text)]

    common_prefix = _common_prefix(lines, starts[0])
    candidates: list[ApiDocumentCandidate] = []
    for index, start in enumerate(starts, start=1):
        end = starts[index] if index < len(starts) else len(lines)
        segment = "\n".join(common_prefix + lines[start:end]).strip()
        document = parse_api_document(segment)
        candidates.append(_candidate(index, document, segment))
    return candidates


def api_document_candidates_to_rows(candidates: list[ApiDocumentCandidate]) -> list[dict[str, str | int]]:
    return [
        {
            "序号": candidate.index,
            "接口名称": candidate.document.api_name or "-",
            "请求方法": candidate.document.method or "-",
            "接口路径": candidate.document.path or "-",
            "业务模块": candidate.document.module or "-",
            "参数数": _param_count(candidate.document),
            "鉴权": _yes_no(candidate.document.auth),
            "业务规则": _yes_no(candidate.document.business_rules),
            "数据库校验": _yes_no(candidate.document.db_checks),
            "复杂度": candidate_complexity_label(candidate.document),
            "建议": _candidate_suggestion(candidate.document),
        }
        for candidate in candidates
    ]


def candidate_complexity_label(document: ApiDocument) -> str:
    score = 0
    if _param_count(document) >= 5:
        score += 1
    if document.auth.strip():
        score += 1
    if document.business_rules.strip():
        score += 1
    if document.db_checks.strip():
        score += 1

    if score <= 1:
        return "低"
    if score <= 3:
        return "中"
    return "高"


def _interface_start_lines(lines: list[str]) -> list[int]:
    name_starts = [index for index, line in enumerate(lines) if INTERFACE_NAME_PATTERN.match(line)]
    if name_starts:
        return name_starts

    starts: list[int] = []
    for index, line in enumerate(lines):
        if _looks_like_method_path_start(lines, index):
            starts.append(index)
    return _dedupe_sorted(starts)


def _looks_like_method_path_start(lines: list[str], index: int) -> bool:
    line = lines[index]
    if not (METHOD_PATTERN.match(line) or PATH_PATTERN.match(line)):
        return False

    nearby_lines = lines[index : min(index + 4, len(lines))]
    has_method = any(METHOD_PATTERN.match(item) for item in nearby_lines)
    has_path = any(PATH_PATTERN.match(item) for item in nearby_lines)
    if not (has_method and has_path):
        return False

    previous_non_empty = _previous_non_empty_line(lines, index)
    return previous_non_empty is None or _is_boundary_line(previous_non_empty)


def _previous_non_empty_line(lines: list[str], index: int) -> str | None:
    for previous_index in range(index - 1, -1, -1):
        value = lines[previous_index].strip()
        if value:
            return value
    return None


def _is_boundary_line(line: str) -> bool:
    return bool(
        INTERFACE_NAME_PATTERN.match(line)
        or COMMON_TITLE_PATTERN.match(line)
        or line.startswith("#")
        or line.startswith("---")
        or line in {"接口列表", "接口清单"}
    )


def _common_prefix(lines: list[str], first_interface_start: int) -> list[str]:
    prefix = []
    for line in lines[:first_interface_start]:
        if COMMON_TITLE_PATTERN.match(line):
            prefix.append(line)
    return prefix


def _dedupe_sorted(values: list[int]) -> list[int]:
    result: list[int] = []
    for value in sorted(values):
        if value not in result:
            result.append(value)
    return result


def _candidate(index: int, document: ApiDocument, source_text: str) -> ApiDocumentCandidate:
    display_name = document.api_name or document.path or f"接口{index}"
    if document.method and document.path:
        display_name = f"{display_name}（{document.method} {document.path}）"
    return ApiDocumentCandidate(index=index, display_name=display_name, document=document, source_text=source_text)


def _candidate_suggestion(document: ApiDocument) -> str:
    complexity = candidate_complexity_label(document)
    if complexity == "高":
        return "建议优先设计，需重点复核规则和数据校验"
    if document.method and document.path and _param_count(document) > 0:
        return "适合生成用例"
    if document.method and document.path:
        return "可生成，建议补充参数说明"
    return "信息不足，需补充"


def _param_count(document: ApiDocument) -> int:
    return len(parse_api_params(document))


def _yes_no(value: str) -> str:
    return "是" if value.strip() else "否"
