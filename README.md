# AI 辅助测试用例生成与导出工具

这是一个面向 PyCharm 调试的最小可运行版本。

当前能力：

- 粘贴需求文本
- 生成结构化测试用例
- 自动拆分业务流程中的多个功能点
- 显示实际生成方式：AI 生成或规则生成
- 支持 OpenAI 和 DeepSeek 两种 AI 服务商
- AI 调用失败时显示回退原因
- 页面预览测试用例
- 导出 Excel
- 无 API Key 时使用本地规则生成
- 配置 `OPENAI_API_KEY` 后可切换为 AI 生成

## 在 PyCharm 中运行

1. 用 PyCharm 打开本目录。
2. 创建 Python 虚拟环境。
3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 运行：

```bash
streamlit run app.py
```

Windows 下也可以直接运行：

```bash
run_app.bat
```

5. 浏览器打开终端里显示的本地地址，通常是：

```text
http://localhost:8501
```

## Streamlit 是什么

`Streamlit` 是一个 Python 本地网页界面框架。它的作用是：不用单独写 HTML、CSS、JavaScript，也能用 Python 快速做出输入框、按钮、表格、下载按钮等网页控件。

本项目里：

- `st.text_area()` 负责显示需求输入框
- `st.button()` 负责显示“生成测试用例”按钮
- `st.dataframe()` 负责显示测试用例预览表格
- `st.download_button()` 负责导出 Excel 文件
- `st.sidebar` 负责左侧配置区

## 如何判断是否真的调用了 AI

页面生成后会显示 5 个指标：

- `实际生成方式`：显示 `AI 生成` 才表示本次真的使用了 OpenAI API
- `服务商`：显示本次选择的是 OpenAI、DeepSeek 还是规则生成
- `识别功能点`：本次从需求里拆出的功能点数量
- `测试用例数`：最终生成的用例数量
- `模型`：AI 模式下使用的模型名

如果选择了 `AI 生成`，但实际显示为 `规则生成`，说明 AI 调用没有成功。页面会展示回退原因。

## 可选：启用 OpenAI

方式一：在项目根目录创建 `.env` 文件：

```text
OPENAI_API_KEY=你的 key
OPENAI_MODEL=gpt-4.1-mini

DEEPSEEK_API_KEY=你的 key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

方式二：在系统环境变量或 PyCharm Run Configuration 里设置：

```text
OPENAI_API_KEY=你的 key
OPENAI_MODEL=gpt-4.1-mini

DEEPSEEK_API_KEY=你的 key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

如果不设置，工具会自动使用本地规则生成模式。

注意：`.env` 已在 `.gitignore` 中排除，不应提交到 Git。
