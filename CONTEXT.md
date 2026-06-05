# Testcase Assistant Project Context

## 项目定位

本项目是一个本地运行的 AI 辅助测试用例生成与编辑工具，当前目标不是做完整平台，而是先把“稳定的测试用例编辑器”打磨好。

工具入口保持为 Streamlit 单页面应用，不引入 RAG、数据库、FastAPI 或独立前端框架。

## 当前阶段首要目标

当前阶段目标：稳定、可用、可编辑、可导出的测试用例助手。

优先处理：

- 生成结果持久化为本地 JSON 文件
- 支持导入历史 JSON 继续编辑
- Prompt 版本管理
- 页面布局管理
- 生成质量报告
- Excel 第二个 sheet 写入质量报告

暂不处理：

- RAG
- GraphRAG
- 知识图谱
- 数据库
- 多用户/权限
- FastAPI 后端
- 独立前端框架
- 复杂文档 OCR

## 生成类型范围

当前先只完整打磨“功能测试”。

之前页面中出现过：

- 功能测试
- 接口测试
- Web UI 测试
- App 测试

但当前阶段不继续扩展接口/Web UI/App 的差异化能力。后续应在功能测试稳定后，再逐类适配。

## 已实现能力

- Streamlit 单页面入口
- 需求模板输入
- DeepSeek / OpenAI API Key 从 `.env` 自动读取
- 无 API Key 或 API 调用失败时回退到规则生成
- 测试用例规则生成
- AI JSON 数组解析
- AI steps 数组清理为多行编号步骤
- 测试用例可编辑表格
- 编辑后导出 Excel
- Excel 自动文件名
- Excel 样式优化
  - 表头样式
  - 冻结表头
  - 自动筛选
  - 边框
  - 优先级颜色
  - 步骤换行
  - 行高适配
- 按模块/功能点分组查看
- 单功能点重新生成
- 质量检查
  - 重复编号
  - 缺字段
  - 步骤过短
  - 预期结果过泛
  - 缺少异常/边界/权限覆盖
- pytest 测试覆盖主要逻辑
- 生成结果本地持久化
- 导入历史 JSON 继续编辑
- Prompt 文件化
- 页面 tabs 布局
- Excel 第二个 sheet 输出质量报告
- 本地历史 JSON 列表选择加载
- 生成/导入/重生成后刷新编辑表格状态，避免旧表格残留
- 支持 `.txt` / `.md` / `.docx` 需求文本上传并自动填充模板字段
- 需求解析支持组合标题，例如 `项目/系统名称`、`业务流程/需求描述`、`补充规则/异常场景`
- `.docx` 当前只抽取正文段落文本，不处理图片、表格、批注或 OCR
- 支持生成前预览与确认，确认前不会调用 AI
- 生成前预览和规则生成数量以“业务流程/需求描述”为功能点抽取来源
- 完整需求仍传入 AI prompt，验收标准和异常规则作为覆盖约束，不逐条当作独立功能点
- 功能点名称不再做固定长度截断，避免预览和规则生成标题丢失关键文字

## 当前核心文件

- `app.py`：Streamlit 页面入口
- `src/models.py`：测试用例数据模型、Excel 列顺序
- `src/ai_client.py`：AI 调用、Prompt 构造、JSON 解析
- `src/rule_based_generator.py`：规则生成
- `src/table_adapter.py`：页面表格和 `TestCase` 互转
- `src/exporter.py`：Excel 导出
- `src/text_utils.py`：步骤格式化
- `src/filename_utils.py`：导出文件名生成
- `src/quality_checker.py`：用例质量检查
- `src/persistence.py`：生成结果 JSON 保存和读取
- `src/prompt_manager.py`：Prompt 文件读取
- `prompts/functional.md`：功能测试 Prompt
- `outputs/`：本地生成结果，不提交 Git
- `tests/`：pytest 测试
- `.env`：真实 API Key，本地使用，不提交 Git

## 当前 Excel 字段顺序

字段顺序以 `src/models.py` 的 `EXCEL_COLUMNS` 为准。

当前顺序：

1. 用例编号
2. 模块
3. 用例标题
4. 优先级
5. 前置条件
6. 测试数据
7. 操作步骤
8. 预期结果
9. 用例类型
10. 功能点
11. 备注

代码里已经有列名到字段名的映射。后续如果只调整展示和导出顺序，优先修改 `EXCEL_COLUMNS`。

## 当前 Git 工作流

- `main`：稳定版本
- `dev`：开发版本

当前功能开发应在 `dev` 分支完成。

常规节奏：

1. 一个完整功能点完成
2. 测试通过
3. 本地 commit
4. push 到 `origin/dev`
5. 试用稳定后再考虑合并到 `main`

## 下一步计划

本轮计划状态：

已完成：

1. 增加本地 JSON 持久化
   - 生成后保存到 `outputs/latest_cases.json`
   - 同时按时间保存历史快照
2. 增加导入历史 JSON 继续编辑
   - 页面支持上传 JSON
   - 支持加载最近一次生成结果
3. Prompt 版本管理
   - 把功能测试 Prompt 放入 `prompts/functional.md`
   - AI 调用时从文件读取
4. 页面布局管理
   - 使用 Streamlit tabs 分为：
     - 需求输入
     - 生成结果
     - 质量检查
     - 导出
5. Excel 增加第二个 sheet
   - Sheet1：测试用例
   - Sheet2：质量报告

下一步候选：

- 继续观察规则/AI 生成规模：已避免把项目名、验收标准和异常规则直接拆成独立功能点；后续可再优化业务流程内部拆分粒度
- 进一步优化表格编辑体验
- 增加 Word 表格文本抽取
- 在功能测试稳定后，再开始接口测试适配
- 增加页面版本号/运行状态提示，避免旧 Streamlit 服务造成误判

## 重要约束

- 不要提交真实 `.env`
- 不要泄露 API Key
- 保持代码简单，适合初学者阅读
- 不要引入数据库或复杂服务
- 不要把功能做成多页面/多框架系统
- 优先让当前工具稳定可用，再进入 RAG/知识增强方向
