# DingDingZhiKuTong - 钉钉知识库同步工具集

> 由于在搭建企业 AI 助手期间需要同步各部门的知识库文件，故开发了此项目，此项目主要为 RPA 流程做相关基础工作，文件的下载部分通过 RPA 部分实现，故未在此项目提及。

本工具专注于钉钉知识库与本地文件夹 (NAS) 的精确、增量单向同步，提供完整的知识库备份和同步解决方案。

## 🚀 核心功能

*   **知识库同步 (DingTalk Sync)**
    *   **智能比较**：通过API获取知识库的完整目录结构，与本地文件夹进行比较，精确识别新增和修改过的文件。
    *   **增量更新**：只生成需要下载的新增或更新文件的URL列表，避免全量下载，提高效率。
    *   **精确同步**：确保最终的本地文件夹内容与钉钉知识库的线上状态完全一致，可自动删除本地多余的文件和目录。
    *   **格式自动转换**：自动将钉钉的专有后缀（如 `.adoc`, `.axls`）映射为标准的Office后缀（`.docx`, `.xlsx`），确保本地文件兼容性。

## 📋 目录结构

```
DingDingZhiKuTong/
├── getToken.py                           # 钉钉API认证模块
├── get_KB_FILE_URL.py                    # 知识库文件管理和比较核心模块
├── compare_move_file.py                  # 文件精确同步执行模块
└── README.md                              # (本文档)
```

## 🛠️ 环境准备

确保您的环境中已经安装了 Python 3.7+。

### 钉钉知识库同步功能依赖
```bash
pip install alibabacloud_dingtalk alibabacloud_tea_openapi alibabacloud_tea_util
```

## 📚 工作流程：知识库与NAS同步

这是一个三步走的工作流，用于将钉钉知识库完整地同步到本地。

### 凭证准备

在开始之前, 您需要从**[钉钉开放平台](https://open.dingtalk.com/)**获取以下凭证:
- `AppKey` 和 `AppSecret`: 在应用详情的"应用凭证"中找到。
- `Access Token`: 运行 `getToken.py` 获取。
- `Operator ID`: 操作者的 `unionId`，可从后台获取。

### 步骤 1: 生成下载列表和知识库蓝图

运行 `get_KB_FILE_URL.py` 脚本。此脚本会连接钉钉，比较本地与远程的差异，并生成两个关键文件。

**配置**:
在 `get_KB_FILE_URL.py` 脚本中填入您的配置信息。
```python
ACCESS_TOKEN = "your_access_token_here"
OPERATOR_ID = "your_unionid_here"
WORKSPACE_NAME = "您的知识库完整名称"
NAS_ROOT_PATH = "./nas_final"  # 您本地的最终目标文件夹
KB_TREE_OUTPUT_FILE = "kb_tree.json"
OUTPUT_FILE = "urls_to_download.txt"
```

**执行**：
```bash
python get_KB_FILE_URL.py
```

**结果**：
- `kb_tree.json`: 知识库的完整文件结构蓝图，是后续精确同步的依据。
- `urls_to_download.txt`: 本次需要下载的所有文件的URL列表。如果为空，则说明本地文件已是最新。

### 步骤 2: 下载文件 (手动)

**这是唯一需要手动介入的步骤**。

1.  使用您偏好的任何下载工具（如 `wget`, `aria2` 或其他脚本）处理 `urls_to_download.txt` 中的URL，将所有文件下载下来。
2.  将下载的文件整理到一个临时的"源文件夹"中 (例如: `download_new`)，并**确保其内部的目录结构与知识库中的结构完全一致**。

**目录结构示例**：
```
download_new/
├── 文件夹A/
│   ├── 文件1.docx
│   └── 新文件.xlsx
└── 根目录文件.pptx
```

### 步骤 3: 清理并同步到最终目录

运行 `compare_move_file.py` 脚本。此脚本会读取 `kb_tree.json` 作为“真实来源”，确保目标文件夹与知识库完全一致。

**配置**：
在 `compare_move_file.py` 脚本中配置路径。
```python
KB_TREE_JSON = 'kb_tree.json'      # 步骤1生成的文件
SOURCE_DIR = 'download_new'          # 步骤2整理好的源文件夹
DEST_DIR = 'nas_final'               # 最终的NAS目标文件夹
```

**执行**：
```bash
# 1. 演练模式 (强烈推荐首先运行，检查操作是否符合预期)
# 将 dry_run 设置为 True
sync_nas_with_kb_tree(..., dry_run=True) 
# > python compare_move_file.py

# 2. 正式执行 (确认演练结果无误后)
# 将 dry_run 设置为 False
sync_nas_with_kb_tree(..., dry_run=False) 
# > python compare_move_file.py
```

**过程**：
1.  **清理阶段**: 脚本会检查 `DEST_DIR`，如果发现任何在 `kb_tree.json` 中不存在的文件或空目录，都会将其删除。
2.  **移动阶段**: 脚本会遍历 `SOURCE_DIR`，将所有新文件移动到 `DEST_DIR` 的正确位置。

**最终结果**：
- `nas_final` 文件夹的内容与钉钉知识库完全同步。
- `download_new` 文件夹在移动后会变空。

---

## 🔗 相关项目：Excel链接内容提取
> 由于钉钉 AI 文档存在文件嵌套文件的问题，故开发了此项目用于提取解析文档附件

如果您需要处理Excel文件中链接的文档内容提取，我们推荐使用 **[LinkContentAI](https://github.com/wjiajian/LinkContentAI)** 项目。

### LinkContentAI 简介

**LinkContentAI** 是一个智能的Excel链接附件文档提取解析工具，专门设计用于自动化处理Excel中的链接文档。

### 核心特性

*   **多格式支持**：支持PDF、DOCX、TXT、XLSX等多种文档格式
*   **智能图片分析**：集成qwen-vl多模态大模型，自动解析文档中的图片内容
*   **优雅输出**：将提取的内容转换为Markdown格式，便于阅读和使用
*   **智能定位**：精确的图片位置检测和占位符替换
*   **实时反馈**：提供处理进度显示和临时文件自动管理
*   **灵活使用**：支持本地和API调用两种使用方式

### 适用场景

*   自动化处理包含链接附件的Excel文件
*   为AI助手构建知识库
*   批量文档内容提取和整理
*   智能文档内容分析与归档

LinkContentAI完美补充了本项目在文档处理方面的能力，特别适合需要处理大量包含图片的文档附件，并需要智能理解图片内容的应用场景。

## 🐛 常见问题

### 同步相关
1.  **API调用失败**: 检查 `ACCESS_TOKEN` 是否过期或 `AppKey` 等凭证是否正确。
2.  **知识库找不到**: 检查 `WORKSPACE_NAME` 是否与钉钉后台显示的名称完全一致。
3.  **文件同步不符合预期**: 务必先运行 `compare_move_file.py` 的演练模式 (`dry_run=True`)，检查其输出的计划操作是否正确。