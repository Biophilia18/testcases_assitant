from src.models import TestCase
from src.regeneration import (
    build_regeneration_requirement,
    coverage_types_for_focus,
    replace_group_preserving_case_ids,
)


def _case(case_id: str, module: str = "设备控制", feature: str = "设备基础控制") -> TestCase:
    return TestCase(
        case_id=case_id,
        module=module,
        feature=feature,
        title=f"{feature}-正常流程",
        precondition="用户已登录",
        test_data="正常数据",
        steps="1. 打开页面\n2. 执行操作",
        expected_result="页面状态正确更新",
        priority="P1",
        case_type="功能测试",
        remark="示例",
    )


def test_build_regeneration_requirement_contains_full_context_and_focus():
    text = build_regeneration_requirement(
        "设备控制 / 设备基础控制",
        [_case("TC-01-01")],
        "完整需求上下文",
        "异常场景",
    )

    assert "重新生成侧重点：异常场景" in text
    assert "完整需求上下文" in text
    assert "TC-01-01 设备基础控制-正常流程" in text


def test_coverage_types_for_focus_uses_focused_mapping():
    assert coverage_types_for_focus("权限场景", ["正常流程"]) == ["权限控制"]
    assert coverage_types_for_focus("综合补全", ["正常流程"]) == ["正常流程"]


def test_replace_group_preserving_case_ids_keeps_group_prefix_and_position():
    current_cases = [
        _case("TC-01-01", feature="设备基础控制"),
        _case("TC-01-02", feature="设备基础控制"),
        _case("TC-02-01", feature="失败提示"),
    ]
    regenerated = [
        _case("TC-99-01", feature="设备基础控制"),
        _case("TC-99-02", feature="设备基础控制"),
        _case("TC-99-03", feature="设备基础控制"),
    ]

    merged = replace_group_preserving_case_ids(current_cases, "设备控制 / 设备基础控制", regenerated)

    assert [case.case_id for case in merged] == ["TC-01-01", "TC-01-02", "TC-01-03", "TC-02-01"]
    assert merged[-1].feature == "失败提示"
