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

