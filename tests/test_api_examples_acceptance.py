from src.api.api_auto_exporter import build_api_auto_yaml
from src.api.coverage_analyzer import build_api_coverage_matrix
from src.api.design_plan import build_api_design_plan
from src.api.document_parser import parse_api_document
from src.api.examples import API_EXAMPLE_DOCUMENTS
from src.api.rule_generator import generate_api_cases


def test_api_examples_parse_key_fields() -> None:
    documents = [parse_api_document(example.text) for example in API_EXAMPLE_DOCUMENTS]

    assert {
        "爱家政服务管理系统",
        "物资后勤管理系统",
        "智控家监测系统",
    }.issubset({document.project_name for document in documents})
    assert all(document.api_name for document in documents)
    assert {"GET", "POST", "PUT", "PATCH", "DELETE"}.issubset({document.method for document in documents})
    assert all(document.path.startswith("/api/") for document in documents)
    assert all("Bearer Token" in document.auth for document in documents)
    assert all(document.business_rules for document in documents)
    assert all(document.db_checks for document in documents)


def test_api_examples_generate_cases_and_non_empty_coverage() -> None:
    for example in API_EXAMPLE_DOCUMENTS:
        document = parse_api_document(example.text)
        plan = build_api_design_plan(document, strategy="标准")
        cases = generate_api_cases(document, plan_items=plan.plan_items)
        coverage_matrix = build_api_coverage_matrix(cases)

        assert cases, example.name
        assert len(cases) == plan.estimated_case_count
        assert any(item.covered for item in coverage_matrix)
        assert any(case.case_title for case in cases)


def test_api_examples_can_build_api_auto_yaml_preview() -> None:
    for example in API_EXAMPLE_DOCUMENTS:
        document = parse_api_document(example.text)
        cases = generate_api_cases(document)
        yaml_text = build_api_auto_yaml(cases, document)

        assert "feature:" in yaml_text
        assert "story:" in yaml_text
        assert "title:" in yaml_text
        assert "request:" in yaml_text
        assert "validate:" in yaml_text
