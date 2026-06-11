from src.api.design_plan import build_api_plan_items
from src.api.models import ApiDocument
from src.api.reliability import (
    api_document_generation_blockers,
    api_document_reliability_level,
    assess_api_document_reliability,
)


def test_reliability_reports_generation_blockers_for_missing_method_and_path() -> None:
    document = ApiDocument(api_name="示例接口")

    blockers = api_document_generation_blockers(document)

    assert {issue.category for issue in blockers} == {"基础信息"}
    assert len(blockers) == 2
    assert api_document_reliability_level(blockers) == "低"


def test_reliability_warns_but_does_not_block_when_params_are_missing() -> None:
    document = ApiDocument(api_name="查询接口", method="GET", path="/api/items/{itemId}")

    issues = assess_api_document_reliability(document)

    assert not api_document_generation_blockers(document)
    assert any(issue.category == "参数信息" and issue.severity == "警告" for issue in issues)


def test_design_plan_does_not_include_param_case_when_params_are_unknown() -> None:
    document = ApiDocument(api_name="查询接口", method="GET", path="/api/items/{itemId}")

    items = build_api_plan_items(document, coverage_types=["参数校验"], strategy="标准")

    assert len(items) == 1
    assert items[0].coverage_type == "参数校验"
    assert items[0].included is False
    assert items[0].estimated_count == 0


def test_design_plan_does_not_create_auth_cases_without_auth_documentation() -> None:
    document = ApiDocument(api_name="公开查询接口", method="GET", path="/api/public/items")

    items = build_api_plan_items(document, coverage_types=["鉴权校验", "权限校验"], strategy="标准")

    assert items == []
