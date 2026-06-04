import json

from src.ai_client import _extract_json_array, _parse_cases


def test_extract_json_array_from_plain_text():
    raw = '说明文字 [{"case_id": "TC-001"}] 结束'

    assert _extract_json_array(raw) == '[{"case_id": "TC-001"}]'


def test_extract_json_array_from_markdown_block():
    raw = """```json
[
  {"case_id": "TC-001"}
]
```"""

    assert json.loads(_extract_json_array(raw))[0]["case_id"] == "TC-001"


def test_parse_cases_supports_new_fields():
    raw = """[
      {
        "case_id": "TC-01-01",
        "module": "订单",
        "feature": "查询订单",
        "title": "查询订单-正常流程",
        "precondition": "用户已登录",
        "test_data": "订单号",
        "steps": "1. 输入订单号",
        "expected_result": "展示订单详情",
        "priority": "P1",
        "case_type": "功能测试",
        "remark": "AI生成"
      }
    ]"""

    cases = _parse_cases(raw)

    assert cases[0].case_id == "TC-01-01"
    assert cases[0].test_data == "订单号"
    assert cases[0].remark == "AI生成"


def test_parse_cases_converts_step_list_to_multiline_text():
    raw = """[
      {
        "case_id": "TC-01-01",
        "module": "登录",
        "feature": "登录系统",
        "title": "登录系统-正常流程",
        "precondition": "用户打开登录页",
        "test_data": ["账号 test_user", "密码 correct123"],
        "steps": ["打开登录页面", "输入用户名 test_user", "输入密码 correct123", "点击登录按钮"],
        "expected_result": "登录成功",
        "priority": "P1",
        "case_type": "功能测试",
        "remark": "AI生成"
      }
    ]"""

    cases = _parse_cases(raw)

    assert cases[0].steps == "1. 打开登录页面\n2. 输入用户名 test_user\n3. 输入密码 correct123\n4. 点击登录按钮"
    assert cases[0].test_data == "账号 test_user；密码 correct123"
