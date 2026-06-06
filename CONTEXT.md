# Project Context

## 项目定位

本项目是本地运行的 Streamlit 测试用例助手，目标是稳定完成“需求/接口文档输入 -> 用例生成 -> 表格编辑 -> 质量检查 -> Excel 导出”。

当前版本：`v0.3.4`

当前约束：

- 不引入 RAG、数据库、FastAPI、独立前端框架。
- 不做 Swagger/OpenAPI 解析。
- 不生成 pytest 接口自动化脚本。
- 不提交 `.env` 或真实 API Key。

## 当前能力

功能测试模式：

- 支持 `.txt` / `.md` / `.docx` 需求上传和模板填写。
- 支持规则生成和 AI 生成，AI 失败自动回退规则生成。
- 支持生成前功能点预览和勾选。
- 支持用例编辑、单功能点重新生成、质量评分、覆盖提示矩阵。
- 支持 JSON 历史保存/导入和 Excel 双 sheet 导出。

接口测试模式：

- 入口位于 `src/api/ui.py`，`app.py` 只负责模式选择和调用。
- 支持 `.txt` / `.md` 接口文档上传或粘贴。
- 支持接口字段解析和手动修正。
- 支持参数解析：参数名、必填、类型、规则、来源。
- 支持参数级规则生成：必填为空、类型错误、边界/非法值。
- 支持正常、鉴权、权限、业务规则、幂等、响应断言、数据库校验用例。
- 支持接口覆盖提示矩阵、接口质量检查、表格编辑。
- 接口 Excel 包含 `接口测试用例` 和 `接口质量报告`。

## 当前结构

```text
app.py
src/
  api/
    coverage_analyzer.py
    document_parser.py
    exporter.py
    models.py
    param_parser.py
    quality_checker.py
    rule_generator.py
    table_adapter.py
    ui.py
  ai_client.py
  coverage_analyzer.py
  coverage_config.py
  document_loader.py
  exporter.py
  feature_selection.py
  filename_utils.py
  generation_preview.py
  models.py
  persistence.py
  prompt_manager.py
  quality_checker.py
  quality_score.py
  regeneration.py
  requirement_parser.py
  rule_based_generator.py
  table_adapter.py
  text_utils.py
  title_utils.py
tests/
examples/
prompts/
outputs/
```

## 关键文件

- `app.py`：Streamlit 入口和模式选择。
- `src/api/ui.py`：接口测试页面 5 步流程。
- `src/api/models.py`：接口用例模型和接口 Excel 列定义。
- `src/api/document_parser.py`：接口文档标题解析。
- `src/api/param_parser.py`：接口参数解析。
- `src/api/rule_generator.py`：接口规则生成。
- `src/api/quality_checker.py`：接口质量检查。
- `src/api/coverage_analyzer.py`：接口覆盖提示矩阵。
- `src/api/exporter.py`：接口 Excel 双 sheet 导出。
- `src/models.py`：功能测试用例模型。
- `src/rule_based_generator.py`：功能测试规则生成。
- `src/ai_client.py`：DeepSeek/OpenAI 调用和回退。

## 接口用例字段

```text
用例编号、模块、接口名称、请求方法、接口路径、请求头、请求参数、请求体、
前置条件、操作步骤、预期状态码、断言点、数据库校验、变量提取、
优先级、用例类型、备注
```

## 验证方式

全量测试：

```powershell
.\.venv\Scripts\python -m pytest -q
```

最近一次重构后测试结果：`94 passed`。

人工验证重点：

- 功能测试页面能正常进入、预览、生成、编辑、导出。
- 接口测试页面能上传 `examples/api_smart_home_device_control.md` 并生成用例。
- 接口 Excel 应包含 `接口测试用例` 和 `接口质量报告`。

## 当前下一步

建议先稳定现有结构，不继续新增大功能。

可选后续：

- 统一功能测试和接口测试的历史 JSON 管理。
- 提升接口参数解析对表格化字段说明的支持。
- 观察接口规则生成结果，减少误判和重复用例。
- 稳定后再考虑功能测试模块继续分包。
