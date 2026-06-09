from __future__ import annotations

import streamlit as st

from src.api.coverage_analyzer import API_COVERAGE_ITEMS, api_coverage_matrix_to_rows, build_api_coverage_matrix
from src.api.design_plan import (
    API_GENERATION_STRATEGIES,
    build_api_design_plan,
    business_rule_risks_to_rows,
    design_plan_summary_rows,
    param_risks_to_rows,
)
from src.api.document_parser import api_document_to_fields, fields_to_api_document, parse_api_document
from src.api.exporter import build_api_excel
from src.api.models import ApiDocument, ApiTestCase
from src.api.quality_checker import analyze_api_quality, api_quality_issues_to_rows, api_quality_summary
from src.api.rule_generator import generate_api_cases
from src.api.table_adapter import api_cases_to_rows, find_api_case_warnings, rows_to_api_cases
from src.document_loader import load_requirement_document


def render_api_test_page() -> None:
    st.title("接口测试用例编辑与导出")
    st.caption("当前接口测试模式为规则生成 MVP：支持接口文档识别、手动修正、规则生成、表格编辑和 Excel 导出，暂不接 AI。")

    _render_api_progress_summary()
    document_text = _render_api_step_input()
    st.divider()
    document = _render_api_step_document_confirm()
    _render_api_current_summary(document)
    st.divider()
    design_options = _render_api_step_design_plan(document)
    st.divider()
    _render_api_step_generate(document, bool(document_text.strip()), design_options)
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

    with st.expander("基础信息", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("项目/系统名称", key="api_project_name", placeholder="例如：智控家监测系统")
            module = st.text_input("业务模块", key="api_module", placeholder="例如：设备控制")
            api_name = st.text_input("接口名称", key="api_name", placeholder="例如：设备控制接口")
        with col2:
            method = st.selectbox("请求方法", ["GET", "POST", "PUT", "PATCH", "DELETE"], index=1, key="api_method")
            path = st.text_input("接口路径", key="api_path", placeholder="例如：/api/devices/{deviceId}/control")
            auth = st.text_input("鉴权方式", key="api_auth", placeholder="例如：Bearer Token / Session / 无")

    with st.expander("请求信息", expanded=True):
        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            headers = st.text_area("请求头", key="api_headers", height=100, placeholder="例如：Authorization、Content-Type")
            params = st.text_area("请求参数 / 字段说明", key="api_params", height=160, placeholder="例如：deviceId 设备ID，必填")
        with detail_col2:
            body = st.text_area("请求体", key="api_body", height=280, placeholder='例如：{"action": "open"}')

    with st.expander("响应与校验", expanded=True):
        check_col1, check_col2 = st.columns(2)
        with check_col1:
            response_example = st.text_area("响应示例", key="api_response_example", height=160, placeholder="可填写成功响应和失败响应")
            db_checks = st.text_area("数据库校验", key="api_db_checks", height=120, placeholder="例如：设备状态记录更新")
        with check_col2:
            business_rules = st.text_area("业务规则", key="api_business_rules", height=290, placeholder="例如：设备在线且用户有权限才允许控制")

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


def _render_api_current_summary(document: ApiDocument) -> None:
    st.caption("当前接口摘要")
    st.dataframe(
        [
            {
                "接口名称": document.api_name.strip() or "-",
                "请求方法": document.method.strip() or "-",
                "接口路径": document.path.strip() or "-",
                "业务模块": document.module.strip() or "-",
            }
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_api_step_design_plan(document: ApiDocument) -> dict[str, object]:
    st.subheader("Step 3：测试设计计划")
    if not _has_basic_api_document(document):
        st.info("填写或解析接口文档后，这里会展示参数风险、业务规则、覆盖项和预计用例数量。")

    col1, col2 = st.columns([1, 2])
    with col1:
        strategy = st.selectbox(
            "生成策略",
            API_GENERATION_STRATEGIES,
            index=1,
            key="api_generation_strategy",
            help="精简适合快速冒烟；标准适合日常设计；完整会尽量展开参数规则。",
        )
    with col2:
        coverage_types = st.multiselect(
            "覆盖项选择",
            API_COVERAGE_ITEMS,
            default=st.session_state.get("api_selected_coverage_types", API_COVERAGE_ITEMS),
            key="api_selected_coverage_types",
        )

    preview_plan = build_api_design_plan(document, coverage_types=coverage_types, strategy=strategy)
    business_rows = business_rule_risks_to_rows(preview_plan.business_rule_risks)
    if business_rows:
        st.markdown("**业务规则识别**")
        edited_business_rows = st.data_editor(
            business_rows,
            use_container_width=True,
            hide_index=True,
            disabled=["规则内容", "风险类型", "建议测试点"],
            key="api_business_rule_plan_editor",
        )
        included_business_rules = _included_business_rules_from_rows(edited_business_rows)
    else:
        st.info("未识别到业务规则。可以在 Step 2 的“业务规则”中补充后再生成。")
        included_business_rules = []

    plan = build_api_design_plan(
        document,
        coverage_types=coverage_types,
        strategy=strategy,
        included_business_rules=included_business_rules if business_rows else None,
    )

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("预计用例数", plan.estimated_case_count)
    metric_col2.metric("参数风险", len(plan.param_risks))
    metric_col3.metric("业务规则", len([rule for rule in plan.business_rule_risks if rule.included]))
    metric_col4.metric("数据库校验", len(plan.db_checks))

    st.markdown("**计划摘要**")
    st.dataframe(design_plan_summary_rows(plan), use_container_width=True, hide_index=True)

    st.markdown("**参数风险分析**")
    if plan.param_risks:
        st.dataframe(param_risks_to_rows(plan.param_risks), use_container_width=True, hide_index=True)
    else:
        st.info("未识别到参数。可以在 Step 2 的“请求参数 / 字段说明”或“请求体”中补充。")

    if plan.db_checks:
        with st.expander("数据库校验识别", expanded=False):
            st.dataframe([{"数据库校验": item} for item in plan.db_checks], use_container_width=True, hide_index=True)

    return {
        "coverage_types": plan.coverage_types,
        "strategy": plan.strategy,
        "business_rules": [rule.content for rule in plan.business_rule_risks if rule.included],
    }


def _render_api_step_generate(document: ApiDocument, has_document_text: bool, design_options: dict[str, object]) -> None:
    st.subheader("Step 4：生成接口测试用例")
    if not has_document_text and not _has_basic_api_document(document):
        st.info("请先上传/粘贴接口文档，或至少手动填写接口名称、请求方法和接口路径。")

    current_cases: list[ApiTestCase] = st.session_state.get("api_cases") or []
    if current_cases:
        _render_api_case_summary(current_cases)

    if st.button("生成接口测试用例", type="primary"):
        st.session_state["api_cases"] = generate_api_cases(
            document,
            coverage_types=list(design_options.get("coverage_types", [])),
            strategy=str(design_options.get("strategy", "标准")),
            business_rules=list(design_options.get("business_rules", [])),
        )
        st.session_state["api_export_filename"] = _build_api_export_filename(document.project_name, document.module)
        st.session_state["api_generation_revision"] = st.session_state.get("api_generation_revision", 0) + 1
        st.success("已生成接口测试用例，可继续编辑并检查质量。")


def _render_api_step_edit_and_quality(document: ApiDocument) -> list[ApiTestCase]:
    st.subheader("Step 5：编辑与质量检查")
    api_cases: list[ApiTestCase] = st.session_state.get("api_cases") or []
    if not api_cases:
        st.info("生成接口测试用例后，这里会展示可编辑表格、覆盖提示矩阵和质量提示。")
        return []

    _render_api_review_summary(api_cases, document)
    _render_api_case_groups(api_cases)
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

    st.markdown("**接口质量检查**")
    quality_col1, quality_col2 = st.columns(2)
    with quality_col1:
        _render_api_coverage_matrix(edited_cases)
    with quality_col2:
        _render_api_quality_panel(edited_cases, document, show_metrics=False)
    return edited_cases


def _render_api_step_export(cases: list[ApiTestCase], document: ApiDocument) -> None:
    st.subheader("Step 6：导出接口 Excel")
    if not cases:
        st.info("生成接口测试用例后，可导出包含接口测试用例和接口质量报告的 Excel。")

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


def _render_api_progress_summary() -> None:
    cases: list[ApiTestCase] = st.session_state.get("api_cases") or []
    parsed = bool(st.session_state.get("api_document_parsed"))
    has_text = bool(str(st.session_state.get("api_document_text", "")).strip())
    issues = analyze_api_quality(cases) if cases else []
    error_count = sum(1 for issue in issues if issue.severity == "错误")
    warning_count = sum(1 for issue in issues if issue.severity == "警告")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("文档输入", "已输入" if has_text else "待输入")
    col2.metric("解析结果", "已解析" if parsed else "待确认")
    col3.metric("接口用例", len(cases))
    col4.metric("质量提示", f"{error_count} 错 / {warning_count} 警")
    col5.metric("导出状态", "可导出" if cases else "待生成")


def _render_api_case_summary(cases: list[ApiTestCase]) -> None:
    case_types = sorted({case.case_type for case in cases if case.case_type})
    matrix = build_api_coverage_matrix(cases)
    covered_count = sum(1 for item in matrix if item.covered)
    col1, col2, col3 = st.columns(3)
    col1.metric("当前用例数", len(cases))
    col2.metric("用例类型", len(case_types))
    col3.metric("覆盖项", f"{covered_count}/{len(matrix)}")
    st.caption("重新生成会覆盖当前接口用例；如已手动编辑，建议先导出或确认后再重新生成。")


def _render_api_review_summary(cases: list[ApiTestCase], document: ApiDocument) -> None:
    matrix = build_api_coverage_matrix(cases)
    covered_count = sum(1 for item in matrix if item.covered)
    issues = analyze_api_quality(cases, document)
    summary = api_quality_summary(cases, issues)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("用例数", len(cases))
    col2.metric("覆盖项", f"{covered_count}/{len(matrix)}")
    col3.metric("错误", summary["error_count"])
    col4.metric("警告", summary["warning_count"])
    col5.metric("建议", summary.get("suggestion_count", 0))


def _render_api_coverage_matrix(cases: list[ApiTestCase]) -> None:
    matrix = build_api_coverage_matrix(cases)
    covered_count = sum(1 for item in matrix if item.covered)
    with st.expander(f"接口覆盖提示矩阵（{covered_count}/{len(matrix)}）", expanded=False):
        st.dataframe(api_coverage_matrix_to_rows(matrix), use_container_width=True, hide_index=True)


def _render_api_quality_panel(cases: list[ApiTestCase], document: ApiDocument, show_metrics: bool = True) -> None:
    issues = analyze_api_quality(cases, document)
    summary = api_quality_summary(cases, issues)

    st.markdown("**质量提示**")
    if show_metrics:
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("用例数", summary["case_count"])
        col2.metric("覆盖类型", summary["covered_categories"])
        col3.metric("错误", summary["error_count"])
        col4.metric("警告", summary["warning_count"])
        col5.metric("建议", summary.get("suggestion_count", 0))
    st.caption("接口质量检查用于辅助发现断言、鉴权、参数和数据库校验缺口，最终仍需结合接口文档和业务规则复核。")

    if not issues:
        st.success("接口用例暂无明显质量提示。")
        return

    with st.expander(f"查看接口质量提示（{summary['issue_count']} 项）", expanded=False):
        st.dataframe(api_quality_issues_to_rows(issues), use_container_width=True, hide_index=True)


def _render_api_case_groups(cases: list[ApiTestCase]) -> None:
    grouped: dict[str, list[str]] = {
        "基础正向": [],
        "参数校验": [],
        "鉴权权限": [],
        "业务规则": [],
        "幂等重复提交": [],
        "响应断言": [],
        "数据库一致性": [],
    }
    for case in cases:
        group_name = _api_case_group_name(case)
        grouped.setdefault(group_name, []).append(f"{case.case_id} {case.case_type}")

    with st.expander("按场景分组查看", expanded=True):
        rows = [
            {"场景分组": name, "用例数": len(case_ids), "命中用例": "、".join(case_ids) if case_ids else "-"}
            for name, case_ids in grouped.items()
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _api_case_group_name(case: ApiTestCase) -> str:
    text = f"{case.case_type} {case.remark} {case.steps} {case.assertions}"
    if any(keyword in text for keyword in ["正常请求", "合法请求"]):
        return "基础正向"
    if any(keyword in text for keyword in ["参数校验", "边界", "必填", "类型错误", "非法"]):
        return "参数校验"
    if any(keyword in text for keyword in ["鉴权", "权限", "401", "403", "Token"]):
        return "鉴权权限"
    if "业务规则" in text:
        return "业务规则"
    if any(keyword in text for keyword in ["幂等", "重复"]):
        return "幂等重复提交"
    if any(keyword in text for keyword in ["响应断言", "响应字段", "字段类型"]):
        return "响应断言"
    if any(keyword in text for keyword in ["数据库", "数据一致"]):
        return "数据库一致性"
    return "基础正向"


def _included_business_rules_from_rows(rows) -> list[str]:
    if hasattr(rows, "to_dict"):
        rows = rows.to_dict("records")
    return [
        str(row.get("规则内容", "")).strip()
        for row in rows
        if row.get("是否参与生成") and str(row.get("规则内容", "")).strip()
    ]


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
