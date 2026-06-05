from __future__ import annotations

from collections import Counter

import streamlit as st

from src.ai_client import generate_cases, is_provider_configured
from src.api_document_parser import api_document_to_fields, fields_to_api_document, parse_api_document
from src.api_exporter import build_api_excel
from src.api_models import ApiDocument, ApiTestCase
from src.api_quality_checker import analyze_api_quality, api_quality_issues_to_rows, api_quality_summary
from src.api_rule_generator import generate_api_cases
from src.api_table_adapter import api_cases_to_rows, find_api_case_warnings, rows_to_api_cases
from src.coverage_analyzer import build_coverage_matrix, coverage_matrix_to_rows
from src.coverage_config import COVERAGE_TYPE_OPTIONS, DEFAULT_COVERAGE_TYPES, normalize_coverage_types
from src.document_loader import load_requirement_document
from src.exporter import build_excel
from src.feature_selection import count_selected_rows, feature_items_to_rows, selected_rows_to_feature_source
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
from src.regeneration import (
    REGENERATION_FOCUS_OPTIONS,
    build_regeneration_requirement,
    coverage_types_for_focus,
    replace_group_preserving_case_ids,
)
from src.requirement_parser import parse_requirement_text
from src.table_adapter import cases_to_rows, find_case_warnings, rows_to_cases


st.set_page_config(page_title="AI 测试用例助手", layout="wide")

QUALITY_MATRIX_TYPES = ["正常流程", "异常场景", "边界/非法输入", "权限控制", "重复操作", "数据一致性", "状态流转"]


def main() -> None:
    st.title("AI 辅助测试用例生成与导出工具")

    with st.sidebar:
        generation_type = st.selectbox("用例生成类型", ["功能测试", "接口测试"], index=0)
        if generation_type == "接口测试":
            st.caption("接口测试当前为规则生成 MVP：支持文档解析、手动修正、规则生成、编辑和 Excel 导出。")
        else:
            mode = st.radio("生成方式", ["规则生成", "AI 生成"], index=0)
            provider = st.radio("AI 服务商", ["DeepSeek", "OpenAI"], index=0)
            st.caption("当前重点支持功能测试。接口/Web UI/App 测试为后续方向或预留模板。")
            coverage_types = st.multiselect(
                "覆盖类型",
                COVERAGE_TYPE_OPTIONS,
                default=DEFAULT_COVERAGE_TYPES,
                help="当前按所选覆盖类型为每个功能点生成用例。建议先保留默认项，弱网/状态流转/兼容性按需求补充。",
            )
            selected_coverage_types = normalize_coverage_types(coverage_types)
            if not coverage_types:
                st.warning("未选择覆盖类型时会使用默认覆盖类型。")
            st.caption(f"当前每个功能点预计生成 {len(selected_coverage_types)} 条用例。")

            if is_provider_configured(provider):
                st.success(f"已检测到 {provider} API Key。")
            else:
                env_name = "DEEPSEEK_API_KEY" if provider == "DeepSeek" else "OPENAI_API_KEY"
                st.info(f"未检测到 {env_name}，AI 生成会自动回退到规则生成。")

            _render_history_loader()

    if generation_type == "接口测试":
        _render_api_test_page()
        return

    _render_step_input(mode, provider, generation_type, selected_coverage_types)
    st.divider()
    _render_step_preview()
    st.divider()

    result: GenerationResult | None = st.session_state.get("generation_result")
    if not result or not result.cases:
        st.subheader("Step 3：生成结果")
        st.info("暂无测试用例。请先完成需求输入和生成计划预览。")
        st.subheader("Step 4：编辑与质量检查")
        st.info("生成测试用例后可在此编辑和检查质量。")
        st.subheader("Step 5：保存与导出")
        st.info("生成测试用例后可保存 JSON 或导出 Excel。")
        return

    st.subheader("Step 3：生成结果")
    _render_generation_status(result)
    _render_quality_snapshot(result.cases, result.coverage_types)
    _render_grouped_summary(result.cases, result.coverage_types)

    edited_cases = st.session_state.get("edited_cases", result.cases)

    st.subheader("Step 4：编辑与质量检查")
    _render_edit_table(result)
    edited_cases = st.session_state.get("edited_cases", result.cases)
    _render_quality_tab(edited_cases, result.coverage_types)
    _render_regenerate_panel(result)

    st.subheader("Step 5：保存与导出")
    _render_export_tab(edited_cases, result.coverage_types)


def _render_step_input(mode: str, provider: str, generation_type: str, coverage_types: list[str]) -> None:
    st.subheader("Step 1：需求输入")
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

    preview_clicked = st.button("生成计划预览", type="primary")

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

        if not business_flow.strip():
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


def _render_history_loader() -> None:
    with st.expander("历史 JSON", expanded=False):
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


def _render_api_test_page() -> None:
    st.title("接口测试用例编辑与导出")
    st.caption("当前接口测试模式为规则生成 MVP：支持接口文档识别、手动修正、规则生成、表格编辑和 Excel 导出，暂不接 AI。")

    st.subheader("接口文档输入")
    api_document_file = st.file_uploader(
        "上传接口文档（txt / md）",
        type=["txt", "md"],
        key="api_document_upload",
        help="当前接口模式先支持 txt 和 md。上传后会自动解析并填充下方字段。",
    )
    if api_document_file is not None:
        _apply_uploaded_api_document(api_document_file)

    api_document_text = st.text_area(
        "粘贴接口文档",
        key="api_document_text",
        height=260,
        placeholder=(
            "示例：\n"
            "项目/系统名称：智控家监测系统\n"
            "业务模块：设备控制\n"
            "接口名称：设备控制接口\n"
            "请求方法：POST\n"
            "接口路径：/api/devices/{deviceId}/control\n"
            "鉴权方式：Bearer Token\n"
            "请求参数：deviceId 设备ID，必填\n"
            "请求体：{\"action\":\"open\"}\n"
            "业务规则：设备在线且用户有权限才允许控制\n"
            "数据库校验：设备状态记录更新"
        ),
    )
    if st.button("解析接口文档"):
        if not api_document_text.strip():
            st.warning("请先粘贴接口文档内容。")
        else:
            parsed_document = parse_api_document(api_document_text)
            _apply_api_document_to_state(parsed_document)
            st.session_state["api_document_parsed"] = True
            st.success("已解析接口文档，请检查并手动修正识别结果。")

    st.subheader("解析结果预览与修正")
    if not st.session_state.get("api_document_parsed"):
        st.info("可以直接手动填写，也可以先粘贴接口文档并点击“解析接口文档”。")

    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("项目/系统名称", key="api_project_name", placeholder="例如：智控家监测系统")
        module = st.text_input("业务模块", key="api_module", placeholder="例如：设备控制")
        api_name = st.text_input("接口名称", key="api_name", placeholder="例如：设备控制接口")
    with col2:
        method = st.selectbox("请求方法", ["GET", "POST", "PUT", "PATCH", "DELETE"], index=1, key="api_method")
        path = st.text_input("接口路径", key="api_path", placeholder="例如：/api/devices/{deviceId}/control")
        auth = st.text_input("鉴权方式", key="api_auth", placeholder="例如：Bearer Token / Session / 无")

    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        headers = st.text_area("请求头", key="api_headers", height=90, placeholder="例如：Authorization、Content-Type")
        params = st.text_area("请求参数 / 字段说明", key="api_params", height=120, placeholder="例如：deviceId 设备ID，必填")
        body = st.text_area("请求体", key="api_body", height=140, placeholder='例如：{"action": "open"}')
    with detail_col2:
        response_example = st.text_area("响应示例", key="api_response_example", height=140, placeholder="可填写成功响应和失败响应")
        business_rules = st.text_area("业务规则", key="api_business_rules", height=120, placeholder="例如：设备在线且用户有权限才允许控制")
        db_checks = st.text_area("数据库校验", key="api_db_checks", height=90, placeholder="例如：设备状态记录更新")

    document = fields_to_api_document(
        {
            "project_name": project_name,
            "module": module,
            "api_name": api_name,
            "method": method,
            "path": path,
            "auth": auth,
            "headers": headers,
            "params": params,
            "body": body,
            "response_example": response_example,
            "business_rules": business_rules,
            "db_checks": db_checks,
        }
    )

    with st.expander("查看当前接口文档结构化结果", expanded=False):
        st.dataframe(_api_document_preview_rows(document), use_container_width=True, hide_index=True)

    if st.button("生成接口测试用例", type="primary"):
        st.session_state["api_cases"] = generate_api_cases(document)
        st.session_state["api_export_filename"] = _build_api_export_filename(project_name, module)

    api_cases: list[ApiTestCase] = st.session_state.get("api_cases") or generate_api_cases(document)
    st.subheader("接口测试用例编辑")
    edited_rows = st.data_editor(
        api_cases_to_rows(api_cases),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="api_case_editor",
    )
    edited_cases = rows_to_api_cases(edited_rows)
    st.session_state["api_cases"] = edited_cases

    warnings = find_api_case_warnings(edited_cases)
    if warnings:
        with st.expander(f"接口用例检查：发现 {len(warnings)} 个提示", expanded=False):
            for warning in warnings:
                st.warning(warning)

    _render_api_quality_panel(edited_cases, document)

    st.subheader("导出接口 Excel")
    filename = st.text_input(
        "接口 Excel 文件名",
        value=st.session_state.get("api_export_filename", _build_api_export_filename(project_name, module)),
        key="api_export_filename",
    )
    st.download_button(
        f"导出接口 Excel（{len(edited_cases)} 条）",
        data=build_api_excel(edited_cases, document=document),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _render_api_quality_panel(cases: list[ApiTestCase], document: ApiDocument) -> None:
    issues = analyze_api_quality(cases, document)
    summary = api_quality_summary(cases, issues)

    st.subheader("接口质量检查")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("用例数", summary["case_count"])
    col2.metric("覆盖类型", summary["covered_categories"])
    col3.metric("错误", summary["error_count"])
    col4.metric("警告", summary["warning_count"])
    st.caption("接口质量检查用于辅助发现断言、鉴权、参数和数据库校验缺口，最终仍需结合接口文档和业务规则复核。")

    if not issues:
        st.success("接口用例暂无明显质量提示。")
        return

    with st.expander(f"查看接口质量提示（{summary['issue_count']} 项）", expanded=False):
        st.dataframe(api_quality_issues_to_rows(issues), use_container_width=True, hide_index=True)


def _apply_uploaded_api_document(uploaded_file) -> None:
    upload_key = f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"
    if st.session_state.get("last_api_document_upload") == upload_key:
        return

    try:
        raw_text = load_requirement_document(uploaded_file.name, uploaded_file.read())
    except Exception as exc:
        st.error(f"接口文档读取失败：{exc}")
        return

    parsed_document = parse_api_document(raw_text)
    st.session_state["api_document_text"] = raw_text
    _apply_api_document_to_state(parsed_document)
    st.session_state["api_document_parsed"] = True
    st.session_state["last_api_document_upload"] = upload_key
    st.success("已读取并解析接口文档，请检查解析结果并手动修正。")


def _apply_api_document_to_state(document: ApiDocument) -> None:
    field_to_key = {
        "project_name": "api_project_name",
        "module": "api_module",
        "api_name": "api_name",
        "method": "api_method",
        "path": "api_path",
        "auth": "api_auth",
        "headers": "api_headers",
        "params": "api_params",
        "body": "api_body",
        "response_example": "api_response_example",
        "business_rules": "api_business_rules",
        "db_checks": "api_db_checks",
    }
    fields = api_document_to_fields(document)
    for field, key in field_to_key.items():
        value = fields.get(field, "")
        if field == "method" and value not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            value = "POST"
        st.session_state[key] = value


def _api_document_preview_rows(document: ApiDocument) -> list[dict[str, str]]:
    return [
        {"字段": "项目/系统名称", "识别内容": document.project_name},
        {"字段": "业务模块", "识别内容": document.module},
        {"字段": "接口名称", "识别内容": document.api_name},
        {"字段": "请求方法", "识别内容": document.method},
        {"字段": "接口路径", "识别内容": document.path},
        {"字段": "鉴权方式", "识别内容": document.auth},
        {"字段": "请求头", "识别内容": document.headers},
        {"字段": "请求参数 / 字段说明", "识别内容": document.params},
        {"字段": "请求体", "识别内容": document.body},
        {"字段": "响应示例", "识别内容": document.response_example},
        {"字段": "业务规则", "识别内容": document.business_rules},
        {"字段": "数据库校验", "识别内容": document.db_checks},
    ]


def _build_api_export_filename(project_name: str, module: str) -> str:
    parts = [part.strip() for part in [project_name, module, "接口测试用例"] if part.strip()]
    return "_".join(parts) + ".xlsx" if parts else "接口测试用例.xlsx"


def _render_step_preview() -> None:
    st.subheader("Step 2：生成计划预览与确认")
    pending_generation = st.session_state.get("pending_generation")
    if not pending_generation:
        st.info("填写需求后点击“生成计划预览”，这里会展示识别到的功能点。")
        return
    st.info("请检查识别到的功能点，取消不需要生成的项，再点击确认生成。")

    preview = build_generation_preview(
        pending_generation["requirement_text"],
        pending_generation["cases_per_feature"],
        feature_source_text=pending_generation.get("feature_source_text", ""),
        coverage_types=pending_generation.get("coverage_types", []),
    )
    selected_rows = _render_generation_preview(preview)
    selected_count = count_selected_rows(selected_rows)
    st.caption(f"当前选择参与生成的功能点：{selected_count} / {len(preview.feature_items)}")
    st.caption(f"选择后预计用例数：{selected_count * preview.cases_per_feature}")

    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("确认生成", type="primary", disabled=selected_count == 0):
            _run_confirmed_generation(pending_generation, selected_rows)
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


def _render_generation_preview(preview: GenerationPreview):
    col1, col2, col3 = st.columns(3)
    col1.metric("识别功能点", len(preview.feature_items))
    col2.metric("每功能点覆盖类型", preview.cases_per_feature)
    col3.metric("预计用例数", preview.estimated_case_count)
    if preview.coverage_types:
        st.caption("覆盖策略：" + "、".join(preview.coverage_types))

    for warning in preview.warnings:
        st.warning(warning)

    st.write("识别到的功能点")
    return st.data_editor(
        feature_items_to_rows(preview.feature_items),
        use_container_width=True,
        hide_index=True,
        key=f"feature_selection_editor_{abs(hash(preview.feature_source_text))}",
        column_config={
            "参与生成": st.column_config.CheckboxColumn("参与生成"),
            "需求片段": st.column_config.TextColumn("需求片段", width="large"),
        },
    )


def _run_confirmed_generation(pending_generation: dict, selected_rows=None) -> None:
    feature_source_text = selected_rows_to_feature_source(selected_rows)
    if not feature_source_text:
        st.warning("请至少选择一个功能点参与生成。")
        return

    with st.spinner("正在生成测试用例..."):
        result = generate_cases(
            requirement_text=pending_generation["requirement_text"],
            mode=pending_generation["mode"],
            cases_per_feature=pending_generation["cases_per_feature"],
            provider=pending_generation["provider"],
            generation_type=pending_generation["generation_type"],
            feature_source_text=feature_source_text,
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
    matrix_types = _quality_matrix_types(coverage_types)
    score = calculate_quality_score(cases, matrix_types)
    matrix = build_coverage_matrix(cases, matrix_types)
    covered_count = sum(1 for item in matrix if item.covered)

    st.subheader("质量概览")
    col1, col2, col3 = st.columns(3)
    col1.metric("质量评分", score.score)
    col2.metric("覆盖项", f"{covered_count}/{len(matrix)}")
    col3.metric("内容扣分", sum(item.points for item in score.deductions))
    st.caption(score.summary)
    st.caption("评分和覆盖提示仅用于辅助检查，最终仍需测试人员结合业务规则复核。")

    with st.expander("查看覆盖提示矩阵", expanded=False):
        st.dataframe(coverage_matrix_to_rows(matrix), use_container_width=True, hide_index=True)


def _render_quality_tab(cases: list[TestCase], coverage_types: list[str] | None = None) -> None:
    st.subheader("生成质量报告")
    matrix_types = _quality_matrix_types(coverage_types)
    score = calculate_quality_score(cases, matrix_types)
    matrix = build_coverage_matrix(cases, matrix_types)
    st.caption("覆盖检查：" + "、".join(matrix_types))
    issues = check_cases(cases, matrix_types)
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("质量评分", score.score)
    col2.metric("总用例数", len(cases))
    col3.metric("功能点数", len(_group_cases(cases)))
    col4.metric("质量提示", len(issues))
    col5.metric("覆盖项", f"{sum(1 for item in matrix if item.covered)}/{len(matrix)}")
    col6.metric("P1/P0", sum(1 for case in cases if case.priority in {"P0", "P1"}))
    st.info(score.summary)
    st.caption("评分和覆盖提示仅用于辅助检查，最终仍需测试人员结合业务规则复核。")

    with st.expander("覆盖提示矩阵", expanded=False):
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
    grouped: dict[str, list] = {}
    for issue in issues:
        grouped.setdefault(_issue_category(issue.message), []).append(issue)

    rows = []
    for category, group in grouped.items():
        case_ids = sorted({issue.case_id for issue in group if issue.case_id})
        rows.append(
            {
                "分类": category,
                "数量": len(group),
                "涉及用例": "、".join(case_ids[:12]) if case_ids else "-",
                "统一建议": _category_suggestion(category),
            }
        )
    return rows


def _warning_summary_rows(warnings: list[str]) -> list[dict[str, str | int]]:
    counter = Counter(_issue_category(warning) for warning in warnings)
    return [
        {
            "分类": category,
            "数量": count,
            "统一建议": _category_suggestion(category),
        }
        for category, count in counter.items()
    ]


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


def _category_suggestion(category: str) -> str:
    suggestions = {
        "基础字段": "补齐必填字段，优先检查编号、标题、步骤、预期结果和优先级。",
        "操作步骤": "补充可执行步骤，至少写清入口、操作动作和提交/查询动作。",
        "预期结果": "写清页面提示、状态变化、数据记录或接口返回，不只写“成功/正常”。",
        "测试数据": "补充账号、参数、边界值或业务数据编号。",
        "覆盖缺口": "根据缺失覆盖项补充对应类型用例，优先补异常、边界、权限和数据一致性。",
        "其他": "结合提示逐项复核。",
    }
    return suggestions.get(category, "结合提示逐项复核。")


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
    focus = st.selectbox("重新生成侧重点", REGENERATION_FOCUS_OPTIONS)
    if st.button("重新生成所选功能点"):
        config = st.session_state.get("last_generation_config", {})
        selected_cases = groups[selected_group]
        full_requirement_text = st.session_state.get("last_requirement_text", "")
        requirement_text = build_regeneration_requirement(selected_group, selected_cases, full_requirement_text, focus)
        focused_coverage_types = coverage_types_for_focus(focus, config.get("coverage_types", result.coverage_types))

        with st.spinner("正在重新生成所选功能点..."):
            regenerated = generate_cases(
                requirement_text=requirement_text,
                mode=config.get("mode", "规则生成"),
                cases_per_feature=config.get("cases_per_feature", 6),
                provider=config.get("provider", "DeepSeek"),
                generation_type=config.get("generation_type", "功能测试"),
                feature_source_text=f"{selected_cases[0].module}：{selected_cases[0].feature}",
                coverage_types=focused_coverage_types,
            )

        merged_cases = replace_group_preserving_case_ids(result.cases, selected_group, regenerated.cases)
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


def _quality_matrix_types(coverage_types: list[str] | None = None) -> list[str]:
    selected = normalize_coverage_types(coverage_types)
    matrix_types = []
    for coverage_type in QUALITY_MATRIX_TYPES + selected:
        if coverage_type not in matrix_types:
            matrix_types.append(coverage_type)
    return matrix_types


def _group_key(case: TestCase) -> str:
    module = case.module or "未指定模块"
    feature = case.feature or "未指定功能点"
    return f"{module} / {feature}"


def _set_generation_result(result: GenerationResult, export_filename: str) -> None:
    st.session_state["generation_result"] = result
    st.session_state["export_filename"] = export_filename
    st.session_state["edited_cases"] = result.cases
    _bump_generation_revision()


def _bump_generation_revision() -> None:
    st.session_state["generation_revision"] = st.session_state.get("generation_revision", 0) + 1

if __name__ == "__main__":
    main()
