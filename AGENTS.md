# AGENTS.md

## 构建与运行 (Build & Run)

- **安装依赖**：
  请执行以下命令安装所需的 Python 库：
  ```bash
  pip install alibabacloud_dingtalk alibabacloud_tea_openapi alibabacloud_tea_util openpyxl python-docx
  ```

- **运行脚本**：
  使用以下命令运行指定脚本：
  ```bash
  python <script_name>.py
  ```

- **测试框架**：
  当前项目暂未配置测试框架。

## 代码规范 (Code Style)

- **文件编码**：
  文件头部必须声明编码格式：`# -*- coding: utf-8 -*-`。

- **类型提示 (Type Hints)**：
  使用 `typing` 模块进行类型标注（如 `Optional`, `Dict`, `List`, `Any`）。

- **命名规范**：
  - **函数与变量**：使用蛇形命名法 (snake_case)。
  - **常量**：使用全大写蛇形命名法 (UPPER_SNAKE_CASE)。

- **文档字符串 (Docstrings)**：
  使用中文编写文档字符串，并明确包含参数 (Args) 和返回值 (Returns) 说明部分。

- **导入顺序 (Imports)**：
  优先导入 Python 标准库，其次导入第三方依赖包。

- **异常处理**：
  使用 `try/except` 结构捕获具体的异常类型，并输出中文错误信息。

- **文件路径**：
  - 使用 `os.path` 模块以确保跨平台兼容性。
  - 使用 `os.path.normpath` 对路径进行标准化处理。

- **配置管理**：
  - 配置常量应定义在模块顶部。
  - 数据存储建议使用 JSON 格式。

- **注释**：
  代码中允许并建议使用中文注释。