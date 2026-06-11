from src.export_review import build_export_review, export_review_summary, export_review_to_rows
from src.models import TestCase


def _case(**overrides) -> TestCase:
    data = {
        "case_id": "TC-01-01",
        "module": "预约管理",
        "feature": "创建预约",
        "title": "创建预约-正常流程",
        "precondition": "用户已登录",
        "test_data": "服务类型=保洁，预约时间=明天10:00",
        "steps": "1. 进入预约页面\n2. 填写预约信息\n3. 提交预约",
        "expected_result": "系统创建预约单并展示预约详情，预约状态为待派单。",
        "priority": "P1",
        "case_type": "功能测试",
        "remark": "覆盖类型：正常流程",
    }
    data.update(overrides)
    return TestCase(**data)


def test_build_export_review_reports_empty_cases() -> None:
    items = build_export_review([])
    summary = export_review_summary(items)

    assert summary["error_count"] == 1
    assert items[0].category == "用例数量"


def test_build_export_review_reports_uncovered_requirement_rule() -> None:
    requirement_text = "\n".join(
        [
            "验收标准：预约成功后生成唯一预约单号。",
            "补充规则/异常场景：重复点击提交按钮不能生成多条预约单。",
        ]
    )

    items = build_export_review([_case()], coverage_types=["正常流程"], requirement_text=requirement_text)
    rows = export_review_to_rows(items)

    assert any(item.category == "需求规则" for item in items)
    assert any("重复点击" in str(row["问题"]) for row in rows)


def test_build_export_review_suggests_duplicate_titles() -> None:
    cases = [
        _case(case_id="TC-01-01"),
        _case(case_id="TC-01-02", remark="覆盖类型：异常场景"),
    ]

    items = build_export_review(cases, coverage_types=["正常流程"])

    assert any(item.category == "用例标题" for item in items)
