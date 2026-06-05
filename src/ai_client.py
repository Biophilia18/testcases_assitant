from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from src.env_loader import load_env_file
from src.models import GenerationResult, TestCase
from src.prompt_manager import load_prompt
from src.rule_based_generator import extract_requirement_items, generate_rule_based_cases
from src.text_utils import normalize_steps


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
    generation_type: str = "功能测试",
) -> GenerationResult:
    load_env_file()
    requested_mode = mode

    if mode == "AI 生成":
        return _generate_with_ai_or_fallback(
            requirement_text=requirement_text,
            requested_mode=requested_mode,
            cases_per_feature=cases_per_feature,
            provider=provider,
            generation_type=generation_type,
        )

    cases = generate_rule_based_cases(requirement_text, cases_per_feature, generation_type)
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
    generation_type: str,
) -> GenerationResult:
    config = _get_provider_config(provider)
    api_key = os.getenv(config.api_key_env)
    local_feature_count = len(extract_requirement_items(requirement_text))

    if not api_key:
        cases = generate_rule_based_cases(requirement_text, cases_per_feature, generation_type)
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
        f"用例生成类型：{generation_type}。"
        f"如需求包含多个业务节点，请先拆分节点再分别生成。\n\n需求：\n{requirement_text}"
    )

    try:
        raw_text = _call_chat_completion(
            config=config,
            api_key=api_key,
            model=model,
            user_prompt=user_prompt,
            generation_type=generation_type,
        )
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
        cases = generate_rule_based_cases(requirement_text, cases_per_feature, generation_type)
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


def _call_chat_completion(
    config: ProviderConfig,
    api_key: str,
    model: str,
    user_prompt: str,
    generation_type: str,
) -> str:
    from openai import OpenAI

    client_kwargs = {"api_key": api_key}
    if config.default_base_url:
        client_kwargs["base_url"] = os.getenv(config.base_url_env, config.default_base_url)

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _build_system_prompt(generation_type)},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("AI response is empty.")
    return content


def _build_system_prompt(generation_type: str) -> str:
    return load_prompt(generation_type)


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
                case_id=str(item.get("case_id", f"TC-{len(cases) + 1:03d}")).strip(),
                module=_field_text(item.get("module", "")),
                feature=_field_text(item.get("feature", "")),
                title=_field_text(item.get("title", "")),
                precondition=_field_text(item.get("precondition", "")),
                test_data=_field_text(item.get("test_data", "")),
                steps=normalize_steps(item.get("steps", "")),
                expected_result=_field_text(item.get("expected_result", "")),
                priority=_field_text(item.get("priority", "P2")),
                case_type=_field_text(item.get("case_type", "功能测试")),
                remark=_field_text(item.get("remark", "")),
            )
        )

    return [case for case in cases if case.title and case.steps and case.expected_result]


def _field_text(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value or "").strip()


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
