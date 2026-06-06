from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class ApiTestCase:
    __test__: ClassVar[bool] = False

    case_id: str
    module: str
    api_name: str
    method: str
    path: str
    headers: str
    query_params: str
    request_body: str
    precondition: str
    steps: str
    expected_status: str
    assertions: str
    db_check: str
    extract_vars: str
    priority: str
    case_type: str
    remark: str


@dataclass
class ApiGenerationResult:
    cases: list[ApiTestCase]
    actual_mode: str
    case_count: int
    coverage_types: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class ApiDocument:
    project_name: str = ""
    module: str = ""
    api_name: str = ""
    method: str = ""
    path: str = ""
    auth: str = ""
    headers: str = ""
    params: str = ""
    body: str = ""
    response_example: str = ""
    business_rules: str = ""
    db_checks: str = ""


API_EXCEL_COLUMNS = [
    "用例编号",
    "模块",
    "接口名称",
    "请求方法",
    "接口路径",
    "请求头",
    "请求参数",
    "请求体",
    "前置条件",
    "操作步骤",
    "预期状态码",
    "断言点",
    "数据库校验",
    "变量提取",
    "优先级",
    "用例类型",
    "备注",
]


API_COLUMN_TO_FIELD = {
    "用例编号": "case_id",
    "模块": "module",
    "接口名称": "api_name",
    "请求方法": "method",
    "接口路径": "path",
    "请求头": "headers",
    "请求参数": "query_params",
    "请求体": "request_body",
    "前置条件": "precondition",
    "操作步骤": "steps",
    "预期状态码": "expected_status",
    "断言点": "assertions",
    "数据库校验": "db_check",
    "变量提取": "extract_vars",
    "优先级": "priority",
    "用例类型": "case_type",
    "备注": "remark",
}


API_FIELD_TO_COLUMN = {field: column for column, field in API_COLUMN_TO_FIELD.items()}
