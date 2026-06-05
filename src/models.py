from dataclasses import dataclass, field
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
    coverage_types: list[str] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    message: str = ""
    fallback_reason: str = ""


EXCEL_COLUMNS = [
    "用例编号",
    "模块",
    "用例标题",
    "优先级",
    "前置条件",
    "测试数据",
    "操作步骤",
    "预期结果",
    "用例类型",
    "功能点",
    "备注",
]


COLUMN_TO_FIELD = {
    "用例编号": "case_id",
    "模块": "module",
    "功能点": "feature",
    "用例标题": "title",
    "前置条件": "precondition",
    "测试数据": "test_data",
    "操作步骤": "steps",
    "预期结果": "expected_result",
    "优先级": "priority",
    "用例类型": "case_type",
    "备注": "remark",
}


FIELD_TO_COLUMN = {field: column for column, field in COLUMN_TO_FIELD.items()}
