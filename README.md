# DingDingZhiKuTong - 钉钉知识库同步与内容提取工具集

本工具套件提供了两大核心功能：一是将钉钉知识库与本地文件夹进行精确、增量的单向同步；二是从Excel文件中提取其链接的各类文档的详细内容。

## 🚀 核心功能

*   **知识库同步 (DingTalk Sync)**
    *   **智能比较**：通过API获取知识库的完整目录结构，与本地文件夹进行比较，精确识别新增和修改过的文件。
    *   **增量更新**：只生成需要下载的新增或更新文件的URL列表，避免全量下载，提高效率。
    *   **精确同步**：确保最终的本地文件夹内容与钉钉知识库的线上状态完全一致，可自动删除本地多余的文件和目录。
    *   **格式自动转换**：自动将钉钉的专有后缀（如 `.adoc`, `.axls`）映射为标准的Office后缀（`.docx`, `.xlsx`），确保本地文件兼容性。

*   **Excel链接内容提取 (Excel Content Extraction)**
    *   **多层次工具选择**：提供从基础到专家级的三个不同工具，满足不同需求。
    *   **广泛的格式支持**：高级版工具可支持超过30种文档格式，包括 `PDF`, `DOCX`, `PPTX`, `HTML`, `Markdown` 等。
    *   **LLM多模态识别 (专家版)**：利用多模态大模型（如 `GPT-4V`, `通义千问-VL`）高精度识别文档中的图片、图表和表格内容，远超传统OCR。
    *   **高度可配置**：提供灵活的配置选项，可以控制输出格式、并发处理、内容长度等。
    *   **路径自动解析**：智能处理Excel中链接的相对和绝对路径。

## 📋 目录结构

```
DingDingZhiKuTong/
├── getToken.py                           # 钉钉API认证模块
├── get_KB_FILE_URL.py                    # 【同步】知识库文件管理和比较核心模块
├── compare_move_file.py                  # 【同步】文件精确同步执行模块
|
├── write_file_excel.py                   # 【提取】基础版-Excel链接内容提取工具
├── excel_link_content_fetcher.py         # 【提取】高级版-支持30+种格式
├── excel_link_content_fetcher_LLM.py     # 【提取】专家版-LLM多模态增强
|
├── excel_link_content_fetcher_README.md     # (将被废弃)
├── excel_link_content_fetcher_LLM_README.md # (将被废弃)
└── README.md                              # (本文档)
```

## 🛠️ 环境准备

确保您的环境中已经安装了 Python 3.7+。然后，根据您需要使用的功能安装依赖。

### 1. 基础依赖 (所有功能都需要)
```bash
pip install openpyxl
```

### 2. 知识库同步功能依赖
```bash
pip install alibabacloud_dingtalk alibabacloud_tea_openapi alibabacloud_tea_util
```

### 3. Excel内容提取功能依赖

*   **基础版 (`write_file_excel.py`)**
    ```bash
    pip install python-docx
    ```

*   **高级版 (`excel_link_content_fetcher.py`)**
    ```bash
    # 安装unstructured核心及所有文档格式支持
    pip install "unstructured[all-docs]"
    
    # 在Linux (Ubuntu/Debian)上，可能还需要系统依赖
    # sudo apt-get install libmagic-dev poppler-utils tesseract-ocr libreoffice
    ```

*   **专家版 (`excel_link_content_fetcher_LLM.py`)**
    ```bash
    # 首先安装高级版的所有依赖
    pip install "unstructured[all-docs]"
    
    # 然后安装LLM和图片提取相关依赖
    pip install openai PyMuPDF beautifulsoup4
    ```

## 📚 工作流程一：知识库与NAS同步

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

## 📖 工作流程二：Excel链接内容提取

此功能用于读取Excel文件中指向本地文件的超链接，提取这些文档的内容，并写回Excel的新列中。提供了三个级别的工具供选择。

### ⚠️ 重要提醒
所有这些脚本都会**直接修改**您传入的Excel文件。**操作前请务必备份原始文件！**

### 1. 基础版: `write_file_excel.py`
- **特点**: 轻量，依赖少，代码简单。
- **支持格式**: `.txt`, `.docx`, `.xlsx`。
- **使用方法**: 直接修改脚本底部的 `excel_file_path` 变量，然后运行。
```python
# 在 write_file_excel.py 中
excel_file_path = "C:\\path\\to\\your\\file.xlsx"
process_excel_in_place(excel_file_path)
```
```bash
python write_file_excel.py
```

### 2. 高级版: `excel_link_content_fetcher.py`
- **特点**: 功能强大，基于 `unstructured` 库，支持30多种文档格式，支持并发处理。
- **使用方法**: 建议通过代码调用。
```python
# 示例代码
from excel_link_content_fetcher import process_excel_links, DocumentProcessingConfig

config = DocumentProcessingConfig(
    output_format="markdown",
    partition_strategy="hi_res",  # "hi_res"策略会执行OCR
    enable_parallel_processing=True,
    max_workers=4
)
result = process_excel_links("C:\\path\\to\\your\\file.xlsx", config=config)
print(result)
```

### 3. 专家版: `excel_link_content_fetcher_LLM.py`
- **特点**: 具备高级版所有功能，并增加了LLM多模态能力，可高精度识别图片内容。
- **凭证准备**: 需要配置LLM的API Key (如OpenAI, 或通义千问)。
- **使用方法**：
```python
# 示例代码 (使用通义千问)
from excel_link_content_fetcher_LLM import *

# 1. 配置多模态模型
multimodal_config = MultimodalConfig(
    vision_model_provider="qwen",
    vision_model_name="qwen-vl-plus",
    api_key=os.environ.get("QWEN_V"), # 推荐使用环境变量
    api_base="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 2. 创建总配置并启用多模态
config = DocumentProcessingConfig(
    enable_multimodal=True,
    multimodal_config=multimodal_config
)

# 3. 执行处理
processor = EnhancedExcelProcessorLLM(config)
result = processor.process_excel_file("C:\\path\\to\\your\\file.xlsx")
print(result)
```

## 🐛 常见问题

### 同步相关
1.  **API调用失败**: 检查 `ACCESS_TOKEN` 是否过期或 `AppKey` 等凭证是否正确。
2.  **知识库找不到**: 检查 `WORKSPACE_NAME` 是否与钉钉后台显示的名称完全一致。
3.  **文件同步不符合预期**: 务必先运行 `compare_move_file.py` 的演练模式 (`dry_run=True`)，检查其输出的计划操作是否正确。

### 提取相关
1.  **Excel处理失败/无法保存**: 确保Excel文件未被其他程序打开，并检查文件写入权限。
2.  **内容提取不准确/格式混乱**：
    - 对于`高级版`和`专家版`，尝试切换 `partition_strategy` (`"hi_res"` 或 `"fast"`)。
    - 对于`专家版`的图片识别，调整 `vision_prompt` 以获得更精确的结果。
3.  **依赖安装问题**: `unstructured` 库可能需要特定的系统依赖，请参考其官方文档进行安装。

---
*最后更新: 2025-11-21*
*文档版本: 2.0*
