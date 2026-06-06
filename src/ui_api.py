from __future__ import annotations

import streamlit as st

from src.api_coverage_analyzer import api_coverage_matrix_to_rows, build_api_coverage_matrix
from src.api_document_parser import api_document_to_fields, fields_to_api_document, parse_api_document
from src.api_exporter import build_api_excel
from src.api_models import ApiDocument, ApiTestCase
from src.api_quality_checker import analyze_api_quality, api_quality_issues_to_rows, api_quality_summary
from src.api_rule_generator import generate_api_cases
from src.api_table_adapter import api_cases_to_rows, find_api_case_warnings, rows_to_api_cases
from src.document_loader import load_requirement_document


def render_api_test_page() -> None:
    st.title("接口测试用例编辑与导出")
    st.caption("当前接口测试模式为规则生成 MVP：支持接口文档识别、手动修正、规则生成、表格编辑和 Excel 导出，暂不接 AI。")

    document_text = _render_api_step_input()
    st.divider()
    document = _render_api_step_document_confirm()
    st.divider()
    _render_api_step_generate(document, bool(document_text.strip()))
    st.divider()
    edited_cases = _render_api_step_edit_and_quality(document)
    st.divider()
    _render_api_step_export(edited_cases, document)


def _render_api_step_input() -> str:
    st.subheader("Step 1：接口文档输入")
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
            st.warning("请先粘贴或上传接口文档内容。")
        else:
            parsed_document = parse_api_document(api_document_text)
            _apply_api_document_to_state(parsed_document)
            _clear_api_cases()
            st.session_state["api_document_parsed"] = True
            st.success("已解析接口文档，请检查并手动修正识别结果。")
    return api_document_text


def _render_api_step_document_confirm() -> ApiDocument:
    st.subheader("Step 2：解析结果确认与修正")
    if not st.session_state.get("api_document_parsed"):
        st.info("可以直接手动填写，也可以先上传或粘贴接口文档并点击“解析接口文档”。")

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
    return document


def _render_api_step_generate(document: ApiDocument, has_document_text: bool) -> None:
    st.subheader("Step 3：生成接口测试用例")
    if not has_document_text and not _has_basic_api_document(document):
        st.info("请先上传/粘贴接口文档，或至少手动填写接口名称、请求方法和接口路径。")

    if st.button("生成接口测试用例", type="primary"):
        st.session_state["api_cases"] = generate_api_cases(document)
        st.session_state["api_export_filename"] = _build_api_export_filename(document.project_name, document.module)
        st.session_state["api_generation_revision"] = st.session_state.get("api_generation_revision", 0) + 1
        st.success("已生成接口测试用例，可继续编辑并检查质量。")


def _render_api_step_edit_and_quality(document: ApiDocument) -> list[ApiTestCase]:
    st.subheader("Step 4：编辑与质量检查")
    api_cases: list[ApiTestCase] = st.session_state.get("api_cases") or []
    if not api_cases:
        st.info("生成接口测试用例后，这里会展示可编辑表格、覆盖提示矩阵和质量提示。")
        return []

    edited_rows = st.data_editor(
        api_cases_to_rows(api_cases),
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=f"api_case_editor_{st.session_state.get('api_generation_revision', 0)}",
    )
    edited_cases = rows_to_api_cases(edited_rows)
    st.session_state["api_cases"] = edited_cases

    warnings = find_api_case_warnings(edited_cases)
    if warnings:
        with st.expander(f"接口用例检查：发现 {len(warnings)} 个提示", expanded=False):
            for warning in warnings:
                st.warning(warning)

    _render_api_coverage_matrix(edited_cases)
    _render_api_quality_panel(edited_cases, document)
    return edited_cases


def _render_api_step_export(cases: list[ApiTestCase], document: ApiDocument) -> None:
    st.subheader("Step 5：导出接口 Excel")
    filename = st.text_input(
        "接口 Excel 文件名",
        value=st.session_state.get("api_export_filename", _build_api_export_filename(document.project_name, document.module)),
        key="api_export_filename",
    )
    st.download_button(
        f"导出接口 Excel（{len(cases)} 条，含质量报告）",
        data=build_api_excel(cases, document=document),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not cases,
    )


def _render_api_coverage_matrix(cases: list[ApiTestCase]) -> None:
    matrix = build_api_coverage_matrix(cases)
    covered_count = sum(1 for item in matrix if item.covered)
    with st.expander(f"接口覆盖提示矩阵（{covered_count}/{len(matrix)}）", expanded=False):
        st.dataframe(api_coverage_matrix_to_rows(matrix), use_container_width=True, hide_index=True)


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
    _clear_api_cases()
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


def _has_basic_api_document(document: ApiDocument) -> bool:
    return bool(document.api_name.strip() or document.path.strip())


def _clear_api_cases() -> None:
    st.session_state.pop("api_cases", None)
    st.session_state["api_generation_revision"] = st.session_state.get("api_generation_revision", 0) + 1
