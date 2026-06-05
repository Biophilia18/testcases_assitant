from __future__ import annotations

from dataclasses import dataclass

from src.coverage_analyzer import build_coverage_matrix
from src.models import TestCase
from src.quality_checker import VAGUE_EXPECTED_KEYWORDS


@dataclass(frozen=True)
class ScoreDetail:
    label: str
    points: int


@dataclass(frozen=True)
class QualityScore:
    score: int
    summary: str
    additions: list[ScoreDetail]
    deductions: list[ScoreDetail]


COVERAGE_POINTS = {
    "正常流程": 8,
    "异常场景": 8,
    "边界/非法输入": 8,
    "权限控制": 6,
    "重复操作": 5,
    "状态流转": 5,
    "数据一致性": 5,
}

BASE_SCORE = 60


def calculate_quality_score(cases: list[TestCase], coverage_types: list[str] | None = None) -> QualityScore:
    if not cases:
        return QualityScore(
            score=0,
            summary="暂无用例，无法评估质量。",
            additions=[],
            deductions=[ScoreDetail("暂无测试用例", -BASE_SCORE)],
        )

    additions = _coverage_additions(cases, coverage_types)
    deductions = _content_deductions(cases)
    raw_score = BASE_SCORE + sum(item.points for item in additions) + sum(item.points for item in deductions)
    score = max(0, min(100, raw_score))

    return QualityScore(
        score=score,
        summary=_score_summary(score),
        additions=additions,
        deductions=deductions,
    )


def _coverage_additions(cases: list[TestCase], coverage_types: list[str] | None) -> list[ScoreDetail]:
    matrix = build_coverage_matrix(cases, coverage_types)
    additions: list[ScoreDetail] = []

    for item in matrix:
        points = COVERAGE_POINTS.get(item.coverage_type, 0)
        if item.covered and points:
            additions.append(ScoreDetail(f"覆盖{item.coverage_type}", points))

    return additions


def _content_deductions(cases: list[TestCase]) -> list[ScoreDetail]:
    short_steps = 0
    vague_expected = 0
    empty_test_data = 0

    for case in cases:
        step_count = case.steps.count("\n") + 1 if case.steps else 0
        if step_count < 2:
            short_steps += 1
        if case.expected_result in VAGUE_EXPECTED_KEYWORDS or len(case.expected_result) < 8:
            vague_expected += 1
        if not case.test_data:
            empty_test_data += 1

    deductions: list[ScoreDetail] = []
    if short_steps:
        deductions.append(ScoreDetail(f"操作步骤过短 {short_steps} 条", -2 * short_steps))
    if vague_expected:
        deductions.append(ScoreDetail(f"预期结果过泛 {vague_expected} 条", -2 * vague_expected))
    if empty_test_data:
        deductions.append(ScoreDetail(f"测试数据为空 {empty_test_data} 条", -empty_test_data))

    return deductions


def _score_summary(score: int) -> str:
    if score >= 90:
        return "覆盖较完整，用例质量较高。"
    if score >= 75:
        return "基础质量可用，建议补齐缺口后再交付。"
    if score >= 60:
        return "可作为初稿，需要重点补充覆盖和执行细节。"
    return "质量偏低，建议重新梳理需求和用例覆盖。"
