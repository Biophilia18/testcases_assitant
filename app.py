from __future__ import annotations

import streamlit as st

from src.ai_client import generate_cases, is_provider_configured
from src.exporter import build_excel
from src.filename_utils import build_export_filename
from src.models import GenerationResult, TestCase
from src.quality_checker import check_cases
from src.table_adapter import cases_to_rows, find_case_warnings, rows_to_cases


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
            st.session_state["export_filename"] = build_export_filename(
                project_name=project_name,
                business_module=business_module,
                generation_type=generation_type,
            )
            st.session_state["last_requirement_text"] = requirement_text
            st.session_state["last_generation_config"] = {
                "mode": mode,
                "provider": provider,
                "generation_type": generation_type,
                "cases_per_feature": cases_per_feature,
            }

    result: GenerationResult | None = st.session_state.get("generation_result")
    if not result or not result.cases:
        return

    _render_generation_status(result)

    _render_grouped_summary(result.cases)
    _render_regenerate_panel(result)

    st.subheader("全部用例编辑")
    st.caption("可直接修改单元格内容。导出 Excel 时会使用编辑后的表格。")

    edited_rows = st.data_editor(
        cases_to_rows(result.cases),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editable_cases",
    )
    edited_cases = rows_to_cases(edited_rows)
    warnings = find_case_warnings(edited_cases)

    if warnings:
        with st.expander(f"编辑检查：发现 {len(warnings)} 个提示"):
            for warning in warnings:
                st.warning(warning)

    excel_bytes = build_excel(edited_cases)
    st.download_button(
        f"导出 Excel（{len(edited_cases)} 条）",
        data=excel_bytes,
        file_name=st.session_state.get("export_filename", "测试用例.xlsx"),
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


def _render_grouped_summary(cases: list[TestCase]) -> None:
    st.subheader("按功能点分组")
    groups = _group_cases(cases)
    if not groups:
        st.info("暂无可分组的测试用例。")
        return

    tabs = st.tabs([f"{key}（{len(group)}）" for key, group in groups.items()])
    for tab, (key, group) in zip(tabs, groups.items()):
        with tab:
            st.dataframe(cases_to_rows(group), use_container_width=True, hide_index=True)
            issues = check_cases(group)
            if issues:
                st.caption(f"{key} 检查提示：{len(issues)} 个")


def _render_regenerate_panel(result: GenerationResult) -> None:
    st.subheader("单功能点重新生成")
    groups = _group_cases(result.cases)
    if not groups:
        return

    selected_group = st.selectbox("选择要重新生成的功能点", list(groups.keys()))
    if st.button("重新生成所选功能点"):
        config = st.session_state.get("last_generation_config", {})
        selected_cases = groups[selected_group]
        requirement_text = _build_regenerate_requirement(selected_group, selected_cases)

        with st.spinner("正在重新生成所选功能点..."):
            regenerated = generate_cases(
                requirement_text=requirement_text,
                mode=config.get("mode", "规则生成"),
                cases_per_feature=config.get("cases_per_feature", 6),
                provider=config.get("provider", "DeepSeek"),
                generation_type=config.get("generation_type", "功能测试"),
            )

        kept_cases = [case for case in result.cases if _group_key(case) != selected_group]
        merged_cases = _renumber_cases(kept_cases + regenerated.cases)
        st.session_state["generation_result"] = GenerationResult(
            cases=merged_cases,
            requested_mode=result.requested_mode,
            actual_mode=result.actual_mode,
            provider=result.provider,
            feature_count=len(_group_cases(merged_cases)),
            case_count=len(merged_cases),
            model=result.model,
            message=f"已重新生成 {selected_group}，当前共 {len(merged_cases)} 条用例。",
            fallback_reason=result.fallback_reason,
        )
        st.rerun()


def _group_cases(cases: list[TestCase]) -> dict[str, list[TestCase]]:
    groups: dict[str, list[TestCase]] = {}
    for case in cases:
        groups.setdefault(_group_key(case), []).append(case)
    return groups


def _group_key(case: TestCase) -> str:
    module = case.module or "未指定模块"
    feature = case.feature or "未指定功能点"
    return f"{module} / {feature}"


def _build_regenerate_requirement(group_key: str, cases: list[TestCase]) -> str:
    case = cases[0]
    return "\n".join(
        [
            f"只重新生成这个功能点：{group_key}",
            f"模块：{case.module}",
            f"功能点：{case.feature}",
            "已有用例摘要：",
            *[f"- {item.title}" for item in cases[:10]],
            "要求：保留同一功能点语义，重新生成更完整、更可执行的测试用例。",
        ]
    )


def _renumber_cases(cases: list[TestCase]) -> list[TestCase]:
    groups = _group_cases(cases)
    renumbered: list[TestCase] = []
    for group_index, group in enumerate(groups.values(), start=1):
        for case_index, case in enumerate(group, start=1):
            case.case_id = f"TC-{group_index:02d}-{case_index:02d}"
            renumbered.append(case)
    return renumbered

if __name__ == "__main__":
    main()
