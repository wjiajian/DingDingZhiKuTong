# DingDingZhiKuTong

本工具用于将钉钉知识库与本地NAS（或任何文件夹）进行精确、增量的单向同步。提供了完整的钉钉知识库API集成、文件比较、同步和Excel文档处理功能。

## 🚀 核心功能

*   **智能比较**：通过API获取知识库的完整目录结构，并与本地文件夹进行比较，识别出新增、修改过的文件。
*   **增量下载**：只生成需要下载的新增或已更新文件的URL列表，最大化效率。
*   **精确同步**：确保最终的本地文件夹内容与钉钉知识库的线上状态完全一致，自动删除本地多余的文件和目录。
*   **自动转换后缀**：自动将钉钉的专有后缀（如 `.adoc`, `.axls`）映射为标准的Office后缀（`.docx`, `.xlsx`），确保本地文件可用性。
*   **Excel文档处理**：读取Excel中链接的文档内容，自动提取并格式化为Markdown格式。

## 📋 目录结构

```
DingDingZhiKuTong/
├── getToken.py              # 钉钉API认证模块
├── get_KB_FILE_URL.py       # 知识库文件管理和比较核心模块
├── compare_move_file.py     # 文件同步执行模块
├── write_file_excel.py      # Excel文档内容提取工具
├── AGENTS.md               # 项目规范文档
└── README.md               # 项目说明文档
```

## 🛠️ 环境准备与凭证

### 1. 环境准备

确保您的环境中已经安装了 Python 3.7+。然后，安装所需的依赖库：

```bash
pip install alibabacloud_dingtalk alibabacloud_tea_openapi alibabacloud_tea_util openpyxl python-docx
```

**依赖说明**：
- `alibabacloud_dingtalk`：钉钉开放平台SDK
- `alibabacloud_tea_openapi`：阿里云通用OpenAPI SDK  
- `alibabacloud_tea_util`：阿里云通用工具库
- `openpyxl`：Excel文件读写处理
- `python-docx`：Word文档内容提取

### 2. 获取访问凭证

首先，您需要获取访问钉钉API所需的凭证。

#### 获取 `app_key` 和 `app_secret`

1.  登录[钉钉开放平台](https://open.dingtalk.com/)。
2.  创建或选择一个应用，进入应用详情页。
3.  在"应用凭证"区域，您可以找到 `AppKey` 和 `AppSecret`。

#### 获取 `access_token`

1.  打开 `getToken.py` 文件。
2.  将您获取到的 `app_key` 和 `app_secret` 填入到 `get_access_token_request` 中。
3.  运行 `getToken.py` 脚本：

    ```bash
    python getToken.py
    ```
4.  在控制台输出中，您将看到包含 `accessToken` 的信息。请复制 `accessToken` 的值。

#### 获取 `operator_id`

`operator_id` 是操作者的 `unionId`。您可以通过调用[根据手机号获取用户信息](https://open.dingtalk.com/document/org-dev-guide/query-user-details-by-phone-number)接口，或者在钉钉后台的用户管理中获取。

## 📚 脚本功能详解

### 🔑 getToken.py
- **用途**：获取钉钉API访问凭证
- **输入**：AppKey和AppSecret（钉钉开放平台获取）
- **输出**：access_token（用于后续API调用）
- **使用场景**：每次需要刷新访问令牌时运行

### 🌐 get_KB_FILE_URL.py  
- **用途**：知识库文件管理和增量比较
- **核心特性**：
  - 自动扫描钉钉知识库完整文件树
  - 智能识别文件新增和更新状态
  - 支持钉钉专有格式转换（.adoc→.docx）
  - 生成精确的下载清单
  - 支持分页处理大量文件
- **输出**：
  - `kb_tree.json`：知识库完整蓝图
  - `urls_to_download.txt`：本次需下载文件URL
  - `workspaces_list.json`：所有知识库列表

### 📁 compare_move_file.py
- **用途**：执行精确的文件同步操作
- **工作流程**：
  1. **清理阶段**：删除本地多余文件和空目录
  2. **移动阶段**：将新文件移动到正确位置
- **安全机制**：支持演练模式，预览操作而不执行
- **路径处理**：自动处理跨平台路径兼容性

### 📊 write_file_excel.py
- **用途**：提取Excel链接文档内容
- **支持格式**：TXT、DOCX、XLSX
- **智能特性**：
  - 自动识别链接列并插入内容列
  - 相对路径自动解析
  - 内容自动格式化为Markdown
  - 多工作表内容提取

**⚠️ 重要提醒**：`write_file_excel.py`会直接修改原始Excel文件，建议使用前做好备份！

## ⚙️ 配置参数详解

### get_KB_FILE_URL.py 配置

| 参数 | 说明 | 示例 |
|------|------|------|
| ACCESS_TOKEN | 钉钉API访问令牌 | 从getToken.py获取 |
| OPERATOR_ID | 操作者unionId | 钉钉用户唯一标识 |
| WORKSPACE_NAME | 目标知识库名称 | "我的知识库" |
| NAS_ROOT_PATH | 本地NAS根路径 | "NAS/Docs" |
| KB_TREE_OUTPUT_FILE | 知识库蓝图输出 | "./kb_tree.json" |
| OUTPUT_FILE | URL列表输出 | "./download_urls.txt" |

### 文件路径支持
- **绝对路径**：`C:/Users/Documents/file.txt`
- **相对路径**：`./Documents/file.txt`（相对于脚本执行目录）
- **跨平台兼容**：自动处理Windows/Linux路径分隔符

## 🔄 知识库与NAS同步流程

这是一个三步走的工作流。

### 步骤 1: 生成下载列表和知识库蓝图

运行 `get_KB_FILE_URL.py` 脚本。

**配置示例**：
```python
# 在脚本第30-37行修改配置
ACCESS_TOKEN = "your_access_token_here"              # 从getToken.py获取
OPERATOR_ID = "your_unionid_here"                    # 您的unionId
WORKSPACE_NAME = "您的知识库名称"                     # 知识库完整名称
NAS_ROOT_PATH = "./local_nas_folder"                 # 本地NAS路径
KB_TREE_OUTPUT_FILE = "./kb_tree.json"               # 知识库蓝图输出
OUTPUT_FILE = "./urls_to_download.txt"              # URL列表输出
```

**执行**：
```bash
python get_KB_FILE_URL.py
```

**结果**：
- 生成 `kb_tree.json` (完整的知识库蓝图)
- 生成 `urls_to_download.txt` (本次需下载的URL列表)

### 步骤 2: 下载并整理文件 (手动)

1. 使用您自己的下载工具处理 `urls_to_download.txt` 文件，将所有文件下载下来。
2. 将下载的文件整理到一个临时的"源文件夹" (例如: `download_new`) 中，并确保其内部的目录结构与知识库中的结构完全一致。

**目录结构示例**：
```
download_new/
├── folder1/
│   ├── file1.txt
│   └── new_file.txt
└── file_at_root.txt
```

### 步骤 3: 清理并同步到NAS

运行 `compare_move_file.py` 脚本。

**配置示例**：
```python
# 在脚本第107-115行修改配置
KB_TREE_JSON = './kb_tree.json'          # 知识库蓝图
SOURCE_DIR = 'download_new'               # 源文件夹
DEST_DIR = 'nas_final'                    # 目标NAS文件夹
```

**执行**：
```bash
# 演练模式（推荐先运行）
python compare_move_file.py

# 正式执行
# （确认演练结果无误后执行）
```

**过程**：
1. **清理阶段**: 脚本会读取 `kb_tree.json`，然后检查"NAS目标文件夹"。如果发现NAS中的任何文件或空目录在 `kb_tree.json` 中不存在，就会将其删除。
2. **移动阶段**: 脚本会遍历"源文件夹"，将里面的所有新文件和更新文件移动到"NAS目标文件夹"的正确位置。

**结果**：
- 一个与钉钉知识库文件结构和内容完全同步的NAS文件夹
- "源文件夹"内的文件被移动后，该文件夹会变空

## 🛡️ 安全与最佳实践

### 演练模式
在执行 `compare_move_file.py` 前，建议先使用演练模式预览操作：
```python
# 在脚本第145行修改
sync_nas_with_kb_tree(KB_TREE_JSON, SOURCE_DIR, DEST_DIR, dry_run=True)  # 演练模式
```

### 文件备份
使用 `write_file_excel.py` 前，请务必备份原始Excel文件：
```bash
cp original_file.xlsx original_file.xlsx.backup
```

### 权限检查
确保以下权限：
- 钉钉应用对目标知识库有读取权限
- 本地文件系统对目标文件夹有读写权限
- 网络连接正常，能访问钉钉API

## 🐛 常见问题解决

### 1. API调用失败
**症状**：`获取 Access Token 失败: code=xxx, message=xxx`
**解决**：
- 检查app_key和app_secret是否正确
- 确认应用权限设置
- 验证网络连接

### 2. 知识库找不到  
**症状**：`无法找到名为 'xxx' 的知识库`
**解决**：
- 检查WORKSPACE_NAME是否与钉钉后台显示的名称完全一致
- 确认operator_id对应的用户有访问权限

### 3. 文件下载权限问题
**症状**：某些文件URL无法下载
**解决**：确认操作者账号对知识库文件有访问权限

### 4. Excel处理失败
**症状**：`无法保存文件 xxx.xlsx`
**解决**：
- 确保Excel文件未被其他程序打开
- 检查文件写入权限
- 确认openpyxl版本兼容性

### 5. 路径解析错误
**症状**：`链接的文件不存在`
**解决**：
- 检查Excel中的链接路径
- 确保文件实际存在且可访问
- 验证相对路径解析

### 6. 编码问题
**症状**：中文文件名或内容显示乱码
**解决**：
- 确保所有文件使用UTF-8编码
- 检查系统默认编码设置

---

*最后更新: 2025-11-20*  
*项目版本: v1.0*