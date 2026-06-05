from src.prompt_manager import load_prompt


def test_load_prompt_returns_functional_prompt():
    prompt = load_prompt("功能测试")

    assert "功能测试用例" in prompt
    assert "case_id" in prompt
