from dataclasses import dataclass
from typing import ClassVar


@dataclass
class TestCase:
    __test__: ClassVar[bool] = False

    case_id: str
    module: str
    feature: str
    title: str
    precondition: str
    test_data: str
    steps: str
    expected_result: str
    priority: str
    case_type: str
    remark: str


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
    "用例编号",
    "模块",
    "功能点",
    "用例标题",
    "前置条件",
    "测试数据",
    "操作步骤",
    "预期结果",
    "优先级",
    "用例类型",
    "备注",
]
