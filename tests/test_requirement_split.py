from src.rule_based_generator import extract_requirement_items


def test_extract_requirement_items_splits_business_flow():
    text = "用户登录系统后查询订单，提交退款申请，客服审核通过后用户导出退款记录。"

    items = extract_requirement_items(text)
    features = [item.feature for item in items]

    assert len(items) >= 4
    assert "登录系统" in features
    assert "查询订单" in features
    assert "提交退款申请" in features
    assert "导出退款记录" in features


def test_extract_requirement_items_supports_numbered_list():
    text = "1. 用户登录系统\n2. 用户查询订单\n3. 客服审核退款"

    items = extract_requirement_items(text)

    assert len(items) == 3
    assert items[0].module == "账号登录"

