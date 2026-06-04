from __future__ import annotations

import json
import os
from dataclasses import dataclass

from src.env_loader import load_env_file
from src.models import GenerationResult, TestCase
from src.rule_based_generator import extract_requirement_items, generate_rule_based_cases


SYSTEM_PROMPT = """你是资深软件测试工程师。请根据需求文本生成结构化测试用例。

要求：
1. 先识别完整业务流程，把登录、查询、提交、审核、导出、支付、退款等业务节点拆成独立功能点，不要把整段流程当成一个功能。
2. 每个功能点至少生成正常流程、异常输入、边界值、权限、重复操作或状态流转相关用例。
3. 用例要覆盖输入校验、状态变化、数据一致性、权限控制和关键异常路径。
4. 只返回 JSON 数组，不要返回 Markdown、解释文字或代码块。

每个对象必须包含这些字段：
module, feature, title, precondition, steps, expected_result, priority, case_type。

priority 只能使用 P0、P1、P2、P3。
case_type 使用功能测试、异常测试、边界测试、权限测试、流程测试、接口测试中的合适值。
"""


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key_env: str
    model_env: str
    default_model: str
    base_url_env: str = ""
    default_base_url: str = ""


PROVIDERS = {
    "OpenAI": ProviderConfig(
        name="OpenAI",
        api_key_env="OPENAI_API_KEY",
        model_env="OPENAI_MODEL",
        default_model="gpt-4.1-mini",
    ),
    "DeepSeek": ProviderConfig(
        name="DeepSeek",
        api_key_env="DEEPSEEK_API_KEY",
        model_env="DEEPSEEK_MODEL",
        default_model="deepseek-v4-flash",
        base_url_env="DEEPSEEK_BASE_URL",
        default_base_url="https://api.deepseek.com",
    ),
}


def generate_cases(
    requirement_text: str,
    mode: str,
    cases_per_feature: int = 6,
    provider: str = "OpenAI",
) -> GenerationResult:
    load_env_file()
    requested_mode = mode

    if mode == "AI 生成":
        return _generate_with_ai_or_fallback(
            requirement_text=requirement_text,
            requested_mode=requested_mode,
            cases_per_feature=cases_per_feature,
            provider=provider,
        )

    cases = generate_rule_based_cases(requirement_text, cases_per_feature)
    feature_count = len(extract_requirement_items(requirement_text))
    return GenerationResult(
        cases=cases,
        requested_mode=requested_mode,
        actual_mode="规则生成",
        provider="规则生成",
        feature_count=feature_count,
        case_count=len(cases),
        message=f"规则生成完成：识别到 {feature_count} 个功能点，生成 {len(cases)} 条测试用例。",
    )


def is_provider_configured(provider: str) -> bool:
    load_env_file()
    config = _get_provider_config(provider)
    return bool(os.getenv(config.api_key_env))


def is_openai_configured() -> bool:
    return is_provider_configured("OpenAI")


def is_deepseek_configured() -> bool:
    return is_provider_configured("DeepSeek")


def _generate_with_ai_or_fallback(
    requirement_text: str,
    requested_mode: str,
    cases_per_feature: int,
    provider: str,
) -> GenerationResult:
    config = _get_provider_config(provider)
    api_key = os.getenv(config.api_key_env)
    local_feature_count = len(extract_requirement_items(requirement_text))

    if not api_key:
        cases = generate_rule_based_cases(requirement_text, cases_per_feature)
        return GenerationResult(
            cases=cases,
            requested_mode=requested_mode,
            actual_mode="规则生成",
            provider=config.name,
            feature_count=local_feature_count,
            case_count=len(cases),
            message=f"未检测到 {config.api_key_env}，已使用规则生成。",
            fallback_reason=f"missing_api_key: {config.api_key_env}",
        )

    model = os.getenv(config.model_env, config.default_model)
    target_count = max(local_feature_count * cases_per_feature, cases_per_feature)
    user_prompt = (
        f"请基于以下需求生成不少于 {target_count} 条测试用例。"
        f"如需求包含多个业务节点，请先拆分节点再分别生成。\n\n需求：\n{requirement_text}"
    )

    try:
        raw_text = _call_chat_completion(config=config, api_key=api_key, model=model, user_prompt=user_prompt)
        cases = _parse_cases(raw_text)
        feature_count = len({f"{case.module}:{case.feature}" for case in cases})
        return GenerationResult(
            cases=cases,
            requested_mode=requested_mode,
            actual_mode=f"AI 生成（{config.name}）",
            provider=config.name,
            feature_count=feature_count,
            case_count=len(cases),
            model=model,
            message=f"AI 生成完成：供应商 {config.name}，模型 {model}，返回 {len(cases)} 条测试用例，覆盖 {feature_count} 个功能点。",
        )
    except Exception as exc:
        cases = generate_rule_based_cases(requirement_text, cases_per_feature)
        reason = f"{type(exc).__name__}: {exc}"
        return GenerationResult(
            cases=cases,
            requested_mode=requested_mode,
            actual_mode="规则生成",
            provider=config.name,
            feature_count=local_feature_count,
            case_count=len(cases),
            model=model,
            message=f"{config.name} 调用失败，已回退到规则生成。",
            fallback_reason=reason[:500],
        )


def _call_chat_completion(config: ProviderConfig, api_key: str, model: str, user_prompt: str) -> str:
    from openai import OpenAI

    client_kwargs = {"api_key": api_key}
    if config.default_base_url:
        client_kwargs["base_url"] = os.getenv(config.base_url_env, config.default_base_url)

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("AI response is empty.")
    return content


def _get_provider_config(provider: str) -> ProviderConfig:
    return PROVIDERS.get(provider, PROVIDERS["OpenAI"])


def _parse_cases(raw_text: str) -> list[TestCase]:
    data = json.loads(_extract_json_array(raw_text))
    if not isinstance(data, list):
        raise ValueError("AI response must be a JSON array.")

    cases: list[TestCase] = []
    for item in data:
        cases.append(
            TestCase(
                module=str(item.get("module", "")).strip(),
                feature=str(item.get("feature", "")).strip(),
                title=str(item.get("title", "")).strip(),
                precondition=str(item.get("precondition", "")).strip(),
                steps=str(item.get("steps", "")).strip(),
                expected_result=str(item.get("expected_result", "")).strip(),
                priority=str(item.get("priority", "P2")).strip(),
                case_type=str(item.get("case_type", "功能测试")).strip(),
            )
        )

    return [case for case in cases if case.title and case.steps and case.expected_result]


def _extract_json_array(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json").strip()

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("AI response does not contain a JSON array.")

    return text[start : end + 1]
