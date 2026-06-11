from src.api.document_candidates import (
    api_document_candidates_to_rows,
    candidate_complexity_label,
    extract_api_document_candidates,
)


def _multi_interface_document() -> str:
    return """
项目/系统名称：爱家政服务管理系统
业务模块：预约管理

接口名称：创建服务预约接口
请求方法：POST
接口路径：/api/appointments
鉴权方式：Bearer Token
请求体：
{"serviceType":"cleaning"}
字段说明：
serviceType：服务类型，必填，string
contactPhone：联系电话，必填，string，手机号格式
业务规则：
预约时间不能早于当前时间
数据库校验：
预约主表生成预约记录

接口名称：取消服务预约接口
请求方法：POST
接口路径：/api/appointments/{appointmentNo}/cancel
鉴权方式：Bearer Token
请求参数：
appointmentNo：预约编号，必填，string，必须存在，必须属于当前用户
业务规则：
已完成的预约不能取消
"""


def _method_path_document_without_interface_names() -> str:
    return """
项目/系统名称：物资后勤管理系统
业务模块：物资领用申请

请求方法：POST
接口路径：/api/material/applications
鉴权方式：Bearer Token
请求体：
{"materialId":10001,"quantity":5}
字段说明：
materialId：物资ID，必填，integer，必须存在
quantity：领用数量，必填，integer，大于0，不能大于库存
业务规则：
领用数量不能大于当前库存

---
请求方法：GET
接口路径：/api/material/applications/{applicationNo}
鉴权方式：Bearer Token
请求参数：
applicationNo：申请编号，必填，string，必须存在
业务规则：
用户只能查看自己提交的申请
"""


def test_extract_api_document_candidates_from_multi_interface_document() -> None:
    candidates = extract_api_document_candidates(_multi_interface_document())

    assert len(candidates) == 2
    assert candidates[0].document.project_name == "爱家政服务管理系统"
    assert candidates[0].document.module == "预约管理"
    assert candidates[0].document.api_name == "创建服务预约接口"
    assert candidates[0].document.path == "/api/appointments"
    assert candidates[1].document.api_name == "取消服务预约接口"
    assert candidates[1].document.path == "/api/appointments/{appointmentNo}/cancel"
    assert "已完成的预约不能取消" in candidates[1].document.business_rules


def test_extract_api_document_candidates_from_method_path_document() -> None:
    candidates = extract_api_document_candidates(_method_path_document_without_interface_names())

    assert len(candidates) == 2
    assert candidates[0].document.project_name == "物资后勤管理系统"
    assert candidates[0].document.module == "物资领用申请"
    assert candidates[0].document.method == "POST"
    assert candidates[0].document.path == "/api/material/applications"
    assert candidates[1].document.method == "GET"
    assert candidates[1].document.path == "/api/material/applications/{applicationNo}"


def test_api_document_candidates_to_rows_contains_readability_fields() -> None:
    candidates = extract_api_document_candidates(_multi_interface_document())
    rows = api_document_candidates_to_rows(candidates)

    assert rows[0]["序号"] == 1
    assert rows[0]["接口名称"] == "创建服务预约接口"
    assert rows[0]["请求方法"] == "POST"
    assert rows[0]["参数数"] >= 2
    assert rows[0]["鉴权"] == "是"
    assert rows[0]["业务规则"] == "是"
    assert rows[0]["数据库校验"] == "是"
    assert rows[0]["复杂度"] == "中"
    assert "建议" in rows[0]


def test_candidate_complexity_label_marks_high_complexity() -> None:
    candidates = extract_api_document_candidates(
        """
接口名称：提交物资领用申请接口
请求方法：POST
接口路径：/api/material/applications
鉴权方式：Bearer Token
字段说明：
materialId：物资ID，必填，integer
quantity：领用数量，必填，integer
reason：申请原因，必填，string
departmentId：部门ID，必填，integer
receiverPhone：联系电话，必填，string，手机号格式
业务规则：
领用数量不能大于当前库存
数据库校验：
物资申请主表生成申请记录
"""
    )

    assert candidate_complexity_label(candidates[0].document) == "高"


def test_extract_api_document_candidates_keeps_single_interface_behavior() -> None:
    candidates = extract_api_document_candidates(
        """
接口名称：设备控制接口
请求方法：POST
接口路径：/api/devices/{deviceId}/control
"""
    )

    assert len(candidates) == 1
    assert candidates[0].document.api_name == "设备控制接口"


def test_extract_api_document_candidates_supports_head_and_options_methods() -> None:
    candidates = extract_api_document_candidates(
        """
请求方法：HEAD
接口路径：/api/files/{fileId}

---
HTTP Method：OPTIONS
URL：/api/files
"""
    )

    assert len(candidates) == 2
    assert candidates[0].document.method == "HEAD"
    assert candidates[0].document.path == "/api/files/{fileId}"
    assert candidates[1].document.method == "OPTIONS"
    assert candidates[1].document.path == "/api/files"
