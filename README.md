# AI 辅助测试用例生成与导出工具

一个基于 Streamlit 的本地测试用例生成工具。用户填写需求模板后，可以选择规则生成或 AI 生成测试用例，并导出 Excel。

当前版本：`v0.2.0`

## 功能简介

- Streamlit 单页面入口
- 需求模板输入：项目、模块、角色、前置条件、业务流程、验收标准、异常规则
- 支持规则生成和 AI 生成
- 支持 DeepSeek 和 OpenAI
- 支持生成类型：
  - 功能测试
  - 接口测试
  - Web UI 测试
  - App 测试
- 自动拆分业务流程中的多个功能点
- 页面展示实际生成方式、服务商、模型、功能点数量和用例数量
- 测试用例字段包含：用例编号、模块、功能点、标题、前置条件、测试数据、步骤、预期结果、优先级、类型、备注
- 生成后可在页面表格中编辑用例，再导出编辑后的 Excel
- 按模块/功能点分组查看生成结果
- 支持单个功能点重新生成，避免整批重跑
- 自动检查用例质量：重复编号、缺字段、步骤过短、预期结果过泛、覆盖类型不足
- Excel 导出包含边框、筛选、冻结表头、优先级颜色和适配行高
- 生成结果自动保存为本地 JSON，可导入历史 JSON 继续编辑
- 可从本地历史 JSON 列表中选择历史记录继续编辑
- Prompt 文件化，当前功能测试 Prompt 位于 `prompts/functional.md`
- Excel 导出包含 `测试用例` 和 `质量报告` 两个 sheet
- 支持 Excel 导出
- AI 调用失败时自动回退到规则生成，并显示回退原因

## 运行步骤

1. 用 PyCharm 打开本目录。

2. 创建并选择虚拟环境。

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 启动页面：

```bash
streamlit run app.py
```

Windows 下也可以运行：

```bash
run_app.bat
```

5. 打开终端显示的地址，通常是：

```text
http://localhost:8501
```

`app.py` 底部保留了：

```python
if __name__ == "__main__":
    main()
```

因此在 PyCharm 中也可以右键运行文件；但 Streamlit 项目更推荐使用 `streamlit run app.py`。

## 环境变量

在项目根目录创建 `.env`，填写自己的 key：

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini

DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

说明：

- `.env` 存放真实 API Key，不要提交到 Git。
- 未配置 API Key 时，选择 AI 生成会自动回退到规则生成。
- 页面显示 `实际生成方式 = AI 生成（DeepSeek）` 或 `AI 生成（OpenAI）` 时，才表示本次真的调用了 AI。

## 测试命令

运行全部测试：

```bash
pytest
```

或使用当前虚拟环境：

```bash
.\.venv\Scripts\python -m pytest
```

当前测试覆盖：

- 需求拆分
- 规则生成
- AI JSON 数组提取和解析
- Excel 导出
- 页面编辑数据转换
- 用例质量检查
- 导出文件名生成
- 操作步骤格式化
- 本地 JSON 持久化
- Prompt 加载
- 质量报告 sheet

## 功能截图

截图占位：

```text
docs/screenshots/v0.2.0-home.png
docs/screenshots/v0.2.0-result.png
```

后续可以在页面稳定后补充实际截图。

## 使用建议

生成测试用例后，优先检查这些内容：

- 功能点是否拆分合理
- 用例编号是否重复
- 操作步骤是否可执行
- 预期结果是否明确
- 是否缺少异常、权限、边界或重复提交场景

页面表格可以直接编辑。点击导出时，系统会使用编辑后的表格内容生成 Excel。

如果只对某个功能点不满意，可以在“单功能点重新生成”区域选择对应模块/功能点并重新生成。系统会替换该功能点下的用例，保留其他功能点。

生成后会自动保存：

```text
outputs/latest_cases.json
outputs/cases_YYYYMMDD_HHMMSS.json
```

`outputs/` 是本地运行产物，不提交 Git。

如果导出的 Excel 没有看到 `质量报告` sheet，请先停止旧的 Streamlit 服务并重新启动：

```bash
streamlit run app.py
```

旧服务进程可能仍在使用旧版导出代码。

## 后续优化计划

- 支持自定义 Excel 列名和列顺序
- 支持上传需求文档并抽取文本
- 支持保存常用测试模板
- 增加更细的接口测试字段，例如请求方法、接口路径、请求体、响应断言
- 增加更稳定的 AI 输出校验和错误提示

暂不引入：

- RAG
- 数据库
- FastAPI
- 独立前端框架
