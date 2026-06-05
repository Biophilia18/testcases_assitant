from __future__ import annotations

from pathlib import Path


PROMPT_DIR = Path("prompts")
FUNCTIONAL_PROMPT_PATH = PROMPT_DIR / "functional.md"


FALLBACK_FUNCTIONAL_PROMPT = """你是资深软件测试工程师。请根据需求文本生成结构化功能测试用例。
只返回 JSON 数组。每个对象包含 case_id, module, feature, title, precondition, test_data, steps, expected_result, priority, case_type, remark。
"""


def load_prompt(generation_type: str) -> str:
    if generation_type != "功能测试":
        generation_type = "功能测试"

    if FUNCTIONAL_PROMPT_PATH.exists():
        return FUNCTIONAL_PROMPT_PATH.read_text(encoding="utf-8")

    return FALLBACK_FUNCTIONAL_PROMPT

