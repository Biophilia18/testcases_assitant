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

