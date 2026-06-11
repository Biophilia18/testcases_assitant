from __future__ import annotations

import streamlit as st

from src.api.coverage_analyzer import API_COVERAGE_ITEMS, api_coverage_matrix_to_rows, build_api_coverage_matrix
from src.api.api_auto_exporter import build_api_auto_preview_rows, build_api_auto_yaml
from src.api.design_plan import (
    API_GENERATION_STRATEGIES,
    build_api_design_plan,
    business_rule_risks_to_rows,
    param_risks_to_rows,
    plan_items_to_rows,
    rows_to_plan_items,
    split_api_text_items,
)
from src.api.document_candidates import api_document_candidates_to_rows, candidate_complexity_label, extract_api_document_candidates
from src.api.document_parser import api_document_to_fields, fields_to_api_document, parse_api_document
from src.api.examples import API_EXAMPLE_BY_NAME, API_EXAMPLE_DOCUMENTS
from src.api.exporter import build_api_excel
from src.api.models import ApiDocument, ApiTestCase
from src.api.param_parser import parse_api_params
from src.api.quality_checker import analyze_api_quality, api_quality_issues_to_rows, api_quality_summary
from src.api.reliability import (
    api_document_generation_blockers,
    api_document_reliability_level,
    api_reliability_issues_to_rows,
    assess_api_document_reliability,
)
from src.api.rule_generator import build_api_plan_trace_rows, generate_api_cases
from src.api.table_adapter import api_cases_to_rows, find_api_case_warnings, rows_to_api_cases
from src.document_loader import load_requirement_document


def render_api_test_page() -> None:
    st.title("接口测试用例编辑与导出")
    st.caption("当前接口模式重点支持单个接口的测试设计：识别接口文档、生成用例、编辑复核并导出 Excel；api_auto YAML 仅作为草稿导出。")

    _render_api_progress_summary()
    document_text = _render_api_step_input()
    st.divider()
    document = _render_api_step_document_confirm()
    _render_api_current_summary(document)
    _render_api_reliability_panel(document)
    st.divider()
    design_options = _render_api_step_design_plan(document)
    st.divider()
    _render_api_step_generate(document, bool(document_text.strip()), design_options)
    st.divider()
    edited_cases = _render_api_step_edit_and_quality(document)
    st.divider()
    _render_api_step_export(edited_cases, document)


def _render_api_step_input() -> str:
    st.subheader("Step 1：接口文档输入（单接口）")
    st.caption("当前阶段优先处理一个接口的文档。若粘贴的是模块级多接口文档，建议先选取其中一个接口片段进行设计。")
    example_col1, example_col2 = st.columns([2, 1])
    with example_col1:
        example_name = st.selectbox(
            "接口示例文档",
            ["不使用示例"] + [example.name for example in API_EXAMPLE_DOCUMENTS],
            key="api_example_document_name",
        )
    with example_col2:
        st.write("")
        st.write("")
        if st.button("填充示例文档", disabled=example_name == "不使用示例"):
            _apply_api_example_document(example_name)

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
            _parse_and_apply_api_document_text(api_document_text)
    _render_api_candidate_selector()
    _render_current_api_candidate_status()
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
            method = st.selectbox("请求方法", ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], index=1, key="api_method")
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


def _render_api_reliability_panel(document: ApiDocument) -> None:
    issues = assess_api_document_reliability(document)
    if not issues:
        st.success("接口文档可信度：较高。仍建议在生成后复核断言、测试数据和数据库校验。")
        return

    level = api_document_reliability_level(issues)
    warning_count = len([issue for issue in issues if issue.severity == "警告"])
    blocker_count = len([issue for issue in issues if issue.severity == "错误"])
    suggestion_count = len([issue for issue in issues if issue.severity == "建议"])
    caption = f"接口文档可信度：{level}。错误 {blocker_count} 个，警告 {warning_count} 个，建议 {suggestion_count} 个。"
    if blocker_count:
        st.error(caption)
    elif warning_count:
        st.warning(caption)
    else:
        st.info(caption)

    with st.expander("查看接口文档可信度提示", expanded=bool(blocker_count)):
        st.dataframe(api_reliability_issues_to_rows(issues), use_container_width=True, hide_index=True)


def _render_api_step_design_plan(document: ApiDocument) -> dict[str, object]:
    st.subheader("Step 3：生成前预览与确认")
    if not _has_basic_api_document(document):
        st.info("填写或解析接口文档后，这里会展示接口概要、覆盖项、预计用例数量和高级设计选项。")

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
    with st.expander("高级设计选项：业务规则、参数风险与计划项", expanded=False):
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

        st.markdown("**参数风险分析**")
        if plan.param_risks:
            edited_param_rows = st.data_editor(
                param_risks_to_rows(plan.param_risks),
                use_container_width=True,
                hide_index=True,
                disabled=["参数名", "参数来源", "是否必填", "参数类型", "识别到的规则", "风险类型", "建议测试点"],
                key="api_param_risk_plan_editor",
            )
            included_param_names = _included_param_names_from_rows(edited_param_rows)
        else:
            st.info("未识别到参数。可以在 Step 2 的“请求参数 / 字段说明”或“请求体”中补充。")
            included_param_names = []

        plan = build_api_design_plan(
            document,
            coverage_types=coverage_types,
            strategy=strategy,
            included_business_rules=included_business_rules if business_rows else None,
            included_param_names=included_param_names if plan.param_risks else None,
        )

        st.markdown("**计划生成项**")
        plan_rows = plan_items_to_rows(plan.plan_items)
        if plan_rows:
            edited_plan_rows = st.data_editor(
                plan_rows,
                use_container_width=True,
                hide_index=True,
                disabled=["计划ID", "覆盖项", "来源类型", "来源名称", "风险类型", "建议测试点", "预计用例数"],
                key="api_plan_item_editor",
            )
            plan_items = rows_to_plan_items(edited_plan_rows)
        else:
            st.info("当前未形成计划生成项。请检查覆盖项选择或补充接口文档信息。")
            plan_items = []

    estimated_count = sum(item.estimated_count for item in plan_items if item.included)
    plan.estimated_case_count = estimated_count
    plan.planned_case_types = _planned_case_types_from_items(plan_items)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("预计用例数", plan.estimated_case_count)
    metric_col2.metric("识别参数", len(plan.param_risks))
    metric_col3.metric("业务规则", len([rule for rule in plan.business_rule_risks if rule.included]))
    metric_col4.metric("数据库校验", len(plan.db_checks))

    st.markdown("**生成前预览**")
    st.dataframe(_api_generation_preview_rows(document, plan), use_container_width=True, hide_index=True)

    if plan.db_checks:
        with st.expander("数据库校验识别", expanded=False):
            st.dataframe([{"数据库校验": item} for item in plan.db_checks], use_container_width=True, hide_index=True)

    return {
        "coverage_types": plan.coverage_types,
        "strategy": plan.strategy,
        "business_rules": [rule.content for rule in plan.business_rule_risks if rule.included],
        "plan_items": plan_items,
    }


def _render_api_step_generate(document: ApiDocument, has_document_text: bool, design_options: dict[str, object]) -> None:
    st.subheader("Step 4：生成接口测试用例")
    if not has_document_text and not _has_basic_api_document(document):
        st.info("请先上传/粘贴接口文档，或至少手动填写接口名称、请求方法和接口路径。")

    current_cases: list[ApiTestCase] = st.session_state.get("api_cases") or []
    if current_cases:
        _render_api_case_summary(current_cases)

    blockers = api_document_generation_blockers(document)
    if blockers:
        st.error("接口文档缺少必要信息，已暂时禁用生成。请先补充请求方法和接口路径。")

    if st.button("生成接口测试用例", type="primary", disabled=bool(blockers)):
        plan_items = list(design_options.get("plan_items", []))
        st.session_state["api_cases"] = generate_api_cases(
            document,
            coverage_types=list(design_options.get("coverage_types", [])),
            strategy=str(design_options.get("strategy", "标准")),
            business_rules=list(design_options.get("business_rules", [])),
            plan_items=plan_items,
        )
        st.session_state["api_last_plan_items"] = plan_items
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

    _render_api_generation_self_check(edited_cases, document)
    _render_api_case_groups(edited_cases)
    _render_api_plan_trace(edited_cases)

    st.markdown("**接口质量检查**")
    quality_col1, quality_col2 = st.columns(2)
    with quality_col1:
        _render_api_coverage_matrix(edited_cases)
    with quality_col2:
        _render_api_quality_panel(edited_cases, document, show_metrics=False)
    return edited_cases


def _render_api_step_export(cases: list[ApiTestCase], document: ApiDocument) -> None:
    st.subheader("Step 6：保存与导出")
    if not cases:
        st.info("生成接口测试用例后，可导出 Excel，也可预览并下载 api_auto YAML。")

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

    with st.expander("api_auto YAML 导出预览", expanded=bool(cases)):
        if not cases:
            st.info("生成接口测试用例后，这里会展示可供 api_auto 使用的 YAML 预览。")
            return

        st.caption("这是面向 api_auto 的 YAML 草稿预览，不承诺导出后可直接执行。落地前需要人工补充或复核 token、环境变量、复杂断言、数据库 SQL 和测试数据。")
        st.dataframe(build_api_auto_preview_rows(cases), use_container_width=True, hide_index=True)
        yaml_text = build_api_auto_yaml(cases, document)
        st.code(yaml_text, language="yaml")
        yaml_filename = filename.rsplit(".", 1)[0] + ".yaml" if filename else "api_auto_cases.yaml"
        st.download_button(
            "下载 api_auto YAML",
            data=yaml_text.encode("utf-8"),
            file_name=yaml_filename,
            mime="text/yaml",
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


def _render_api_generation_self_check(cases: list[ApiTestCase], document: ApiDocument) -> None:
    params = parse_api_params(document)
    business_rules = split_api_text_items(document.business_rules)
    coverage_matrix = build_api_coverage_matrix(cases)
    covered_count = sum(1 for item in coverage_matrix if item.covered)
    issues = analyze_api_quality(cases, document)
    review_items = _manual_review_items(cases, document, issues)

    with st.expander("生成质量自检摘要", expanded=True):
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("识别参数数", len(params))
        col2.metric("业务规则数", len(business_rules))
        col3.metric("生成用例数", len(cases))
        col4.metric("覆盖项数量", f"{covered_count}/{len(coverage_matrix)}")
        col5.metric("人工复核项", len(review_items))
        st.dataframe(
            [{"建议人工复核项": item} for item in review_items] or [{"建议人工复核项": "暂无明显复核提示，仍建议结合真实接口文档抽查。"}],
            use_container_width=True,
            hide_index=True,
        )


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

    with st.expander("按场景分组查看", expanded=False):
        rows = [
            {"场景分组": name, "用例数": len(case_ids), "命中用例": "、".join(case_ids) if case_ids else "-"}
            for name, case_ids in grouped.items()
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_api_plan_trace(cases: list[ApiTestCase]) -> None:
    plan_items = st.session_state.get("api_last_plan_items") or []
    if not plan_items:
        return

    with st.expander("测试计划覆盖追踪", expanded=False):
        st.dataframe(build_api_plan_trace_rows(plan_items, cases), use_container_width=True, hide_index=True)


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


def _included_param_names_from_rows(rows) -> list[str]:
    if hasattr(rows, "to_dict"):
        rows = rows.to_dict("records")
    return [
        str(row.get("参数名", "")).strip()
        for row in rows
        if row.get("是否参与生成") and str(row.get("参数名", "")).strip()
    ]


def _planned_case_types_from_items(plan_items) -> list[str]:
    planned = []
    for item in plan_items:
        if item.included and item.coverage_type not in planned:
            planned.append(item.coverage_type)
    return planned


def _manual_review_items(cases: list[ApiTestCase], document: ApiDocument, issues) -> list[str]:
    review_items = []
    if any(issue.severity in {"警告", "建议"} for issue in issues):
        review_items.append("质量检查中存在警告或建议，需要确认断言、测试数据和覆盖范围。")
    if document.auth.strip():
        review_items.append("接口包含鉴权，需确认 token 获取方式、权限账号和过期场景。")
    if document.db_checks.strip():
        review_items.append("接口包含数据库校验，需补充真实 SQL、期望值和测试环境数据准备方式。")
    if any("${token}" in case.headers or "{token}" in case.headers for case in cases):
        review_items.append("YAML 草稿中包含 token 占位，需要在 api_auto 中准备登录或上下文变量。")
    if not any(case.case_type == "响应断言" for case in cases):
        review_items.append("未生成独立响应断言用例，建议确认响应字段、业务码和错误码。")
    return review_items


def _apply_api_example_document(example_name: str) -> None:
    example = API_EXAMPLE_BY_NAME.get(example_name)
    if not example:
        return

    st.session_state["api_document_text"] = example.text
    _parse_and_apply_api_document_text(example.text)
    st.success(f"已填充示例文档：{example.name}。")


def _apply_uploaded_api_document(uploaded_file) -> None:
    upload_key = f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"
    if st.session_state.get("last_api_document_upload") == upload_key:
        return

    try:
        raw_text = load_requirement_document(uploaded_file.name, uploaded_file.read())
    except Exception as exc:
        st.error(f"接口文档读取失败：{exc}")
        return

    st.session_state["api_document_text"] = raw_text
    _parse_and_apply_api_document_text(raw_text)
    st.session_state["last_api_document_upload"] = upload_key
    st.success("已读取并解析接口文档，请检查解析结果并手动修正。")


def _parse_and_apply_api_document_text(text: str) -> None:
    candidates = extract_api_document_candidates(text)
    st.session_state["api_document_candidates"] = candidates

    if len(candidates) > 1:
        selected_candidate = candidates[0]
        st.session_state["api_selected_candidate_index"] = selected_candidate.index
        _apply_api_document_to_state(selected_candidate.document)
        _clear_api_cases()
        st.session_state["api_document_parsed"] = True
        st.info(f"识别到 {len(candidates)} 个接口，已默认选择第 1 个。可在接口清单中切换。")
        return

    document = candidates[0].document if candidates else parse_api_document(text)
    st.session_state["api_document_candidates"] = []
    st.session_state.pop("api_selected_candidate_index", None)
    _apply_api_document_to_state(document)
    _clear_api_cases()
    st.session_state["api_document_parsed"] = True
    st.success("已解析接口文档，请检查并手动修正识别结果。")


def _render_api_candidate_selector() -> None:
    candidates = st.session_state.get("api_document_candidates") or []
    if len(candidates) <= 1:
        return

    with st.expander(f"识别到的接口清单（{len(candidates)} 个）", expanded=True):
        st.caption("当前不批量生成。请选择一个接口进入后续单接口测试设计流程。")
        _render_api_candidate_summary(candidates)
        st.dataframe(api_document_candidates_to_rows(candidates), use_container_width=True, hide_index=True)
        selected_index = st.selectbox(
            "选择要设计的接口",
            [candidate.index for candidate in candidates],
            format_func=lambda index: next(candidate.display_name for candidate in candidates if candidate.index == index),
            key="api_candidate_selector",
        )
        if st.button("使用选中的接口"):
            selected_candidate = next(candidate for candidate in candidates if candidate.index == selected_index)
            st.session_state["api_document_text"] = selected_candidate.source_text
            st.session_state["api_selected_candidate_index"] = selected_candidate.index
            _apply_api_document_to_state(selected_candidate.document)
            _clear_api_cases()
            st.session_state["api_document_parsed"] = True
            st.success(f"已切换到接口：{selected_candidate.display_name}")


def _render_current_api_candidate_status() -> None:
    candidates = st.session_state.get("api_document_candidates") or []
    selected_index = st.session_state.get("api_selected_candidate_index")
    if len(candidates) <= 1 or not selected_index:
        return

    selected_candidate = next((candidate for candidate in candidates if candidate.index == selected_index), None)
    if not selected_candidate:
        return

    complexity = candidate_complexity_label(selected_candidate.document)
    st.info(f"当前正在设计：第 {selected_candidate.index} 个接口，{selected_candidate.display_name}，复杂度：{complexity}")


def _render_api_candidate_summary(candidates) -> None:
    auth_count = sum(1 for candidate in candidates if candidate.document.auth.strip())
    param_count = sum(1 for candidate in candidates if parse_api_params(candidate.document))
    rule_count = sum(1 for candidate in candidates if candidate.document.business_rules.strip())
    db_count = sum(1 for candidate in candidates if candidate.document.db_checks.strip())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("接口数", len(candidates))
    col2.metric("有参数", param_count)
    col3.metric("有鉴权", auth_count)
    col4.metric("有规则/DB", f"{rule_count}/{db_count}")


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


def _api_generation_preview_rows(document: ApiDocument, plan) -> list[dict[str, str | int]]:
    included_plan_items = [item for item in plan.plan_items if item.included]
    return [
        {"预览项": "当前处理范围", "内容": "单接口测试设计"},
        {"预览项": "接口名称", "内容": document.api_name or "-"},
        {"预览项": "请求方法", "内容": document.method or "-"},
        {"预览项": "接口路径", "内容": document.path or "-"},
        {"预览项": "覆盖项", "内容": "、".join(plan.coverage_types) or "-"},
        {"预览项": "计划生成类型", "内容": "、".join(plan.planned_case_types) or "-"},
        {"预览项": "计划生成项", "内容": len(included_plan_items)},
        {"预览项": "预计生成用例数", "内容": plan.estimated_case_count},
        {"预览项": "api_auto YAML 草稿", "内容": _api_auto_draft_readiness(document)},
        {"预览项": "说明", "内容": "参数风险和计划项可在上方高级设计选项中调整。"},
    ]


def _api_auto_draft_readiness(document: ApiDocument) -> str:
    if not document.method or not document.path:
        return "缺少请求方法或接口路径，暂不适合导出"
    if not document.response_example:
        return "可导出基础草稿，建议补响应示例"
    if document.auth and not document.headers:
        return "可导出基础草稿，需补鉴权请求头"
    return "可导出基础草稿，仍需人工复核"


def _build_api_export_filename(project_name: str, module: str) -> str:
    parts = [part.strip() for part in [project_name, module, "接口测试用例"] if part.strip()]
    return "_".join(parts) + ".xlsx" if parts else "接口测试用例.xlsx"


def _has_basic_api_document(document: ApiDocument) -> bool:
    return bool(document.api_name.strip() or document.path.strip())


def _clear_api_cases() -> None:
    st.session_state.pop("api_cases", None)
    st.session_state["api_generation_revision"] = st.session_state.get("api_generation_revision", 0) + 1
