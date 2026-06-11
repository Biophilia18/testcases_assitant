# AI 辅助测试用例生成与导出工具

本项目是一个本地 Streamlit 测试用例助手，目标是把需求或接口文档稳定转换为可编辑、可解释、可导出的测试设计结果。

## 当前能力

- 功能测试：需求解析、功能点预览、规则/AI 生成、用例编辑、质量检查、JSON 保存、Excel 导出。
- 接口测试：单接口文档解析、接口清单识别、文档可信度提示、参数风险分析、规则生成、用例编辑、质量检查、Excel 导出。
- 接口自动化辅助：可导出 `api_auto` YAML 草稿，但不承诺直接可执行。
- 示例验收：内置爱家政、物资后勤、智控家等接口示例，覆盖 GET/POST/PUT/PATCH/DELETE。

暂不支持：RAG、数据库、FastAPI、独立前端、Swagger/OpenAPI、Postman、真实接口执行、pytest 脚本生成。

## 运行

```powershell
pip install -r requirements.txt
streamlit run app.py
```

或在 Windows 下运行：

```powershell
run_app.bat
```

## 环境变量

在项目根目录创建 `.env`：

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini

DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

不要提交真实 API Key。

## 接口测试模式说明

当前接口模式优先支持“单接口测试设计”。如果粘贴模块级多接口文档，工具会先识别接口清单，用户选择一个接口后再进入单接口生成流程。

接口清单会展示：

- 参数数
- 是否有鉴权
- 是否有业务规则
- 是否有数据库校验
- 复杂度：低 / 中 / 高

生成前会做接口文档可信度检查：缺少请求方法或接口路径时不会生成；缺少参数、鉴权、响应示例或业务规则时只提示，不会凭空编造对应测试点。

参数识别支持普通文本和 Markdown 表格，会区分路径参数、查询参数和请求体字段，避免把路径参数误拼成 URL query。

生成后可导出：

- 接口测试 Excel
- `api_auto` YAML 草稿

YAML 草稿需要人工补充或复核 token、环境变量、复杂断言、数据库 SQL 和测试数据。

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

## 后续方向

- 继续提升接口清单识别稳定性。
- 强化接口 YAML 草稿的自动化就绪度检查。
- 稳定后再做模块分包和文档整理。
