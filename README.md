# AI 测试用例助手

本项目是一个本地 Streamlit 工具，用于把需求说明或接口文档转换为可编辑、可复核、可导出的测试设计结果。

当前目标不是自动执行测试，而是帮助测试人员更稳定地完成用例设计、覆盖检查和 Excel 交付。

## 当前能力

- 功能测试：需求解析、功能点预览、规则/AI 生成、表格编辑、质量检查、需求规则追踪、导出前复核、JSON 保存、Excel 导出。
- 接口测试：单接口文档解析、接口清单识别、参数风险分析、测试设计计划、规则生成、表格编辑、质量检查、导出前复核、Excel 导出。
- 接口辅助：可预览 `api_auto` YAML 草稿，但不承诺直接可执行。

## 暂不支持

- RAG、数据库、FastAPI、独立前端框架
- Swagger/OpenAPI、Postman 解析
- 真实接口执行
- pytest 自动化脚本生成
- 直接可执行的流程 YAML

## 运行

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Windows 下也可以运行：

```powershell
run_app.bat
```

## 环境变量

如需 AI 生成，在项目根目录创建 `.env`：

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini

DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

不要提交真实 API Key。

## 测试

```powershell
.\.venv\Scripts\python -m pytest -q
```

## 示例文件

功能测试示例：

```text
examples/housekeeping_appointment.txt
examples/housekeeping_dispatch.txt
examples/material_apply_approval.txt
examples/smart_home_device_bind.txt
examples/smart_home_alarm.txt
```

接口测试示例：

```text
examples/api_housekeeping_appointment.txt
examples/api_material_application.txt
examples/api_smart_home_device_control.md
```

## 使用说明

- 生成结果需要人工复核，尤其是业务规则、测试数据、断言和数据库校验。
- 导出前复核清单会提示明显错误、覆盖缺口和人工确认项，但不会强制阻断导出。
- `api_auto` YAML 只是草稿，需要人工补充 token、环境变量、复杂断言、数据库 SQL 和测试数据。

## 后续方向

- 继续提升接口文档识别稳定性。
- 收口接口页面展示，减少默认展开内容。
- 稳定后再做代码分包和文档整理。
