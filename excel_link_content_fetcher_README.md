# Excel链接内容提取器使用说明

## 概述

`excel_link_content_fetcher.py` 是基于技术文档重构的新版Excel链接内容提取器，相比原版具备以下优势：

### 🚀 新增功能
- **支持30+种文档格式**：PDF、DOCX、PPT、HTML、RTF等
- **统一处理接口**：基于Unstructured的文档解析
- **备份安全机制**：自动备份，支持文件恢复
- **并行处理**：支持批量文件并行处理
- **详细日志**：完整的处理日志和错误追踪
- **配置灵活**：丰富的配置选项

### 📊 对比原版

| 功能 | 原版 | 新版 |
|------|------|------|
| 支持格式 | 3种 (TXT, DOCX, XLSX) | 30+种 |
| 错误处理 | 基础 | 统一，完整日志 |
| 备份机制 | 无 | 自动备份+恢复 |
| 并行处理 | 无 | 支持批量并行 |
| 配置灵活性 | 硬编码 | 丰富的配置类 |
| 代码结构 | 单一文件 | 模块化设计 |

## 🛠️ 安装依赖

### 基础依赖
```bash
pip install openpyxl
```

### 完整依赖（推荐）
```bash
pip install unstructured[all-docs]
```

### 系统依赖（Ubuntu/Debian）
```bash
sudo apt-get update
sudo apt-get install -y libmagic-dev poppler-utils tesseract-ocr libreoffice pandoc
```

## 📖 使用方法

### 1. 基本使用

```python
from excel_link_content_fetcher import process_excel_links, DocumentProcessingConfig

# 创建配置
config = DocumentProcessingConfig(
    output_format="markdown",
    backup_enabled=True,
    max_content_length=10000
)

# 处理Excel文件
result = process_excel_links("your_file.xlsx", config=config)

print(f"成功处理: {result['successful']} 个链接")
print(f"处理失败: {result['failed']} 个链接")
```

### 2. 高级使用

```python
from excel_link_content_fetcher import EnhancedExcelProcessor, DocumentProcessingConfig

# 创建处理器
config = DocumentProcessingConfig(
    output_format="markdown",           # 输出格式: markdown/plain_text/json
    partition_strategy="hi_res",       # 文档解析策略: hi_res/fast/ocr_only
    backup_enabled=True,               # 启用备份
    enable_parallel_processing=True,   # 启用并行处理
    max_workers=4,                     # 最大工作线程
    max_content_length=10000,          # 最大内容长度
    languages=["zh", "en"],           # 识别语言
    continue_on_error=True             # 遇到错误继续处理
)

processor = EnhancedExcelProcessor(config)

# 处理单个文件
result = processor.process_excel_file("your_file.xlsx")

# 批量处理
file_list = ["file1.xlsx", "file2.xlsx", "file3.xlsx"]
results = processor.process_multiple_files(file_list)
```

## ⚙️ 配置选项

### DocumentProcessingConfig 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `output_format` | str | "markdown" | 输出格式: markdown/plain_text/json |
| `partition_strategy` | str | "hi_res" | 解析策略: hi_res/fast/ocr_only |
| `max_content_length` | int | 10000 | 最大内容长度限制 |
| `backup_enabled` | bool | True | 是否启用备份 |
| `backup_location` | str | "./backup/" | 备份文件目录 |
| `enable_parallel_processing` | bool | True | 是否启用并行处理 |
| `max_workers` | int | 4 | 并行处理最大线程数 |
| `languages` | List[str] | ["zh", "en"] | 文档识别语言 |
| `continue_on_error` | bool | True | 遇到错误是否继续 |
| `max_retries` | int | 3 | 最大重试次数 |
| `include_metadata` | bool | True | 是否包含元信息 |

### 支持的文档格式

当安装unstructured时支持：
- **文档**: PDF, DOCX, DOC, TXT, MD, RTF, ODT
- **网页**: HTML, HTM, XML
- **数据**: JSON, CSV, LOG
- **演示**: PPTX, PPT
- **表格**: XLSX, XLS
- **电子书**: EPUB, MOBI
- **邮件**: MSG

当未安装unstructured时（回退方案）：
- TXT, MD, CSV, JSON

## 🔧 处理流程

### 1. 文件备份阶段
- 检查是否启用备份
- 创建带时间戳的备份文件
- 支持硬链接和复制两种方式

### 2. 链接检测阶段
- 扫描Excel中的所有超链接
- 解析相对和绝对路径
- 验证链接目标文件存在性

### 3. 文档处理阶段
- 使用Unstructured自动检测文档类型
- 提取结构化内容
- 支持错误回退机制

### 4. 内容格式化阶段
- 根据配置输出格式进行格式化
- 支持内容长度限制
- 添加元信息头部

### 5. Excel更新阶段
- 插入新的内容列
- 设置列标题格式
- 保存文件

### 6. 清理阶段
- 处理成功：删除备份文件
- 处理失败：从备份恢复文件

## 📊 处理结果格式

```python
{
    'file_path': 'your_file.xlsx',
    'processed_at': '2025-11-20T10:30:00',
    'total_links': 5,
    'successful': 4,
    'failed': 1,
    'errors': [
        '处理链接 document.pdf 失败: 文件不存在'
    ],
    'backup_path': './backup/20251120_103000_your_file.xlsx'
}
```

## 🐛 错误处理

### 常见错误及解决方案

1. **unstructured未安装**
   ```
   警告: 未安装unstructured库，将使用基础回退方案
   ```
   解决方案：`pip install unstructured[all-docs]`

2. **文件权限不足**
   ```
   处理失败: Permission denied
   ```
   解决方案：检查文件权限，确保有读写权限

3. **文档格式不支持**
   ```
   不支持的文件格式: .xyz
   ```
   解决方案：安装unstructured或转换文档格式

4. **Excel文件被占用**
   ```
   无法保存文件，请确保文件没有被其他程序打开
   ```
   解决方案：关闭Excel程序后重试

## 📈 性能优化建议

### 1. 单文件处理
- 设置 `enable_parallel_processing=False`
- 减少 `max_workers` 到1-2
- 限制 `max_content_length` 避免内存溢出

### 2. 批量处理
- 启用 `enable_parallel_processing=True`
- 设置合适的 `max_workers`（建议CPU核心数）
- 使用SSD存储提高I/O性能

### 3. 大文件处理
- 设置 `partition_strategy="fast"` 提升速度
- 调整 `max_content_length` 控制内存使用
- 启用错误继续处理 `continue_on_error=True`