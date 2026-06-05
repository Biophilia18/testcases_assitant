from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from src.coverage_analyzer import infer_case_coverage_types
from src.coverage_config import normalize_coverage_types
from src.models import TestCase


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    case_id: str
    message: str


VAGUE_EXPECTED_KEYWORDS = ["正常", "正确", "符合要求", "成功", "通过"]


def check_cases(cases: list[TestCase], coverage_types: list[str] | None = None) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    case_id_counts = Counter(case.case_id for case in cases if case.case_id)

    for case in cases:
        issues.extend(_check_required_fields(case))
        issues.extend(_check_case_content(case))
        if case.case_id and case_id_counts[case.case_id] > 1:
            issues.append(QualityIssue("错误", case.case_id, "用例编号重复。"))

    issues.extend(_check_coverage(cases, coverage_types))
    return issues


def issue_messages(cases: list[TestCase], coverage_types: list[str] | None = None) -> list[str]:
    return [f"[{issue.severity}] {issue.case_id} {issue.message}" for issue in check_cases(cases, coverage_types)]


def build_quality_report_rows(cases: list[TestCase], coverage_types: list[str] | None = None) -> list[list[str | int]]:
    selected_coverage_types = normalize_coverage_types(coverage_types)
    issues = check_cases(cases, selected_coverage_types)
    priority_counts = Counter(case.priority or "未设置" for case in cases)
    type_counts = Counter(case.case_type or "未设置" for case in cases)
    feature_count = len({f"{case.module}:{case.feature}" for case in cases})

    rows: list[list[str | int]] = [
        ["指标", "值"],
        ["总用例数", len(cases)],
        ["功能点数量", feature_count],
        ["质量提示数", len(issues)],
        ["覆盖类型", "、".join(selected_coverage_types)],
        ["P0 用例数", priority_counts.get("P0", 0)],
        ["P1 用例数", priority_counts.get("P1", 0)],
        ["P2 用例数", priority_counts.get("P2", 0)],
        ["P3 用例数", priority_counts.get("P3", 0)],
        ["", ""],
        ["用例类型", "数量"],
    ]

    rows.extend([[case_type, count] for case_type, count in sorted(type_counts.items())])
    rows.extend([["", ""], ["严重程度", "用例编号", "问题"]])
    rows.extend([[issue.severity, issue.case_id, issue.message] for issue in issues])

    return rows


def _check_required_fields(case: TestCase) -> list[QualityIssue]:
    checks = [
        (case.case_id, "缺少用例编号。"),
        (case.title, "缺少用例标题。"),
        (case.steps, "缺少操作步骤。"),
        (case.expected_result, "缺少预期结果。"),
        (case.priority, "缺少优先级。"),
    ]
    return [QualityIssue("错误", case.case_id or "-", message) for value, message in checks if not value]


def _check_case_content(case: TestCase) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    step_count = case.steps.count("\n") + 1 if case.steps else 0

    if case.steps and step_count < 2:
        issues.append(QualityIssue("提示", case.case_id, "操作步骤少于 2 步，建议补充执行细节。"))

    if case.expected_result in VAGUE_EXPECTED_KEYWORDS or len(case.expected_result) < 8:
        issues.append(QualityIssue("提示", case.case_id, "预期结果偏笼统，建议写清页面提示、状态或数据变化。"))

    if not case.test_data:
        issues.append(QualityIssue("提示", case.case_id, "测试数据为空，建议补充账号、参数或边界值。"))

    return issues


def _check_coverage(cases: list[TestCase], coverage_types: list[str] | None = None) -> list[QualityIssue]:
    if not cases:
        return []

    issues: list[QualityIssue] = []
    expected_coverage_types = normalize_coverage_types(coverage_types)

    groups: dict[str, list[TestCase]] = {}
    for case in cases:
        groups.setdefault(f"{case.module} / {case.feature}", []).append(case)

    for group_key, group_cases in groups.items():
        covered = set()
        for case in group_cases:
            covered.update(_case_coverage_types(case))

        for coverage_type in expected_coverage_types:
            if coverage_type not in covered:
                issues.append(QualityIssue("提示", group_key, f"缺少{coverage_type}用例。"))

    return issues


def _case_coverage_types(case: TestCase) -> set[str]:
    return infer_case_coverage_types(case)


def _check_legacy_coverage(cases: list[TestCase]) -> list[QualityIssue]:
    case_types = {case.case_type for case in cases}
    issues: list[QualityIssue] = []

    if not any("异常" in case_type for case_type in case_types):
        issues.append(QualityIssue("提示", "整体", "当前结果缺少异常测试用例。"))
    if not any("边界" in case_type for case_type in case_types):
        issues.append(QualityIssue("提示", "整体", "当前结果缺少边界测试用例。"))
    if not any("权限" in case_type for case_type in case_types):
        issues.append(QualityIssue("提示", "整体", "当前结果缺少权限测试用例。"))

    return issues
