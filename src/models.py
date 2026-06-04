from dataclasses import dataclass


@dataclass
class TestCase:
    module: str
    feature: str
    title: str
    precondition: str
    steps: str
    expected_result: str
    priority: str
    case_type: str


@dataclass
class GenerationResult:
    cases: list[TestCase]
    requested_mode: str
    actual_mode: str
    feature_count: int
    case_count: int
    provider: str = ""
    model: str = ""
    message: str = ""
    fallback_reason: str = ""


EXCEL_COLUMNS = [
    "模块",
    "功能点",
    "用例标题",
    "前置条件",
    "操作步骤",
    "预期结果",
    "优先级",
    "用例类型",
]
