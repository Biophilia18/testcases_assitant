from __future__ import annotations

from dataclasses import dataclass
import re

from src.coverage_config import normalize_coverage_types
from src.rule_based_generator import RequirementItem, extract_requirement_items


HIGH_FEATURE_COUNT = 12
HIGH_CASE_COUNT = 50


@dataclass
class GenerationPreview:
    requirement_text: str
    feature_source_text: str
    feature_items: list[RequirementItem]
    cases_per_feature: int
    coverage_types: list[str]
    estimated_case_count: int
    warnings: list[str]


def build_generation_preview(
    requirement_text: str,
    cases_per_feature: int,
    feature_source_text: str = "",
    coverage_types: list[str] | None = None,
) -> GenerationPreview:
    source_text = feature_source_text.strip() or requirement_text
    normalized_coverage_types = normalize_coverage_types(coverage_types) if coverage_types is not None else []
    feature_items = extract_requirement_items(source_text)
    actual_cases_per_feature = len(normalized_coverage_types) or cases_per_feature
    estimated_case_count = len(feature_items) * actual_cases_per_feature
    warnings = _build_warnings(feature_items, source_text, estimated_case_count)

    return GenerationPreview(
        requirement_text=requirement_text,
        feature_source_text=source_text,
        feature_items=feature_items,
        cases_per_feature=actual_cases_per_feature,
        coverage_types=normalized_coverage_types,
        estimated_case_count=estimated_case_count,
        warnings=warnings,
    )


def _build_warnings(feature_items: list[RequirementItem], source_text: str, estimated_case_count: int) -> list[str]:
    warnings: list[str] = []
    feature_count = len(feature_items)
    if feature_count >= HIGH_FEATURE_COUNT:
        warnings.append(
            f"识别到 {feature_count} 个功能点，数量偏多。建议检查是否把验收标准或异常规则拆成了功能点。"
        )
    if estimated_case_count >= HIGH_CASE_COUNT:
        warnings.append(
            f"预计生成 {estimated_case_count} 条用例，数量偏多。建议先减少每个功能点用例数，或调整业务流程描述。"
        )
    warnings.extend(_build_noise_warnings(feature_items, source_text))
    return warnings


def _build_noise_warnings(feature_items: list[RequirementItem], source_text: str) -> list[str]:
    warnings: list[str] = []
    suspicious_items = [item for item in feature_items if _looks_like_quality_rule(item.description)]
    if len(suspicious_items) >= 3:
        warnings.append(
            f"识别到 {len(suspicious_items)} 个片段更像验收标准、异常规则或数据校验。建议在预览表中取消这些项，把它们作为覆盖点复核。"
        )

    if _contains_structured_sections(source_text) and suspicious_items:
        warnings.append(
            "当前文本包含验收标准或补充规则。主功能点建议只保留业务流程中的用户操作，验收标准和异常规则用于检查覆盖完整性。"
        )
    return warnings


def _looks_like_quality_rule(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return False
    rule_keywords = [
        "验收标准",
        "补充规则",
        "异常场景",
        "不能为空",
        "不能",
        "必须",
        "一致",
        "数据库",
        "接口返回",
        "状态码",
        "重复",
        "无权限",
        "弱网",
        "断网",
        "超时",
        "失败提示",
        "正确更新",
    ]
    action_keywords = ["进入", "选择", "填写", "提交", "点击", "查询", "创建", "修改", "删除", "审批", "控制"]
    has_rule = any(keyword in compact for keyword in rule_keywords)
    has_action = any(keyword in compact for keyword in action_keywords)
    return has_rule and (not has_action or len(compact) <= 36)


def _contains_structured_sections(text: str) -> bool:
    return any(keyword in text for keyword in ["验收标准", "补充规则", "异常场景", "业务规则", "限制条件"])
