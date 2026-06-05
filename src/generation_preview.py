from __future__ import annotations

from dataclasses import dataclass

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
    warnings = _build_warnings(len(feature_items), estimated_case_count)

    return GenerationPreview(
        requirement_text=requirement_text,
        feature_source_text=source_text,
        feature_items=feature_items,
        cases_per_feature=actual_cases_per_feature,
        coverage_types=normalized_coverage_types,
        estimated_case_count=estimated_case_count,
        warnings=warnings,
    )


def _build_warnings(feature_count: int, estimated_case_count: int) -> list[str]:
    warnings: list[str] = []
    if feature_count >= HIGH_FEATURE_COUNT:
        warnings.append(
            f"识别到 {feature_count} 个功能点，数量偏多。建议检查是否把验收标准或异常规则拆成了功能点。"
        )
    if estimated_case_count >= HIGH_CASE_COUNT:
        warnings.append(
            f"预计生成 {estimated_case_count} 条用例，数量偏多。建议先减少每个功能点用例数，或调整业务流程描述。"
        )
    return warnings
