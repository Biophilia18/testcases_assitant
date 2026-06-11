from src.models import TestCase
from src.requirement_trace import build_requirement_trace, requirement_trace_summary, requirement_trace_to_rows


def _case(case_id: str, title: str, steps: str, expected: str, case_type: str = "功能测试") -> TestCase:
    return TestCase(
        case_id=case_id,
        module="服务预约管理",
        feature="服务预约",
        title=title,
        precondition="用户已登录",
        test_data="正常业务数据",
        steps=steps,
        expected_result=expected,
        priority="P1",
        case_type=case_type,
        remark="功能测试规则生成；建议人工复核。",
    )


def test_build_requirement_trace_tracks_acceptance_and_constraint_items() -> None:
    requirement_text = """
业务流程/需求描述：用户提交服务预约。
验收标准：
1. 预约创建成功后生成唯一预约单号。
2. 页面状态正确更新。
补充规则/异常场景：
- 重复提交不得产生多条预约单。
- 无权限用户不能创建预约。
"""
    cases = [
        _case(
            "TC-01-01",
            "服务预约-正常流程",
            "1. 用户填写预约信息\n2. 提交预约",
            "预约创建成功，生成唯一预约单号，页面状态更新。",
        ),
        _case(
            "TC-01-02",
            "服务预约-重复提交",
            "1. 用户连续重复点击提交",
            "系统不产生多条预约单。",
            case_type="异常测试",
        ),
        _case(
            "TC-01-03",
            "服务预约-权限校验",
            "1. 使用无权限用户提交预约",
            "系统拒绝访问。",
            case_type="权限测试",
        ),
    ]

    trace_items = build_requirement_trace(cases, requirement_text)
    rows = requirement_trace_to_rows(trace_items)
    summary = requirement_trace_summary(trace_items)

    assert summary == {"total": 4, "covered": 4, "missing": 0}
    assert rows[0]["来源"] == "验收标准"
    assert rows[0]["是否覆盖"] == "是"
    assert rows[0]["命中用例"] == "TC-01-01"
    assert rows[-1]["来源"] == "补充规则/异常场景"
    assert rows[-1]["命中用例"] == "TC-01-03"


def test_build_requirement_trace_reports_missing_rules() -> None:
    requirement_text = """
验收标准：
1. 控制结果与数据库设备状态记录一致。
补充规则/异常场景：
1. 接口超时时页面不能误显示控制成功。
"""
    cases = [
        _case(
            "TC-01-01",
            "设备控制-正常流程",
            "1. 用户点击控制按钮",
            "设备状态更新。",
        )
    ]

    trace_items = build_requirement_trace(cases, requirement_text)

    assert requirement_trace_summary(trace_items)["missing"] == 2
    missing_rows = [row for row in requirement_trace_to_rows(trace_items) if row["是否覆盖"] == "否"]
    assert missing_rows
    assert "建议" in missing_rows[0]
