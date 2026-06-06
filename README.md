# AI 辅助测试用例生成与导出工具

基于 Streamlit 的本地测试用例生成、编辑和导出工具。

当前版本：`v0.3.4`

## 当前能力

- 功能测试：需求上传/填写、规则生成、AI 生成、生成前预览、用例编辑、质量检查、历史 JSON、Excel 双 sheet 导出。
- 接口测试：md/txt 接口文档上传或粘贴、字段解析、参数解析、参数级规则生成、覆盖提示矩阵、质量检查、用例编辑、Excel 双 sheet 导出。
- AI 服务：支持 DeepSeek 和 OpenAI；未配置 Key 或调用失败时自动回退规则生成。
- 示例文件：`examples/` 内含功能测试需求和接口文档示例。

暂不支持：RAG、数据库、FastAPI、独立前端框架、Swagger/OpenAPI 解析、接口自动化脚本生成、登录系统。

## 运行

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Windows 也可以运行：

```powershell
run_app.bat
```

通常访问：

```text
http://localhost:8501
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

`.env` 存放真实 Key，不要提交 Git。

## 功能测试模式

主要流程：

1. 上传 `.txt` / `.md` / `.docx` 需求，或手动填写需求模板。
2. 选择规则生成或 AI 生成。
3. 预览识别到的功能点，取消误识别项。
4. 生成并编辑测试用例。
5. 查看质量评分、覆盖提示矩阵和分类质量提示。
6. 保存 JSON 或导出 Excel。

导出 Excel 包含：

- `测试用例`
- `质量报告`

## 接口测试模式

主要流程：

1. 上传 `.txt` / `.md` 接口文档，或粘贴接口文档。
2. 确认并修正解析结果。
3. 生成接口测试用例。
4. 编辑用例并查看覆盖提示矩阵、质量提示。
5. 导出接口 Excel。

接口用例字段：

```text
用例编号、模块、接口名称、请求方法、接口路径、请求头、请求参数、请求体、
前置条件、操作步骤、预期状态码、断言点、数据库校验、变量提取、
优先级、用例类型、备注
```

接口规则生成覆盖：

- 正常请求
- 必填参数为空
- 参数类型错误
- 参数边界/非法值
- 未鉴权或 Token 缺失
- 权限不足
- 业务规则不满足
- 重复请求/幂等性
- 响应字段断言
- 数据库校验

导出 Excel 包含：

- `接口测试用例`
- `接口质量报告`

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
examples/api_smart_home_device_control.md
examples/api_housekeeping_appointment.txt
```

## 测试

```powershell
.\.venv\Scripts\python -m pytest -q
```

当前测试覆盖核心解析、生成、表格转换、质量检查、Excel 导出、持久化和提示矩阵逻辑。

## 目录结构

```text
app.py                 Streamlit 入口
src/api/               接口测试模式：解析、参数、生成、质量、导出、UI
src/*.py               功能测试模式和通用工具
prompts/functional.md  功能测试 AI Prompt
examples/              示例需求和接口文档
tests/                 pytest 测试
outputs/               本地生成结果，不提交 Git
```

## 下一步

- 功能测试与接口测试结果的本地历史管理进一步统一。
- 继续观察接口参数解析准确性，必要时支持更复杂的字段表格格式。
- 稳定后再考虑更细的分包重构。
