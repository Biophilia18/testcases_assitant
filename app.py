from __future__ import annotations

from collections import Counter

import streamlit as st

from src.ai_client import generate_cases, is_provider_configured
from src.coverage_analyzer import build_coverage_matrix, coverage_matrix_to_rows
from src.coverage_config import COVERAGE_TYPE_OPTIONS, DEFAULT_COVERAGE_TYPES, normalize_coverage_types
from src.document_loader import load_requirement_document
from src.exporter import build_excel
from src.filename_utils import build_export_filename
from src.generation_preview import GenerationPreview, build_generation_preview
from src.models import GenerationResult, TestCase
from src.persistence import (
    list_history_files,
    load_generation_result_from_path,
    load_generation_result_from_text,
    load_latest_generation_result,
    save_generation_result,
)
from src.quality_score import QualityScore, calculate_quality_score
from src.quality_checker import check_cases
from src.requirement_parser import parse_requirement_text
from src.table_adapter import cases_to_rows, find_case_warnings, rows_to_cases


st.set_page_config(page_title="AI 测试用例助手", layout="wide")


def main() -> None:
    st.title("AI 辅助测试用例生成与导出工具")

    with st.sidebar:
        mode = st.radio("生成方式", ["规则生成", "AI 生成"], index=0)
        provider = st.radio("AI 服务商", ["DeepSeek", "OpenAI"], index=0)
        generation_type = "功能测试"
        st.selectbox("用例生成类型", ["功能测试"], index=0, help="当前阶段先完整打磨功能测试。")
        coverage_types = st.multiselect(
            "覆盖类型",
            COVERAGE_TYPE_OPTIONS,
            default=DEFAULT_COVERAGE_TYPES,
            help="当前按所选覆盖类型为每个功能点生成用例。建议先保留默认项，弱网/状态流转/兼容性按需求补充。",
        )
        selected_coverage_types = normalize_coverage_types(coverage_types)
        if not coverage_types:
            st.warning("未选择覆盖类型时会使用默认覆盖类型。")

        if is_provider_configured(provider):
            st.success(f"已检测到 {provider} API Key。")
        else:
            env_name = "DEEPSEEK_API_KEY" if provider == "DeepSeek" else "OPENAI_API_KEY"
            st.info(f"未检测到 {env_name}，AI 生成会自动回退到规则生成。")

    input_tab, result_tab, quality_tab, export_tab = st.tabs(["需求输入", "生成结果", "质量检查", "导出"])

    with input_tab:
        _render_input_tab(mode, provider, generation_type, selected_coverage_types)

    result: GenerationResult | None = st.session_state.get("generation_result")
    if not result or not result.cases:
        with result_tab:
            st.info("暂无测试用例。请先生成或导入历史 JSON。")
        return

    with result_tab:
        _render_generation_status(result)
        _render_quality_snapshot(result.cases, result.coverage_types)
        _render_grouped_summary(result.cases, result.coverage_types)
        _render_regenerate_panel(result)
        _render_edit_table(result)

    edited_cases = st.session_state.get("edited_cases", result.cases)

    with quality_tab:
        _render_quality_tab(edited_cases, result.coverage_types)

    with export_tab:
        _render_export_tab(edited_cases, result.coverage_types)


def _render_input_tab(mode: str, provider: str, generation_type: str, coverage_types: list[str]) -> None:
    st.subheader("需求模板")
    requirement_file = st.file_uploader(
        "上传需求文件（txt / md / docx）",
        type=["txt", "md", "docx"],
        help="不要求固定格式。能识别的字段会自动填入；识别不到的内容会放入业务流程/需求描述。",
    )
    if requirement_file is not None:
        _apply_uploaded_requirement(requirement_file)

    project_name = st.text_input(
        "项目/系统名称",
        key="project_name",
        placeholder="例如：电商后台、会员 App、订单管理系统",
    )

    col1, col2 = st.columns(2)
    with col1:
        business_module = st.text_input(
            "业务模块",
            key="business_module",
            placeholder="例如：退款管理、用户登录、订单查询",
        )
    with col2:
        user_role = st.text_input(
            "使用角色",
            key="user_role",
            placeholder="例如：普通用户、客服、管理员",
        )

    precondition = st.text_area(
        "前置条件",
        key="precondition",
        height=90,
        placeholder="例如：用户已登录；存在可退款订单；客服账号具备审核权限。",
    )
    business_flow = st.text_area(
        "业务流程/需求描述",
        key="business_flow",
        height=180,
        placeholder="例如：用户登录后查询订单，选择订单提交退款申请，客服审核通过后系统原路退款，用户可导出退款记录。",
    )
    acceptance_criteria = st.text_area(
        "验收标准",
        key="acceptance_criteria",
        height=120,
        placeholder="例如：退款成功后订单状态变更；审核失败需要展示失败原因；导出文件包含退款单号和金额。",
    )
    constraints = st.text_area(
        "补充规则/异常场景",
        key="constraints",
        height=100,
        placeholder="例如：重复提交不得产生多条退款单；弱网下不能重复扣款；无权限用户不能审核。",
    )

    preview_clicked = st.button("预览生成计划", type="primary")
    load_col1, load_col2 = st.columns(2)
    with load_col1:
        if st.button("加载最近一次 JSON"):
            try:
                result, filename = load_latest_generation_result()
                _set_generation_result(result, filename)
                st.success("已加载最近一次生成结果。")
                st.rerun()
            except FileNotFoundError:
                st.warning("还没有找到 outputs/latest_cases.json。")
            except Exception as exc:
                st.error(f"加载失败：{exc}")

    with load_col2:
        uploaded_file = st.file_uploader("导入历史 JSON", type=["json"])
        if uploaded_file is not None:
            try:
                result, filename = load_generation_result_from_text(uploaded_file.read().decode("utf-8"))
                _set_generation_result(result, filename)
                st.success("已导入历史 JSON。")
                st.rerun()
            except Exception as exc:
                st.error(f"导入失败：{exc}")

    history_files = list_history_files()
    if history_files:
        history_labels = [path.name for path in history_files]
        selected_history = st.selectbox("选择本地历史 JSON", history_labels)
        if st.button("加载所选历史 JSON"):
            try:
                selected_path = history_files[history_labels.index(selected_history)]
                result, filename = load_generation_result_from_path(selected_path)
                _set_generation_result(result, filename)
                st.success(f"已加载 {selected_path.name}。")
                st.rerun()
            except Exception as exc:
                st.error(f"加载失败：{exc}")

    if preview_clicked:
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

        st.session_state["pending_generation"] = {
            "requirement_text": requirement_text,
            "feature_source_text": business_flow,
            "project_name": project_name,
            "business_module": business_module,
            "mode": mode,
            "provider": provider,
            "generation_type": generation_type,
            "cases_per_feature": len(coverage_types),
            "coverage_types": coverage_types,
        }

    pending_generation = st.session_state.get("pending_generation")
    if pending_generation:
        preview = build_generation_preview(
            pending_generation["requirement_text"],
            pending_generation["cases_per_feature"],
            feature_source_text=pending_generation.get("feature_source_text", ""),
            coverage_types=pending_generation.get("coverage_types", []),
        )
        _render_generation_preview(preview)

        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("确认生成", type="primary"):
                _run_confirmed_generation(pending_generation)
        with cancel_col:
            if st.button("取消预览"):
                st.session_state.pop("pending_generation", None)
                st.rerun()


def _apply_uploaded_requirement(uploaded_file) -> None:
    upload_key = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.get("last_requirement_upload") == upload_key:
        return

    try:
        raw_text = load_requirement_document(uploaded_file.name, uploaded_file.read())
    except Exception as exc:
        st.error(f"需求文件读取失败：{exc}")
        return

    parsed = parse_requirement_text(raw_text)
    field_map = {
        "project_name": parsed.project_name,
        "business_module": parsed.business_module,
        "user_role": parsed.user_role,
        "precondition": parsed.precondition,
        "business_flow": parsed.business_flow,
        "acceptance_criteria": parsed.acceptance_criteria,
        "constraints": parsed.constraints,
    }

    filled_fields = []
    for key, value in field_map.items():
        if value:
            st.session_state[key] = value
            filled_fields.append(key)

    st.session_state["last_requirement_upload"] = upload_key
    if filled_fields:
        st.success(f"已识别并填充 {len(filled_fields)} 个字段，可继续手动调整。")
    else:
        st.warning("未识别到有效内容，请检查文件内容。")


def _render_generation_preview(preview: GenerationPreview) -> None:
    st.subheader("生成前预览")
    col1, col2, col3 = st.columns(3)
    col1.metric("识别功能点", len(preview.feature_items))
    col2.metric("每功能点覆盖类型", preview.cases_per_feature)
    col3.metric("预计用例数", preview.estimated_case_count)
    if preview.coverage_types:
        st.caption("覆盖策略：" + "、".join(preview.coverage_types))

    for warning in preview.warnings:
        st.warning(warning)

    with st.expander("查看识别到的功能点", expanded=bool(preview.warnings)):
        for index, item in enumerate(preview.feature_items, start=1):
            st.write(f"{index}. {item.module} / {item.feature}")
            st.caption(item.description[:160])


def _run_confirmed_generation(pending_generation: dict) -> None:
    with st.spinner("正在生成测试用例..."):
        result = generate_cases(
            requirement_text=pending_generation["requirement_text"],
            mode=pending_generation["mode"],
            cases_per_feature=pending_generation["cases_per_feature"],
            provider=pending_generation["provider"],
            generation_type=pending_generation["generation_type"],
            feature_source_text=pending_generation.get("feature_source_text", ""),
            coverage_types=pending_generation.get("coverage_types", []),
        )
        export_filename = build_export_filename(
            project_name=pending_generation["project_name"],
            business_module=pending_generation["business_module"],
            generation_type=pending_generation["generation_type"],
        )
        _set_generation_result(result, export_filename)
        st.session_state["last_requirement_text"] = pending_generation["requirement_text"]
        st.session_state["last_generation_config"] = {
            "mode": pending_generation["mode"],
            "provider": pending_generation["provider"],
            "generation_type": pending_generation["generation_type"],
            "cases_per_feature": pending_generation["cases_per_feature"],
            "coverage_types": pending_generation.get("coverage_types", []),
        }
        save_generation_result(result, export_filename)
        st.session_state.pop("pending_generation", None)
        st.success("生成结果已保存到 outputs/latest_cases.json。")
        st.rerun()


def _render_edit_table(result: GenerationResult) -> None:
    st.subheader("全部用例编辑")
    st.caption("可直接修改单元格内容。导出 Excel 时会使用编辑后的表格。")

    edited_rows = st.data_editor(
        cases_to_rows(result.cases),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=f"editable_cases_{st.session_state.get('generation_revision', 0)}",
    )
    edited_cases = rows_to_cases(edited_rows)
    st.session_state["edited_cases"] = edited_cases
    warnings = find_case_warnings(edited_cases)

    if warnings:
        with st.expander(f"编辑检查：发现 {len(warnings)} 个提示", expanded=False):
            st.dataframe(_warning_summary_rows(warnings), use_container_width=True, hide_index=True)


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


def _render_quality_snapshot(cases: list[TestCase], coverage_types: list[str] | None = None) -> None:
    score = calculate_quality_score(cases, coverage_types)
    matrix = build_coverage_matrix(cases, coverage_types)
    covered_count = sum(1 for item in matrix if item.covered)

    st.subheader("质量概览")
    col1, col2, col3 = st.columns(3)
    col1.metric("质量评分", score.score)
    col2.metric("覆盖项", f"{covered_count}/{len(matrix)}")
    col3.metric("内容扣分", sum(item.points for item in score.deductions))
    st.caption(score.summary)

    with st.expander("查看覆盖矩阵", expanded=False):
        st.dataframe(coverage_matrix_to_rows(matrix), use_container_width=True, hide_index=True)


def _render_quality_tab(cases: list[TestCase], coverage_types: list[str] | None = None) -> None:
    st.subheader("生成质量报告")
    selected_coverage_types = normalize_coverage_types(coverage_types)
    score = calculate_quality_score(cases, selected_coverage_types)
    matrix = build_coverage_matrix(cases, selected_coverage_types)
    st.caption("覆盖检查：" + "、".join(selected_coverage_types))
    issues = check_cases(cases, selected_coverage_types)
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("质量评分", score.score)
    col2.metric("总用例数", len(cases))
    col3.metric("功能点数", len(_group_cases(cases)))
    col4.metric("质量提示", len(issues))
    col5.metric("覆盖项", f"{sum(1 for item in matrix if item.covered)}/{len(matrix)}")
    col6.metric("P1/P0", sum(1 for case in cases if case.priority in {"P0", "P1"}))
    st.info(score.summary)

    with st.expander("覆盖矩阵", expanded=False):
        st.dataframe(coverage_matrix_to_rows(matrix), use_container_width=True, hide_index=True)

    with st.expander("评分明细", expanded=False):
        _render_score_details(score)

    if not issues:
        st.success("暂无明显质量提示。")
        return

    with st.expander("质量提示分类汇总", expanded=False):
        st.dataframe(_issue_summary_rows(issues), use_container_width=True, hide_index=True)

    with st.expander("质量提示明细", expanded=False):
        for issue in issues:
            if issue.severity == "错误":
                st.error(f"{issue.case_id}：{issue.message}")
            else:
                st.warning(f"{issue.case_id}：{issue.message}")


def _render_score_details(score: QualityScore) -> None:
    addition_rows = [{"项目": item.label, "分值": item.points} for item in score.additions]
    deduction_rows = [{"项目": item.label, "分值": item.points} for item in score.deductions]
    if addition_rows:
        st.write("加分项")
        st.dataframe(addition_rows, use_container_width=True, hide_index=True)
    if deduction_rows:
        st.write("扣分项")
        st.dataframe(deduction_rows, use_container_width=True, hide_index=True)
    if not addition_rows and not deduction_rows:
        st.caption("暂无评分明细。")


def _issue_summary_rows(issues) -> list[dict[str, str | int]]:
    counter = Counter(_issue_category(issue.message) for issue in issues)
    return [{"分类": category, "数量": count} for category, count in counter.items()]


def _warning_summary_rows(warnings: list[str]) -> list[dict[str, str | int]]:
    counter = Counter(_issue_category(warning) for warning in warnings)
    return [{"分类": category, "数量": count} for category, count in counter.items()]


def _issue_category(message: str) -> str:
    if any(keyword in message for keyword in ["缺少用例编号", "缺少用例标题", "缺少操作步骤", "缺少预期结果", "缺少优先级", "用例编号重复"]):
        return "基础字段"
    if "操作步骤" in message:
        return "操作步骤"
    if "预期结果" in message:
        return "预期结果"
    if "测试数据" in message:
        return "测试数据"
    if message.startswith("缺少") and "用例" in message:
        return "覆盖缺口"
    return "其他"


def _render_export_tab(cases: list[TestCase], coverage_types: list[str] | None = None) -> None:
    st.subheader("导出")
    filename = st.session_state.get("export_filename", "测试用例.xlsx")
    st.text_input("导出文件名", value=filename, key="export_filename")

    result: GenerationResult | None = st.session_state.get("generation_result")
    if result and st.button("保存当前编辑结果为 JSON"):
        snapshot = GenerationResult(
            cases=cases,
            requested_mode=result.requested_mode,
            actual_mode=result.actual_mode,
            feature_count=len(_group_cases(cases)),
            case_count=len(cases),
            coverage_types=result.coverage_types,
            provider=result.provider,
            model=result.model,
            message=result.message,
            fallback_reason=result.fallback_reason,
        )
        save_generation_result(snapshot, st.session_state.get("export_filename", filename))
        st.success("已保存到 outputs/latest_cases.json，并生成历史快照。")

    excel_bytes = build_excel(cases, coverage_types=coverage_types)
    st.download_button(
        f"导出 Excel（{len(cases)} 条，含质量报告）",
        data=excel_bytes,
        file_name=st.session_state.get("export_filename", filename),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _render_grouped_summary(cases: list[TestCase], coverage_types: list[str] | None = None) -> None:
    st.subheader("按功能点分组")
    groups = _group_cases(cases)
    if not groups:
        st.info("暂无可分组的测试用例。")
        return

    tabs = st.tabs([f"{key}（{len(group)}）" for key, group in groups.items()])
    for tab, (key, group) in zip(tabs, groups.items()):
        with tab:
            st.dataframe(cases_to_rows(group), use_container_width=True, hide_index=True)
            issues = check_cases(group, coverage_types)
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
                feature_source_text=requirement_text,
                coverage_types=config.get("coverage_types", []),
            )

        kept_cases = [case for case in result.cases if _group_key(case) != selected_group]
        merged_cases = _renumber_cases(kept_cases + regenerated.cases)
        merged_result = GenerationResult(
            cases=merged_cases,
            requested_mode=result.requested_mode,
            actual_mode=result.actual_mode,
            provider=result.provider,
            coverage_types=result.coverage_types,
            feature_count=len(_group_cases(merged_cases)),
            case_count=len(merged_cases),
            model=result.model,
            message=f"已重新生成 {selected_group}，当前共 {len(merged_cases)} 条用例。",
            fallback_reason=result.fallback_reason,
        )
        _set_generation_result(merged_result, st.session_state.get("export_filename", "测试用例.xlsx"))
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


def _set_generation_result(result: GenerationResult, export_filename: str) -> None:
    st.session_state["generation_result"] = result
    st.session_state["export_filename"] = export_filename
    st.session_state["edited_cases"] = result.cases
    _bump_generation_revision()


def _bump_generation_revision() -> None:
    st.session_state["generation_revision"] = st.session_state.get("generation_revision", 0) + 1

if __name__ == "__main__":
    main()
