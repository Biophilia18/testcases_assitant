from src.rule_based_generator import extract_requirement_items


def test_extract_requirement_items_splits_business_flow():
    text = "用户登录系统后查询订单，提交退款申请，客服审核通过后用户导出退款记录。"

    items = extract_requirement_items(text)
    descriptions = [item.description for item in items]

    assert len(items) >= 4
    assert any("登录系统" in description for description in descriptions)
    assert any("查询订单" in description for description in descriptions)
    assert any("提交退款申请" in description for description in descriptions)
    assert any("导出退款记录" in description for description in descriptions)


def test_extract_requirement_items_supports_numbered_list():
    text = "1. 用户登录系统\n2. 用户查询订单\n3. 客服审核退款"

    items = extract_requirement_items(text)

    assert len(items) == 3
    assert items[0].module == "账号登录"


def test_extract_requirement_items_keeps_long_feature_text():
    text = "用户点击控制按钮后，App 向服务端发送控制指令，服务端返回处理结果"

    items = extract_requirement_items(text)

    assert items[0].module == "设备控制"
    assert items[0].feature == "控制指令发送"
    assert "服务端返回处理结果" in items[0].description
