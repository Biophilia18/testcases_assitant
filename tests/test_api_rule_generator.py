from src.api.models import ApiDocument
from src.api.rule_generator import generate_api_cases


def _document() -> ApiDocument:
    return ApiDocument(
        project_name="智控家监测系统",
        module="设备控制",
        api_name="设备控制接口",
        method="POST",
        path="/api/devices/{deviceId}/control",
        auth="Bearer Token",
        headers="Authorization: Bearer token\nContent-Type: application/json",
        params="deviceId：设备ID，必填，integer，范围大于0",
        body='{"action":"open","mode":"auto"}',
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


def test_generate_api_cases_includes_param_level_empty_type_and_boundary_cases() -> None:
    cases = generate_api_cases(_document())

    assert any("deviceId" in case.remark and "为空" in case.remark for case in cases)
    assert any("deviceId" in case.remark and "类型错误" in case.remark for case in cases)
    assert any("deviceId" in case.remark and "边界" in case.remark for case in cases)


def test_generate_api_cases_keeps_body_fields_out_of_query_params_when_duplicated() -> None:
    cases = generate_api_cases(_document())
    normal_case = cases[0]

    assert "deviceId" in normal_case.query_params
    assert "action" not in normal_case.query_params
    assert "mode" not in normal_case.query_params
    assert "action" in normal_case.request_body


def test_generate_api_cases_includes_business_rule_case_when_rules_exist() -> None:
    cases = generate_api_cases(_document())

    business_case = next(case for case in cases if case.case_type == "业务规则")
    assert "设备在线才允许控制" in business_case.precondition
    assert business_case.expected_status == "400"


def test_generate_api_cases_includes_database_check_case_when_db_checks_exist() -> None:
    cases = generate_api_cases(_document())

    db_case = next(case for case in cases if case.case_type == "数据库校验")
    assert "设备状态记录更新" in db_case.db_check
    assert db_case.expected_status == "200"


def test_generate_api_cases_ids_are_continuous() -> None:
    cases = generate_api_cases(_document())

    assert [case.case_id for case in cases] == [f"API-01-{index:02d}" for index in range(1, len(cases) + 1)]


def test_generate_api_cases_keeps_basic_cases_when_document_is_sparse() -> None:
    cases = generate_api_cases(ApiDocument(api_name="示例接口"))
    case_types = {case.case_type for case in cases}

    assert {"正常请求", "参数校验", "鉴权校验"}.issubset(case_types)


def test_generate_api_cases_respects_selected_coverage_types() -> None:
    cases = generate_api_cases(_document(), coverage_types=["正常请求", "业务规则"], business_rules=["设备在线才允许控制"])
    case_types = {case.case_type for case in cases}

    assert case_types == {"正常请求", "业务规则"}
    assert all("参数" not in case.case_type for case in cases)


def test_generate_api_cases_respects_compact_strategy() -> None:
    cases = generate_api_cases(_document(), coverage_types=["参数校验"], strategy="精简")

    assert len(cases) <= 3
    assert all(case.case_type in {"参数校验", "边界值"} for case in cases)
