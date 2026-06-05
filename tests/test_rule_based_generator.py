from src.rule_based_generator import generate_rule_based_cases


def test_rule_based_generator_adds_new_fields():
    cases = generate_rule_based_cases("用户登录系统后查询订单", cases_per_feature=3, generation_type="功能测试")

    assert len(cases) >= 6
    assert cases[0].case_id.startswith("TC-")
    assert cases[0].test_data
    assert cases[0].remark


def test_rule_based_generator_uses_generation_type():
    cases = generate_rule_based_cases("查询订单接口", cases_per_feature=3, generation_type="接口测试")

    assert cases[0].case_type == "接口测试"
    assert "接口" in cases[0].title


def test_rule_based_generator_uses_short_feature_name_and_keeps_description_in_steps():
    cases = generate_rule_based_cases(
        "用户点击控制按钮后，App 向服务端发送控制指令，服务端返回处理结果",
        cases_per_feature=3,
        generation_type="功能测试",
    )

    assert cases[0].feature == "控制指令发送"
    assert cases[0].title == "控制指令发送-正常流程"
    assert "服务端返回处理结果" in cases[0].steps


def test_rule_based_generator_uses_selected_coverage_types():
    cases = generate_rule_based_cases(
        "用户点击控制按钮后，App 向服务端发送控制指令，服务端返回处理结果",
        cases_per_feature=6,
        generation_type="功能测试",
        coverage_types=["正常流程", "弱网/超时"],
    )

    assert len(cases) == 2
    assert "覆盖：正常流程" in cases[0].remark
    assert "覆盖：弱网/超时" in cases[1].remark
