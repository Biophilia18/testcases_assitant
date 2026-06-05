from src.api_models import ApiDocument
from src.api_rule_generator import generate_api_cases


def _document() -> ApiDocument:
    return ApiDocument(
        project_name="智控家监测系统",
        module="设备控制",
        api_name="设备控制接口",
        method="POST",
        path="/api/devices/{deviceId}/control",
        auth="Bearer Token",
        headers="Authorization: Bearer token\nContent-Type: application/json",
        params="deviceId：设备ID，必填",
        body='{"action":"open"}',
        response_example='{"code":0,"message":"success"}',
        business_rules="设备在线才允许控制",
        db_checks="设备状态记录更新",
    )


def test_generate_api_cases_includes_auth_failure_when_auth_exists() -> None:
    cases = generate_api_cases(_document())

    assert any(case.case_type == "鉴权校验" and case.expected_status == "401" for case in cases)
    assert any(case.case_type == "权限校验" and case.expected_status == "403" for case in cases)


def test_generate_api_cases_includes_parameter_validation_when_request_data_exists() -> None:
    cases = generate_api_cases(_document())
    parameter_cases = [case for case in cases if case.case_type == "参数校验"]

    assert len(parameter_cases) >= 2
    assert any("必填参数" in case.remark for case in parameter_cases)
    assert any("错误类型" in case.remark or "错误类型" in case.steps for case in parameter_cases)


def test_generate_api_cases_includes_business_rule_case_when_rules_exist() -> None:
    cases = generate_api_cases(_document())

    business_case = next(case for case in cases if case.case_type == "业务规则")
    assert "设备在线才允许控制" in business_case.precondition
    assert business_case.expected_status == "400"


def test_generate_api_cases_includes_database_check_case_when_db_checks_exist() -> None:
    cases = generate_api_cases(_document())

    db_case = next(case for case in cases if case.case_type == "数据库校验")
    assert "设备状态记录更新" in db_case.expected_result
    assert db_case.expected_status == "200"


def test_generate_api_cases_ids_are_continuous() -> None:
    cases = generate_api_cases(_document())

    assert [case.case_id for case in cases] == [f"API-01-{index:02d}" for index in range(1, len(cases) + 1)]


def test_generate_api_cases_keeps_basic_cases_when_document_is_sparse() -> None:
    cases = generate_api_cases(ApiDocument(api_name="示例接口"))
    case_types = {case.case_type for case in cases}

    assert {"正常请求", "参数校验", "鉴权校验"}.issubset(case_types)
