from __future__ import annotations

import streamlit as st

from src.ai_client import generate_cases, is_provider_configured
from src.exporter import build_excel
from src.models import EXCEL_COLUMNS, GenerationResult, TestCase


# Streamlit 会读取这个 Python 文件，并把 st.xxx 调用渲染成本地网页控件。
st.set_page_config(page_title="AI 测试用例助手", layout="wide")


def main() -> None:
    st.title("AI 辅助测试用例生成与导出工具")

    # sidebar 是页面左侧配置栏，适合放模式选择、模型配置等非主流程内容。
    with st.sidebar:
        mode = st.radio("生成方式", ["规则生成", "AI 生成"], index=0)
        provider = st.radio("AI 服务商", ["DeepSeek", "OpenAI"], index=0)
        cases_per_feature = st.slider("每个功能点生成用例数", min_value=3, max_value=8, value=6)

        if is_provider_configured(provider):
            st.success(f"已检测到 {provider} API Key。")
        else:
            env_name = "DEEPSEEK_API_KEY" if provider == "DeepSeek" else "OPENAI_API_KEY"
            st.info(f"未检测到 {env_name}，AI 生成会自动回退到规则生成。")

        if provider == "DeepSeek":
            st.caption("DeepSeek 默认使用 DEEPSEEK_MODEL=deepseek-v4-flash。")

    # text_area 是多行文本输入框，用来粘贴需求说明。
    requirement_text = st.text_area(
        "需求文本",
        height=300,
        placeholder="请粘贴需求说明、用户故事、功能描述或验收标准。支持一整段业务流程，也支持编号列表。",
    )

    # button 返回 True 时，表示用户刚刚点击了按钮。
    generate_clicked = st.button("生成测试用例", type="primary")

    if generate_clicked:
        if not requirement_text.strip():
            st.warning("请先输入需求文本。")
            return

        # spinner 会在耗时操作期间显示“正在处理”的提示。
        with st.spinner("正在生成测试用例..."):
            # session_state 用来保存本次生成结果，避免页面刷新后立刻丢失。
            st.session_state["generation_result"] = generate_cases(
                requirement_text=requirement_text,
                mode=mode,
                cases_per_feature=cases_per_feature,
                provider=provider,
            )

    result: GenerationResult | None = st.session_state.get("generation_result")
    if not result or not result.cases:
        return

    _render_generation_status(result)

    st.subheader("测试用例预览")
    # dataframe 把 Python 数据列表渲染成可滚动、可复制的表格。
    st.dataframe(_to_table(result.cases), use_container_width=True, hide_index=True)

    excel_bytes = build_excel(result.cases)
    # download_button 会把内存里的 Excel 二进制内容作为文件下载给用户。
    st.download_button(
        "导出 Excel",
        data=excel_bytes,
        file_name="测试用例.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _render_generation_status(result: GenerationResult) -> None:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("实际生成方式", result.actual_mode)
    col2.metric("服务商", result.provider or "-")
    col3.metric("识别功能点", result.feature_count)
    col4.metric("测试用例数", result.case_count)
    col5.metric("模型", result.model or "-")

    if result.actual_mode.startswith("AI 生成"):
        st.success(result.message)
    elif result.fallback_reason:
        st.warning(result.message)
        with st.expander("回退原因"):
            st.code(result.fallback_reason)
    else:
        st.info(result.message)


def _to_table(cases: list[TestCase]) -> list[dict[str, str]]:
    rows = []
    for case in cases:
        rows.append(
            {
                EXCEL_COLUMNS[0]: case.module,
                EXCEL_COLUMNS[1]: case.feature,
                EXCEL_COLUMNS[2]: case.title,
                EXCEL_COLUMNS[3]: case.precondition,
                EXCEL_COLUMNS[4]: case.steps,
                EXCEL_COLUMNS[5]: case.expected_result,
                EXCEL_COLUMNS[6]: case.priority,
                EXCEL_COLUMNS[7]: case.case_type,
            }
        )
    return rows


if __name__ == "__main__":
    main()
