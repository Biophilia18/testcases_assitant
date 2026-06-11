from src.api.document_parser import api_document_to_fields, fields_to_api_document, parse_api_document
from pathlib import Path


def test_parse_api_document_by_titles() -> None:
    text = """
项目/系统名称：智控家监测系统
业务模块：基础设备控制
接口名称：设备控制接口
请求方法：post
接口路径：/api/devices/{deviceId}/control
鉴权方式：Bearer Token
请求头：
- Authorization: Bearer token
- Content-Type: application/json
请求参数：
1. deviceId：设备ID，必填
字段说明：
- action：控制动作，必填
请求体：
{"action":"open"}
成功响应：
{"code":0,"message":"success"}
失败响应：
{"code":400,"message":"deviceId required"}
业务规则：
- 设备在线才允许控制
- 用户必须具备设备权限
数据库校验：
1. 设备状态记录更新
2. 控制日志写入
"""

    document = parse_api_document(text)

    assert document.project_name == "智控家监测系统"
    assert document.module == "基础设备控制"
    assert document.api_name == "设备控制接口"
    assert document.method == "POST"
    assert document.path == "/api/devices/{deviceId}/control"
    assert "Authorization" in document.headers
    assert "deviceId" in document.params
    assert "action" in document.params
    assert document.body == '{"action":"open"}'
    assert "success" in document.response_example
    assert "deviceId required" in document.response_example
    assert "设备在线才允许控制" in document.business_rules
    assert "设备状态记录更新" in document.db_checks


def test_parse_api_document_supports_markdown_titles_and_list_markers() -> None:
    text = """
### 项目名称：家政服务管理系统
### 模块：预约管理
### 接口名称：创建预约
### 请求方法：GET
### URL：/api/appointments
### 业务规则：
- 服务类型不能为空
2. 预约时间不能早于当前时间
"""

    document = parse_api_document(text)

    assert document.project_name == "家政服务管理系统"
    assert document.module == "预约管理"
    assert document.method == "GET"
    assert document.path == "/api/appointments"
    assert document.business_rules.splitlines() == ["服务类型不能为空", "预约时间不能早于当前时间"]


def test_parse_api_document_supports_common_title_aliases() -> None:
    text = """
项目名称：物资后勤管理系统
模块：申请查询
接口名称：查询申请详情
请求方式：get
接口地址：/api/material/applications/{applicationNo}
鉴权：Bearer Token
请求入参：
applicationNo：申请编号，必填，string，必须存在
返回示例：
{"code":0,"data":{"applicationNo":"WL202606090001"}}
错误码：
404 application not found
数据库校验：
查询接口不应修改数据
"""

    document = parse_api_document(text)

    assert document.project_name == "物资后勤管理系统"
    assert document.method == "GET"
    assert document.path == "/api/material/applications/{applicationNo}"
    assert "applicationNo" in document.params
    assert "application not found" in document.response_example
    assert "不应修改数据" in document.db_checks


def test_parse_empty_api_document_returns_empty_model() -> None:
    document = parse_api_document("")

    assert api_document_to_fields(document) == {
        "project_name": "",
        "module": "",
        "api_name": "",
        "method": "",
        "path": "",
        "auth": "",
        "headers": "",
        "params": "",
        "body": "",
        "response_example": "",
        "business_rules": "",
        "db_checks": "",
    }


def test_api_document_fields_round_trip_and_normalize_method() -> None:
    document = fields_to_api_document(
        {
            "project_name": " 智控家监测系统 ",
            "module": " 设备控制 ",
            "api_name": " 控制接口 ",
            "method": " patch ",
            "path": " /api/control ",
            "auth": " token ",
            "headers": " Authorization ",
            "params": " deviceId ",
            "body": " {} ",
            "response_example": " 200 ",
            "business_rules": " 在线 ",
            "db_checks": " 状态更新 ",
        }
    )

    fields = api_document_to_fields(document)

    assert fields["project_name"] == "智控家监测系统"
    assert fields["method"] == "PATCH"
    assert fields["path"] == "/api/control"
    assert fields["db_checks"] == "状态更新"


def test_parse_api_document_skips_markdown_code_fences() -> None:
    text = """
请求体：
```json
{"name":"demo"}
```
成功响应：
```json
{"code":0}
```
"""

    document = parse_api_document(text)

    assert "```" not in document.body
    assert "```" not in document.response_example
    assert '{"name":"demo"}' in document.body
    assert '{"code":0}' in document.response_example


def test_parse_api_document_examples() -> None:
    root = Path(__file__).resolve().parents[1]
    markdown_document = parse_api_document((root / "examples/api_smart_home_device_control.md").read_text(encoding="utf-8"))
    text_document = parse_api_document((root / "examples/api_housekeeping_appointment.txt").read_text(encoding="utf-8"))

    assert markdown_document.project_name == "智控家监测系统"
    assert markdown_document.method == "POST"
    assert "/api/devices/{deviceId}/control" == markdown_document.path
    assert "设备必须在线才允许控制" in markdown_document.business_rules
    assert "设备状态记录更新" in markdown_document.db_checks
    assert text_document.project_name == "爱家政服务管理系统"
    assert text_document.api_name == "创建服务预约接口"
    assert text_document.method == "POST"
    assert "预约主表生成预约记录" in text_document.db_checks
