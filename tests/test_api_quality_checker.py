from src.api.models import ApiDocument, ApiTestCase
from src.api.quality_checker import analyze_api_quality, api_quality_summary
from src.api.rule_generator import generate_api_cases


def _case(case_id: str = "API-01-01", case_type: str = "正常请求") -> ApiTestCase:
    return ApiTestCase(
        case_id=case_id,
        case_title="正常请求-设备控制成功",
        module="设备控制",
        api_name="设备控制接口",
        method="POST",
        path="/api/devices/{deviceId}/control",
        headers="Authorization: Bearer token",
        query_params="deviceId=10001",
        request_body='{"action":"open"}',
        precondition="准备有效 Token",
        steps="1. 构造合法请求\n2. 发送请求\n3. 查看响应",
        expected_status="200",
        assertions="接口返回成功，响应字段符合接口文档。",
        db_check="",
        extract_vars="",
        priority="P1",
        case_type=case_type,
        remark="正常请求",
    )


def test_analyze_api_quality_reports_empty_cases() -> None:
    issues = analyze_api_quality([])

    assert issues[0].category == "用例数量"
    assert issues[0].severity == "错误"


def test_analyze_api_quality_reports_required_field_issues() -> None:
    case = _case()
    case.api_name = ""
    case.expected_status = ""

    issues = analyze_api_quality([case])

    assert any(issue.category == "基础字段" and "接口名称" in issue.message for issue in issues)
    assert any(issue.category == "基础字段" and "预期状态码" in issue.message for issue in issues)


def test_analyze_api_quality_reports_document_driven_missing_checks() -> None:
    document = ApiDocument(
        auth="Bearer Token",
        business_rules="设备在线才允许控制",
        response_example='{"code":0}',
        db_checks="设备状态记录更新",
    )
    issues = analyze_api_quality([_case()], document)
    categories = {issue.category for issue in issues}

    assert "业务规则" in categories
    assert "数据库校验" in categories
    assert "权限校验" in categories


def test_analyze_api_quality_accepts_generated_api_cases() -> None:
    document = ApiDocument(
        module="设备控制",
        api_name="设备控制接口",
        method="POST",
        path="/api/devices/{deviceId}/control",
        auth="Bearer Token",
        params="deviceId：设备ID，必填",
        body='{"action":"open"}',
        response_example='{"code":0,"message":"success"}',
        business_rules="设备在线才允许控制",
        db_checks="设备状态记录更新",
    )
    cases = generate_api_cases(document)
    issues = analyze_api_quality(cases, document)

    assert not [issue for issue in issues if issue.severity == "错误"]
    assert not [issue for issue in issues if issue.category in {"业务规则", "数据库校验", "权限校验", "响应断言"}]


def test_api_quality_summary_counts_issue_levels() -> None:
    case = _case()
    case.assertions = "成功"
    issues = analyze_api_quality([case])
    summary = api_quality_summary([case], issues)

    assert summary["case_count"] == 1
    assert summary["issue_count"] == len(issues)
    assert summary["warning_count"] >= 1
