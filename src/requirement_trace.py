from __future__ import annotations

import re
from dataclasses import dataclass

from src.models import TestCase
from src.requirement_parser import parse_requirement_text


@dataclass
class RequirementTraceItem:
    source_type: str
    content: str
    covered: bool
    matched_case_ids: list[str]
    suggestion: str


def build_requirement_trace(cases: list[TestCase], requirement_text: str) -> list[RequirementTraceItem]:
    parsed = parse_requirement_text(requirement_text)
    source_items = [
        ("验收标准", item) for item in _split_trace_items(parsed.acceptance_criteria)
    ] + [
        ("补充规则/异常场景", item) for item in _split_trace_items(parsed.constraints)
    ]

    trace_items: list[RequirementTraceItem] = []
    for source_type, content in source_items:
        matched_case_ids = _matched_case_ids(cases, content)
        covered = bool(matched_case_ids)
        trace_items.append(
            RequirementTraceItem(
                source_type=source_type,
                content=content,
                covered=covered,
                matched_case_ids=matched_case_ids,
                suggestion=_trace_suggestion(source_type, content, covered),
            )
        )
    return trace_items


def requirement_trace_to_rows(trace_items: list[RequirementTraceItem]) -> list[dict[str, str]]:
    return [
        {
            "来源": item.source_type,
            "规则内容": item.content,
            "是否覆盖": "是" if item.covered else "否",
            "命中用例": "、".join(item.matched_case_ids) if item.matched_case_ids else "-",
            "建议": item.suggestion,
        }
        for item in trace_items
    ]


def requirement_trace_summary(trace_items: list[RequirementTraceItem]) -> dict[str, int]:
    covered_count = sum(1 for item in trace_items if item.covered)
    return {
        "total": len(trace_items),
        "covered": covered_count,
        "missing": len(trace_items) - covered_count,
    }


def _split_trace_items(text: str) -> list[str]:
    items: list[str] = []
    for raw_line in re.split(r"[\n；;]+", text or ""):
        line = _clean_trace_item(raw_line)
        if line:
            items.append(line)
    return _unique(items)


def _clean_trace_item(text: str) -> str:
    value = text.strip()
    value = re.sub(r"^[-*•]\s*", "", value)
    value = re.sub(r"^\d+[.)、]\s*", "", value)
    value = re.sub(r"^[一二三四五六七八九十]+[、.)]\s*", "", value)
    return value.strip(" 。；;")


def _matched_case_ids(cases: list[TestCase], rule: str) -> list[str]:
    return [case.case_id for case in cases if _case_matches_rule(case, rule)]


def _case_matches_rule(case: TestCase, rule: str) -> bool:
    case_text = _case_text(case)
    rule_text = _normalize(rule)

    for keywords, match_words in _rule_match_groups():
        if any(keyword in rule_text for keyword in keywords):
            return any(match_word in case_text for match_word in match_words)

    anchors = _rule_anchors(rule_text)
    if not anchors:
        return False
    return any(anchor in case_text for anchor in anchors)


def _case_text(case: TestCase) -> str:
    return _normalize(
        " ".join(
            [
                case.module,
                case.feature,
                case.title,
                case.precondition,
                case.test_data,
                case.steps,
                case.expected_result,
                case.case_type,
            ]
        )
    )


def _rule_match_groups() -> list[tuple[list[str], list[str]]]:
    return [
        (["重复", "多条", "多次"], ["重复", "幂等", "多条"]),
        (["创建成功", "生成唯一", "预约单号", "单号"], ["创建成功", "生成唯一", "预约单号", "单号"]),
        (["权限", "无权", "角色"], ["权限", "无权限", "拒绝访问"]),
        (["弱网", "断网", "超时", "网络"], ["弱网", "断网", "超时", "失败", "重试"]),
        (["数据库", "落库", "数据一致", "记录一致"], ["数据库", "数据一致", "一致", "关联数据", "记录"]),
        (["状态", "流转", "更新"], ["状态", "流转", "更新", "变更"]),
        (["失败", "错误", "异常", "不能", "不能为空", "非法"], ["异常", "失败", "错误", "非法", "阻止", "不能"]),
        (["必填", "为空", "空值"], ["必填", "为空", "空值"]),
        (["导出", "下载"], ["导出", "下载"]),
        (["查询", "列表", "详情"], ["查询", "列表", "详情"]),
    ]


def _rule_anchors(rule_text: str) -> list[str]:
    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", rule_text)
    ignored = {"可以", "需要", "必须", "不能", "正确", "一致", "进行", "用户", "系统", "页面", "数据"}
    anchors = [token for token in tokens if token not in ignored and len(token) >= 2]
    return anchors[:4]


def _trace_suggestion(source_type: str, content: str, covered: bool) -> str:
    if covered:
        return "已找到相关用例，建议人工确认步骤、测试数据和预期结果是否真正覆盖该规则。"
    if source_type == "验收标准":
        return "建议补充或调整用例，确保该验收标准有明确步骤和预期结果。"
    return "建议补充异常、边界、权限、弱网、重复提交或数据一致性相关用例。"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def _unique(items: list[str]) -> list[str]:
    result = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result
