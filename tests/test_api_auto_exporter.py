from src.api.api_auto_exporter import build_api_auto_preview_rows, build_api_auto_yaml
from src.api.models import ApiDocument, ApiTestCase


def _api_case() -> ApiTestCase:
    return ApiTestCase(
        case_id="API-01-01",
        case_title="正常请求-创建设备成功",
        module="设备管理",
        api_name="创建设备接口",
        method="POST",
        path="/api/devices",
        headers="Authorization: Bearer ${token}\nContent-Type: application/json",
        query_params="",
        request_body='{"name":"device-a","type":"sensor"}',
        precondition="已登录",
        steps="1. 构造请求\n2. 发送请求",
        expected_status="200",
        assertions="接口返回 success，并包含 id 字段",
        db_check="",
        extract_vars="deviceId: data.id",
        priority="P1",
        case_type="正常请求",
        remark="示例",
    )


def test_build_api_auto_yaml_contains_framework_fields() -> None:
    yaml_text = build_api_auto_yaml([_api_case()], ApiDocument())

    assert "feature: 设备管理" in yaml_text
    assert "story: 创建设备接口" in yaml_text
    assert "title: 正常请求-创建设备成功" in yaml_text
    assert "method: post" in yaml_text
    assert "url: /api/devices" in yaml_text
    assert "deviceId:" in yaml_text
    assert "状态码为200:" in yaml_text
    assert "响应包含success:" in yaml_text
    assert "响应包含id字段:" in yaml_text


def test_build_api_auto_preview_rows_marks_ready_cases() -> None:
    rows = build_api_auto_preview_rows([_api_case()])

    assert rows[0]["用例标题"] == "正常请求-创建设备成功"
    assert rows[0]["自动化就绪"] == "可导出"
