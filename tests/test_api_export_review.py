from src.api.export_review import build_api_export_review, api_export_review_summary, api_export_review_to_rows
from src.api.models import ApiDocument, ApiTestCase


def _case(**overrides) -> ApiTestCase:
    data = {
        "case_id": "API-01-01",
        "case_title": "正常请求-创建预约成功",
        "module": "预约管理",
        "api_name": "创建预约接口",
        "method": "POST",
        "path": "/api/appointments",
        "headers": "Authorization: Bearer ${token}\nContent-Type: application/json",
        "query_params": "",
        "request_body": '{"serviceType":"cleaning","appointmentTime":"2026-06-12 10:00"}',
        "precondition": "准备有效 Token",
        "steps": "1. 构造合法请求\n2. 发送请求\n3. 查看响应",
        "expected_status": "200",
        "assertions": "断言 status_code=200，code=0，返回 appointmentId。",
        "db_check": "",
        "extract_vars": "appointmentId: data.appointmentId",
        "priority": "P1",
        "case_type": "正常请求",
        "remark": "正常请求",
    }
    data.update(overrides)
    return ApiTestCase(**data)


def test_build_api_export_review_reports_empty_cases() -> None:
    items = build_api_export_review([], ApiDocument())
    summary = api_export_review_summary(items)

    assert summary["error_count"] == 1
    assert items[0].category == "用例数量"


def test_build_api_export_review_reports_document_and_quality_risks() -> None:
    case = _case(api_name="", expected_status="", assertions="")
    document = ApiDocument(method="POST", path="/api/appointments")

    items = build_api_export_review([case], document)
    rows = api_export_review_to_rows(items)

    assert any(item.severity == "错误" for item in items)
    assert any("接口名称" in str(row["问题"]) for row in rows)
    assert any("预期状态码" in str(row["问题"]) for row in rows)


def test_build_api_export_review_reports_token_and_db_review_items() -> None:
    document = ApiDocument(
        api_name="创建预约接口",
        method="POST",
        path="/api/appointments",
        auth="Bearer Token",
        db_checks="预约记录写入数据库",
    )
    cases = [
        _case(),
        _case(case_id="API-01-02", case_type="数据库校验", db_check="检查预约记录已写入", remark="数据库校验"),
    ]

    items = build_api_export_review(cases, document)

    assert any(item.category == "运行数据" for item in items)
    assert any(item.category == "数据库校验" for item in items)


def test_build_api_export_review_reports_weak_assertion() -> None:
    items = build_api_export_review([_case(assertions="成功")], ApiDocument(method="POST", path="/api/appointments"))

    assert any(item.category == "响应断言" and item.severity == "警告" for item in items)
