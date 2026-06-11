# AI 测试用例助手

一个本地运行的 Streamlit 工具，用于把需求说明或接口文档转换为可编辑、可检查、可导出的测试用例。

当前重点是测试设计辅助，不是自动执行测试。

## 功能

- 功能测试：需求解析、功能点预览、规则/AI 生成、用例编辑、质量检查、Excel 导出。
- 接口测试：接口文档解析、参数识别、测试设计计划、规则生成、用例编辑、质量检查、Excel 导出。
- 导出前复核：提示明显错误、覆盖缺口和需要人工确认的内容。
- `api_auto` YAML：仅提供草稿预览，不保证直接可执行。

## 不做的事

- 不引入 RAG、数据库、FastAPI、独立前端框架。
- 不做 Swagger/OpenAPI、Postman 解析。
- 不真实执行接口。
- 不生成 pytest 自动化脚本。

## 运行

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Windows 可直接运行：

```powershell
run_app.bat
```

## 环境变量

如需 AI 生成，在根目录创建 `.env`：

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

## 注意

生成结果只能作为测试设计草稿。业务规则、测试数据、断言、数据库校验和 YAML 草稿仍需要人工复核。
