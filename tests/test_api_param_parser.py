from src.api.models import ApiDocument
from src.api.param_parser import parse_api_params


def test_parse_api_params_extracts_required_type_enum_length_and_range() -> None:
    document = ApiDocument(
        params="\n".join(
            [
                "deviceId：设备ID，必填，integer，范围大于0",
                "action：控制动作，必填，string，枚举 open、close、switch_mode",
                "contactPhone: 联系电话, 必填, string, 长度11位, 手机号格式",
                "remark：备注，选填，string，最大长度100",
            ]
        )
    )

    params = parse_api_params(document)
    by_name = {param.name: param for param in params}

    assert by_name["deviceId"].required is True
    assert by_name["deviceId"].param_type == "integer"
    assert "范围大于0" in by_name["deviceId"].rule
    assert by_name["action"].param_type == "string"
    assert "枚举" in by_name["action"].rule
    assert by_name["contactPhone"].required is True
    assert "长度11位" in by_name["contactPhone"].rule
    assert by_name["remark"].required is False


def test_parse_api_params_extracts_body_json_fields() -> None:
    document = ApiDocument(body='{"action":"open","count":1,"enabled":true}')

    params = parse_api_params(document)
    by_name = {param.name: param for param in params}

    assert by_name["action"].source == "body"
    assert by_name["action"].param_type == "string"
    assert by_name["count"].param_type == "integer"
    assert by_name["enabled"].param_type == "boolean"


def test_parse_api_params_supports_newline_list_and_dunhao() -> None:
    document = ApiDocument(params="- serviceType：服务类型、必填、string、允许值 cleaning、repair")

    params = parse_api_params(document)

    assert params[0].name == "serviceType"
    assert params[0].required is True
    assert params[0].param_type == "string"
    assert "允许值" in params[0].rule


def test_parse_api_params_merges_body_json_field_rules_from_field_descriptions() -> None:
    document = ApiDocument(
        params="action：控制动作，必填，允许值 open、close\nmode：工作模式，必填，允许值 auto、manual",
        body='{"action":"open","mode":"auto"}',
    )

    params = parse_api_params(document)
    by_name = {param.name: param for param in params}

    assert len([param for param in params if param.name == "action"]) == 1
    assert by_name["action"].source == "body"
    assert by_name["action"].param_type == "string"
    assert "允许值 open、close" in by_name["action"].rule


def test_parse_api_params_marks_path_parameters_from_path_template() -> None:
    document = ApiDocument(
        path="/api/appointments/{appointmentNo}",
        params="appointmentNo：预约编号，路径参数，必填，string，必须存在\nstatus：状态，查询参数，选填，string",
    )

    params = parse_api_params(document)
    by_name = {param.name: param for param in params}

    assert by_name["appointmentNo"].source == "path"
    assert by_name["status"].source == "query"


def test_parse_api_params_supports_markdown_table_fields() -> None:
    document = ApiDocument(
        path="/api/material/applications/{applicationNo}",
        params="""
| 参数名 | 类型 | 是否必填 | 说明 |
| --- | --- | --- | --- |
| applicationNo | string | 是 | 路径参数，必须存在，必须属于当前用户 |
| status | string | 否 | 查询参数，允许值 pending、approved、rejected |
| page | integer | 否 | 查询参数，大于0 |
""",
    )

    params = parse_api_params(document)
    by_name = {param.name: param for param in params}

    assert set(by_name) == {"applicationNo", "status", "page"}
    assert by_name["applicationNo"].source == "path"
    assert by_name["applicationNo"].required is True
    assert by_name["status"].source == "query"
    assert by_name["status"].required is False
    assert "允许值" in by_name["status"].rule
    assert by_name["page"].param_type == "integer"
