from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from src.models import TestCase


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    case_id: str
    message: str


VAGUE_EXPECTED_KEYWORDS = ["正常", "正确", "符合要求", "成功", "通过"]


def check_cases(cases: list[TestCase]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    case_id_counts = Counter(case.case_id for case in cases if case.case_id)

    for case in cases:
        issues.extend(_check_required_fields(case))
        issues.extend(_check_case_content(case))
        if case.case_id and case_id_counts[case.case_id] > 1:
            issues.append(QualityIssue("错误", case.case_id, "用例编号重复。"))

    issues.extend(_check_coverage(cases))
    return issues


def issue_messages(cases: list[TestCase]) -> list[str]:
    return [f"[{issue.severity}] {issue.case_id} {issue.message}" for issue in check_cases(cases)]


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


def _check_coverage(cases: list[TestCase]) -> list[QualityIssue]:
    if not cases:
        return []

    case_types = {case.case_type for case in cases}
    issues: list[QualityIssue] = []

    if not any("异常" in case_type for case_type in case_types):
        issues.append(QualityIssue("提示", "整体", "当前结果缺少异常测试用例。"))
    if not any("边界" in case_type for case_type in case_types):
        issues.append(QualityIssue("提示", "整体", "当前结果缺少边界测试用例。"))
    if not any("权限" in case_type for case_type in case_types):
        issues.append(QualityIssue("提示", "整体", "当前结果缺少权限测试用例。"))

    return issues
