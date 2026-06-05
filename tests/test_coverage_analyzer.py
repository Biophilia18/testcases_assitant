from src.coverage_analyzer import build_coverage_matrix, coverage_matrix_to_rows
from src.models import TestCase


def _case(**overrides) -> TestCase:
    data = {
        "case_id": "TC-01-01",
        "module": "订单",
        "feature": "查询订单",
        "title": "查询订单-正常流程",
        "precondition": "用户已登录",
        "test_data": "订单号：A001",
        "steps": "1. 输入订单号\n2. 点击查询",
        "expected_result": "展示订单详情和订单状态",
        "priority": "P1",
        "case_type": "功能测试",
        "remark": "覆盖类型：正常流程",
    }
    data.update(overrides)
    return TestCase(**data)


def test_build_coverage_matrix_marks_covered_items():
    cases = [
        _case(),
        _case(case_id="TC-01-02", title="查询订单-无权限校验", remark="覆盖类型：权限控制"),
    ]

    matrix = build_coverage_matrix(cases, ["正常流程", "权限控制", "边界/非法输入"])
    by_type = {item.coverage_type: item for item in matrix}

    assert by_type["正常流程"].covered is True
    assert by_type["正常流程"].case_ids == ["TC-01-01"]
    assert by_type["权限控制"].covered is True
    assert by_type["边界/非法输入"].covered is False
    assert "补充边界值" in by_type["边界/非法输入"].suggestion


def test_build_coverage_matrix_handles_empty_case_list():
    matrix = build_coverage_matrix([], ["正常流程", "异常场景"])

    assert len(matrix) == 2
    assert all(not item.covered for item in matrix)
    assert matrix[0].case_ids == []


def test_coverage_matrix_to_rows_formats_result():
    matrix = build_coverage_matrix([_case()], ["正常流程", "异常场景"])

    rows = coverage_matrix_to_rows(matrix)

    assert rows[0]["覆盖项"] == "正常流程"
    assert rows[0]["是否覆盖"] == "是"
    assert rows[1]["是否覆盖"] == "否"


def test_precondition_permission_text_does_not_mark_permission_covered():
    case = _case(precondition="用户已登录且具备访问权限")

    matrix = build_coverage_matrix([case], ["权限控制"])

    assert matrix[0].covered is False
