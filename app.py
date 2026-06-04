from __future__ import annotations

import streamlit as st

from src.ai_client import generate_cases, is_provider_configured
from src.exporter import build_excel
from src.models import EXCEL_COLUMNS, GenerationResult, TestCase


st.set_page_config(page_title="AI 测试用例助手", layout="wide")


def main() -> None:
    st.title("AI 辅助测试用例生成与导出工具")

    with st.sidebar:
        mode = st.radio("生成方式", ["规则生成", "AI 生成"], index=0)
        provider = st.radio("AI 服务商", ["DeepSeek", "OpenAI"], index=0)
        generation_type = st.selectbox(
            "用例生成类型",
            ["功能测试", "接口测试", "Web UI 测试", "App 测试"],
            index=0,
        )
        cases_per_feature = st.slider("每个功能点生成用例数", min_value=3, max_value=8, value=6)

        if is_provider_configured(provider):
            st.success(f"已检测到 {provider} API Key。")
        else:
            env_name = "DEEPSEEK_API_KEY" if provider == "DeepSeek" else "OPENAI_API_KEY"
            st.info(f"未检测到 {env_name}，AI 生成会自动回退到规则生成。")

    st.subheader("需求模板")
    project_name = st.text_input("项目/系统名称", placeholder="例如：电商后台、会员 App、订单管理系统")

    col1, col2 = st.columns(2)
    with col1:
        business_module = st.text_input("业务模块", placeholder="例如：退款管理、用户登录、订单查询")
    with col2:
        user_role = st.text_input("使用角色", placeholder="例如：普通用户、客服、管理员")

    precondition = st.text_area(
        "前置条件",
        height=90,
        placeholder="例如：用户已登录；存在可退款订单；客服账号具备审核权限。",
    )
    business_flow = st.text_area(
        "业务流程/需求描述",
        height=180,
        placeholder="例如：用户登录后查询订单，选择订单提交退款申请，客服审核通过后系统原路退款，用户可导出退款记录。",
    )
    acceptance_criteria = st.text_area(
        "验收标准",
        height=120,
        placeholder="例如：退款成功后订单状态变更；审核失败需要展示失败原因；导出文件包含退款单号和金额。",
    )
    constraints = st.text_area(
        "补充规则/异常场景",
        height=100,
        placeholder="例如：重复提交不得产生多条退款单；弱网下不能重复扣款；无权限用户不能审核。",
    )

    generate_clicked = st.button("生成测试用例", type="primary")

    if generate_clicked:
        requirement_text = _build_requirement_text(
            project_name=project_name,
            business_module=business_module,
            user_role=user_role,
            precondition=precondition,
            business_flow=business_flow,
            acceptance_criteria=acceptance_criteria,
            constraints=constraints,
            generation_type=generation_type,
        )

        if not requirement_text.strip():
            st.warning("请至少输入业务流程/需求描述。")
            return

        with st.spinner("正在生成测试用例..."):
            st.session_state["generation_result"] = generate_cases(
                requirement_text=requirement_text,
                mode=mode,
                cases_per_feature=cases_per_feature,
                provider=provider,
                generation_type=generation_type,
            )

    result: GenerationResult | None = st.session_state.get("generation_result")
    if not result or not result.cases:
        return

    _render_generation_status(result)

    st.subheader("测试用例预览")
    st.dataframe(_to_table(result.cases), use_container_width=True, hide_index=True)

    excel_bytes = build_excel(result.cases)
    st.download_button(
        "导出 Excel",
        data=excel_bytes,
        file_name="测试用例.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _build_requirement_text(
    project_name: str,
    business_module: str,
    user_role: str,
    precondition: str,
    business_flow: str,
    acceptance_criteria: str,
    constraints: str,
    generation_type: str,
) -> str:
    sections = [
        ("用例生成类型", generation_type),
        ("项目/系统名称", project_name),
        ("业务模块", business_module),
        ("使用角色", user_role),
        ("前置条件", precondition),
        ("业务流程/需求描述", business_flow),
        ("验收标准", acceptance_criteria),
        ("补充规则/异常场景", constraints),
    ]
    return "\n".join(f"{title}：{value.strip()}" for title, value in sections if value.strip())


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
                EXCEL_COLUMNS[0]: case.case_id,
                EXCEL_COLUMNS[1]: case.module,
                EXCEL_COLUMNS[2]: case.feature,
                EXCEL_COLUMNS[3]: case.title,
                EXCEL_COLUMNS[4]: case.precondition,
                EXCEL_COLUMNS[5]: case.test_data,
                EXCEL_COLUMNS[6]: case.steps,
                EXCEL_COLUMNS[7]: case.expected_result,
                EXCEL_COLUMNS[8]: case.priority,
                EXCEL_COLUMNS[9]: case.case_type,
                EXCEL_COLUMNS[10]: case.remark,
            }
        )
    return rows


if __name__ == "__main__":
    main()
