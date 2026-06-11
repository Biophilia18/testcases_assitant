# Project Context

## 项目定位

本项目是本地运行的 Streamlit 测试用例助手，目标是让用户在真实测试场景下稳定得到一套专业、可解释、可编辑、可导出的测试设计结果。

当前阶段重点不是自动执行接口，而是辅助完成测试设计。

## 当前限制

- 不引入 RAG、数据库、FastAPI、独立前端框架。
- 不做 Swagger/OpenAPI、Postman 解析。
- 不真实执行接口。
- 不生成 pytest 自动化脚本。
- 不提交 `.env` 或真实 API Key。

## 功能测试模式

入口仍在 Streamlit 主页面中。

主要能力：

- 需求文本/文件输入。
- 功能点识别和生成前预览。
- 规则生成与 AI 生成。
- 可编辑表格。
- 质量评分、覆盖提示、质量报告。
- JSON 保存/导入和 Excel 导出。

## 接口测试模式

入口位于 `src/api/ui.py`。

当前定位：单接口测试设计工作台。

主要能力：

- txt/md 接口文档粘贴或上传。
- 示例文档一键填充。
- 单接口字段解析与手动修正。
- 模块级多接口文档识别为接口清单，但不批量生成。
- 接口清单展示参数数、鉴权、业务规则、数据库校验、复杂度。
- 选择一个接口后进入单接口生成流程。
- 生成前做接口文档可信度检查：缺少请求方法或接口路径时禁用生成；缺少参数、鉴权、响应示例或业务规则时只提示，不凭空生成对应测试点。
- 参数解析支持普通文本和 Markdown 表格，并区分 path/query/body，避免路径参数进入 query。
- 生成前预览与高级设计选项。
- 参数风险、业务规则、计划项驱动生成。
- 用例标题、接口字段、断言、数据库校验、变量提取。
- Excel 导出和 `api_auto` YAML 草稿导出。

`api_auto` YAML 只是草稿，需要人工补充 token、环境变量、复杂断言、数据库 SQL 和测试数据。

## 关键文件

```text
app.py                         Streamlit 入口
src/api/ui.py                  接口测试页面
src/api/document_parser.py     单接口文档解析
src/api/document_candidates.py 多接口候选识别
src/api/examples.py            内置接口示例
src/api/param_parser.py        参数解析
src/api/reliability.py         接口文档可信度检查
src/api/design_plan.py         测试设计计划
src/api/rule_generator.py      接口规则生成
src/api/api_auto_exporter.py   api_auto YAML 草稿导出
src/api/exporter.py            接口 Excel 导出
tests/                         pytest 测试
examples/                      示例需求和接口文档
```

## 验证命令

```powershell
.\.venv\Scripts\python -m pytest -q
```

最近目标测试结果：全部通过。

## 下一步建议

优先继续小步稳定接口模式：

1. 优化接口清单选择体验。
2. 继续补充真实接口文档回归样本。
3. 增强 `api_auto` YAML 草稿就绪度检查。
4. 稳定后再做结构分包和文档重整。
