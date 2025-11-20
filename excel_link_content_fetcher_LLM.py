# -*- coding: utf-8 -*-
"""
Excel链接内容提取器 - LLM增强版

基于Unstructured和多模态大模型的增强型Excel超链接文档内容提取工具，支持30+种文档格式，
通过LLM高精度的图片内容识别，替代低精度的传统OCR识别。
具备备份机制、错误恢复、性能优化等企业级特性。
"""

import os
import shutil
import time
import logging
import mimetypes
import tempfile
import base64
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font

try:
    from unstructured.partition.auto import partition

    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    partition = None

# 1. 屏蔽 pdfminer 的字体警告 (设置为只显示 ERROR 级别)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# 2. 屏蔽 huggingface 的下载警告
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# ==================== LLM多模态配置和数据结构 ====================


@dataclass
class MultimodalConfig:
    """多模态LLM处理配置"""

    # LLM模型配置
    vision_model_provider: str = "openai"  # openai, qwen
    vision_model_name: str = (
        "gpt-4-vision-preview"  # 或 "qwen-vl-plus" (通过OpenAI兼容方式调用)
    )
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    # 图片处理配置
    max_image_size: int = 10 * 1024 * 1024  # 10MB
    supported_image_formats: List[str] = field(
        default_factory=lambda: [".png", ".jpg", ".jpeg", ".gif", ".bmp"]
    )
    extract_embedded_images: bool = True

    # OCR替代配置
    enable_vision_ocr: bool = True
    vision_prompt: str = "请详细识别和描述这张图片中的所有文本内容，包括标题、正文、表格、图表等，保持原有的格式和结构。如果是表格，请用markdown表格格式输出。"

    # 批处理配置
    batch_size: int = 5
    max_retries: int = 3
    retry_delay: float = 1.0

    # 成本控制
    max_tokens_per_image: int = 2000
    enable_caching: bool = True


@dataclass
class ImageContentInfo:
    """图片内容信息"""

    image_id: int
    source_path: str
    processed_content: str
    alt_text: str = ""
    extraction_type: str = "embedded"  # embedded, external, screenshot
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==================== 原有配置和数据结构 ====================


@dataclass
class DocumentContent:
    """文档内容结构"""

    sections: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    full_text: str

    def __post_init__(self):
        """后处理验证"""
        if not isinstance(self.sections, list):
            self.sections = []
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        if not isinstance(self.full_text, str):
            self.full_text = ""


@dataclass
class DocumentProcessingConfig:
    """文档处理配置"""

    # Unstructured配置
    partition_strategy: str = "hi_res"  # hi_res, fast, ocr_only
    model_name: Optional[str] = None
    languages: List[str] = field(default_factory=lambda: ["zh", "en"])

    # 输出配置
    output_format: str = "markdown"  # markdown, plain_text, json
    max_content_length: int = 10000
    include_metadata: bool = True

    # 安全配置
    backup_enabled: bool = True
    backup_location: str = "./backup/"
    continue_on_error: bool = True
    max_retries: int = 3

    # 性能配置
    enable_parallel_processing: bool = True
    max_workers: int = 4
    memory_limit_mb: int = 512

    # LLM多模态配置
    enable_multimodal: bool = False
    multimodal_config: Optional[MultimodalConfig] = None

    def __post_init__(self):
        """后处理初始化"""
        # 确保languages不为空
        if not self.languages:
            self.languages = ["zh", "en"]

        # 验证输出格式
        valid_formats = ["markdown", "plain_text", "json"]
        if self.output_format not in valid_formats:
            self.output_format = "markdown"

        # 验证分区策略
        valid_strategies = ["hi_res", "fast", "ocr_only"]
        if self.partition_strategy not in valid_strategies:
            self.partition_strategy = "hi_res"

        # 验证多模态配置
        if self.enable_multimodal and not self.multimodal_config:
            self.multimodal_config = MultimodalConfig()


@dataclass
class HyperlinkInfo:
    """超链接信息"""

    cell: openpyxl.cell.Cell
    target: str
    display_text: Union[str, int, float]

    def __post_init__(self):
        """后处理验证"""
        if self.display_text is None:
            self.display_text = ""


# ==================== LLM多模态处理器 ====================


class MultimodalProcessor:
    """多模态大模型处理器，用于高精度图片内容解析"""

    def __init__(self, config: MultimodalConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._cache = {} if config.enable_caching else None

    def extract_and_process_images(self, file_path: str) -> List[ImageContentInfo]:
        """
        提取并处理文档中的图片

        Args:
            file_path: 文档文件路径

        Returns:
            List[ImageContentInfo]: 处理后的图片内容信息列表
        """
        try:
            # 1. 提取嵌入图片
            extracted_images = self._extract_embedded_images(file_path)

            # 2. 处理外部图片引用
            external_images = self._extract_external_images(file_path)

            # 3. 合并所有图片
            all_images = extracted_images + external_images

            # 4. 批量处理图片
            processed_images = []
            for img_info in all_images:
                try:
                    processed_content = self._process_single_image(
                        img_info["source_path"]
                    )
                    processed_images.append(
                        ImageContentInfo(
                            image_id=len(processed_images),
                            source_path=img_info["source_path"],
                            processed_content=processed_content,
                            alt_text=img_info.get("alt_text", ""),
                            extraction_type=img_info.get("type", "embedded"),
                        )
                    )
                except Exception as e:
                    self.logger.error(
                        f"处理图片失败 {img_info.get('source_path', 'unknown')}: {e}"
                    )
                    processed_images.append(
                        ImageContentInfo(
                            image_id=len(processed_images),
                            source_path=img_info.get("source_path", "unknown"),
                            processed_content=f"[图片处理失败: {str(e)}]",
                            alt_text=img_info.get("alt_text", ""),
                            extraction_type=img_info.get("type", "embedded"),
                        )
                    )

            return processed_images

        except Exception as e:
            self.logger.error(f"图片提取和处理失败: {e}")
            return []

    def _extract_embedded_images(self, file_path: str) -> List[Dict[str, Any]]:
        """提取文档中的嵌入图片"""
        images = []

        try:
            _, extension = os.path.splitext(file_path.lower())

            if extension == ".pdf":
                images = self._extract_pdf_images(file_path)
            elif extension in [".docx", ".pptx"]:
                images = self._extract_office_images(file_path, extension)
            elif extension == ".html":
                images = self._extract_html_images(file_path)
            elif extension == ".epub":
                images = self._extract_epub_images(file_path)

        except Exception as e:
            self.logger.error(f"提取嵌入图片失败: {e}")

        return images

    def _extract_pdf_images(self, pdf_path: str) -> List[Dict[str, Any]]:
        """提取PDF中的图片"""
        try:
            # 尝试使用PyMuPDF提取图片
            import fitz  # PyMuPDF

            images = []
            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images(full=True)

                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)

                        if pix.n - pix.alpha < 4:  # GRAY or RGB
                            temp_path = f"{pdf_path}_img_{page_num}_{img_index}.png"
                            pix.save(temp_path)

                            images.append(
                                {
                                    "source_path": temp_path,
                                    "alt_text": f"PDF图片 - 页面{page_num + 1}, 图片{img_index + 1}",
                                    "type": "pdf_embedded",
                                }
                            )
                    except Exception as e:
                        self.logger.warning(f"提取PDF图片失败: {e}")

            doc.close()
            return images

        except ImportError:
            self.logger.warning("未安装PyMuPDF，跳过PDF图片提取")
            return []
        except Exception as e:
            self.logger.error(f"PDF图片提取失败: {e}")
            return []

    def _extract_office_images(
        self, file_path: str, extension: str
    ) -> List[Dict[str, Any]]:
        """提取Office文档中的图片"""
        images = []

        try:
            if extension == ".docx":
                # 使用python-docx提取图片
                try:
                    from docx import Document
                    from docx.document import Document as _Document
                    from docx.oxml.table import CT_Tbl
                    from docx.oxml.text.paragraph import CT_P
                    from docx.table import _Cell, Table
                    from docx.text.paragraph import Paragraph

                    doc = Document(file_path)

                    # 遍历所有段落和表格中的图片
                    for element in doc.element.body:
                        if isinstance(element, CT_P):
                            paragraph = Paragraph(element, doc)
                            for run in paragraph.runs:
                                for inline_shape in run._element.xpath(".//a:blip"):
                                    # 这里需要更复杂的处理来提取实际图片
                                    pass

                except ImportError:
                    self.logger.warning("未安装python-docx，跳过Word文档图片提取")

            elif extension == ".pptx":
                # 使用python-pptx提取图片
                try:
                    from pptx import Presentation

                    prs = Presentation(file_path)

                    for slide_num, slide in enumerate(prs.slides):
                        for shape in slide.shapes:
                            if hasattr(shape, "image"):
                                try:
                                    image = shape.image
                                    temp_path = f"{file_path}_slide_{slide_num + 1}_img_{len(images)}.png"

                                    with open(temp_path, "wb") as f:
                                        f.write(image.blob)

                                    images.append(
                                        {
                                            "source_path": temp_path,
                                            "alt_text": f"PPT图片 - 幻灯片{slide_num + 1}",
                                            "type": "pptx_embedded",
                                        }
                                    )
                                except Exception as e:
                                    self.logger.warning(f"提取PPT图片失败: {e}")

                except ImportError:
                    self.logger.warning("未安装python-pptx，跳过PowerPoint文档图片提取")

        except Exception as e:
            self.logger.error(f"Office文档图片提取失败: {e}")

        return images

    def _extract_html_images(self, html_path: str) -> List[Dict[str, Any]]:
        """提取HTML中的图片"""
        try:
            from bs4 import BeautifulSoup

            images = []
            with open(html_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            # 处理<img>标签
            for i, img in enumerate(soup.find_all("img")):
                src = img.get("src")
                alt = img.get("alt", "")
                if src:
                    if src.startswith(("http://", "https://")):
                        # 网络图片，需要下载
                        temp_path = f"{html_path}_web_img_{i}.jpg"
                        images.append(
                            {
                                "source_path": temp_path,
                                "alt_text": alt,
                                "type": "html_web_image",
                                "url": src,
                            }
                        )
                    elif os.path.isfile(src):
                        # 本地图片文件
                        images.append(
                            {
                                "source_path": os.path.abspath(src),
                                "alt_text": alt,
                                "type": "html_local_image",
                            }
                        )

            return images

        except ImportError:
            self.logger.warning("未安装BeautifulSoup4，跳过HTML图片提取")
            return []
        except Exception as e:
            self.logger.error(f"HTML图片提取失败: {e}")
            return []

    def _extract_epub_images(self, epub_path: str) -> List[Dict[str, Any]]:
        """提取EPUB电子书中的图片"""
        try:
            import zipfile
            import xml.etree.ElementTree as ET

            images = []

            with zipfile.ZipFile(epub_path, "r") as epub:
                # 获取图片文件列表
                image_files = [
                    f
                    for f in epub.namelist()
                    if f.startswith("OEBPS/images/") or f.startswith("images/")
                ]

                for i, img_file in enumerate(image_files):
                    try:
                        # 提取图片到临时文件
                        temp_path = f"{epub_path}_epub_img_{i}.png"
                        with (
                            epub.open(img_file) as source,
                            open(temp_path, "wb") as target,
                        ):
                            target.write(source.read())

                        images.append(
                            {
                                "source_path": temp_path,
                                "alt_text": f"EPUB图片 {i + 1}",
                                "type": "epub_embedded",
                                "source_in_epub": img_file,
                            }
                        )
                    except Exception as e:
                        self.logger.warning(f"提取EPUB图片失败: {e}")

            return images

        except Exception as e:
            self.logger.error(f"EPUB图片提取失败: {e}")
            return []

    def _extract_external_images(self, file_path: str) -> List[Dict[str, Any]]:
        """提取外部引用的图片（截图、附件等）"""
        # 这里可以扩展处理外部图片文件
        # 比如同一目录下的图片文件，或文档中引用的外部图片链接
        return []

    def _process_single_image(self, image_path: str) -> str:
        """使用多模态模型处理单张图片"""
        try:
            # 检查缓存
            if self._cache and image_path in self._cache:
                return self._cache[image_path]

            # 检查文件是否存在
            if not os.path.exists(image_path):
                return f"[图片文件不存在: {image_path}]"

            # 检查文件大小
            file_size = os.path.getsize(image_path)
            if file_size > self.config.max_image_size:
                return f"[图片文件过大: {file_size} bytes, 最大允许: {self.config.max_image_size} bytes]"

            # 根据模型提供商选择处理方式
            if self.config.vision_model_provider == "openai":
                result = self._process_with_openai_vision(image_path)
            elif self.config.vision_model_provider == "qwen":
                result = self._process_with_qwen_vision(image_path)
            else:
                result = f"[不支持的模型提供商: {self.config.vision_model_provider}]"

            # 缓存结果
            if self._cache:
                self._cache[image_path] = result

            return result

        except Exception as e:
            return f"[图片处理失败: {str(e)}]"

    def _process_with_openai_vision(self, image_path: str) -> str:
        """使用OpenAI GPT-4V处理图片"""
        try:
            from openai import OpenAI

            # 创建客户端
            client_params = {"api_key": self.config.api_key}
            if self.config.api_base:
                client_params["base_url"] = self.config.api_base

            client = OpenAI(**client_params)

            # 读取图片并转换为base64
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

            # 调用API
            response = client.chat.completions.create(
                model=self.config.vision_model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.config.vision_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}",
                                    "detail": "high",  # 高精度模式
                                },
                            },
                        ],
                    }
                ],
                max_tokens=self.config.max_tokens_per_image,
            )

            return response.choices[0].message.content

        except ImportError:
            return "[错误: 请安装openai库: pip install openai]"
        except Exception as e:
            return f"[OpenAI处理失败: {str(e)}]"

    def _process_with_qwen_vision(self, image_path: str) -> str:
        """使用通义千问Qwen-VL通过OpenAI兼容方式处理图片"""
        try:
            from openai import OpenAI

            # 配置OpenAI兼容的客户端
            client_params = {"api_key": self.config.api_key}

            # 设置DashScope的OpenAI兼容API端点
            if not self.config.api_base:
                self.config.api_base = (
                    "https://dashscope.aliyuncs.com/compatible-mode/v1"
                )

            client_params["base_url"] = self.config.api_base

            client = OpenAI(**client_params)

            # 读取图片并转换为base64
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

            # 调用OpenAI兼容的Qwen-VL API
            response = client.chat.completions.create(
                model=self.config.vision_model_name,  # 例如: "qwen-vl-plus"
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.config.vision_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=self.config.max_tokens_per_image,
                temperature=0.1,
            )

            return response.choices[0].message.content

        except ImportError:
            return "[错误: 请安装openai库: pip install openai]"
        except Exception as e:
            return f"[Qwen处理失败: {str(e)}]"

    def cleanup_temporary_files(self, image_contents: List[ImageContentInfo]):
        """清理临时文件"""
        for img_info in image_contents:
            try:
                if img_info.source_path.startswith(tempfile.gettempdir()):
                    if os.path.exists(img_info.source_path):
                        os.remove(img_info.source_path)
            except Exception as e:
                self.logger.warning(f"清理临时文件失败 {img_info.source_path}: {e}")


# ==================== 原有核心处理模块 ====================


class UnifiedDocumentProcessor:
    """基于Unstructured的统一文档处理器，支持LLM多模态增强"""

    def __init__(self, config: DocumentProcessingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.partition_options = self._build_partition_options()

        # 初始化多模态处理器
        if self.config.enable_multimodal and self.config.multimodal_config:
            self.multimodal_processor = MultimodalProcessor(
                self.config.multimodal_config
            )
        else:
            self.multimodal_processor = None

    def _build_partition_options(self) -> Dict[str, Any]:
        """构建Unstructured分区选项"""
        options = {
            "strategy": self.config.partition_strategy,
            "languages": self.config.languages,
        }

        if self.config.model_name:
            options["model_name"] = self.config.model_name

        return options

    def process_document(self, file_path: str) -> DocumentContent:
        """
        统一的文档处理接口，支持LLM多模态增强

        Args:
            file_path: 文档文件路径

        Returns:
            DocumentContent: 包含提取内容和元信息的结构化对象
        """
        try:
            # 1. 文件存在性检查
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文档文件不存在: {file_path}")

            # 2. 检查unstructured是否可用
            if not UNSTRUCTURED_AVAILABLE:
                self.logger.warning("unstructured库未安装，使用回退处理方案")
                doc_content = self._fallback_process_document(file_path)
            else:
                # 使用Unstructured处理基础内容
                elements = partition(filename=file_path, **self.partition_options)
                doc_content = self._extract_structured_content(elements, file_path)

            # 3. 如果启用多模态，额外处理图片内容
            if self.config.enable_multimodal and self.multimodal_processor:
                try:
                    self.logger.info(f"开始LLM多模态处理: {file_path}")
                    image_contents = (
                        self.multimodal_processor.extract_and_process_images(file_path)
                    )

                    # 将图片内容合并到文档内容中
                    if image_contents:
                        doc_content = self._merge_image_content(
                            doc_content, image_contents
                        )
                        self.logger.info(
                            f"LLM多模态处理完成，提取到 {len(image_contents)} 张图片"
                        )
                    else:
                        self.logger.info("未发现图片内容")

                except Exception as e:
                    self.logger.warning(f"LLM多模态处理失败，使用文本处理结果: {e}")

            return doc_content

        except Exception as e:
            self.logger.error(f"文档处理失败 {file_path}: {e}")
            return self._handle_processing_error(file_path, e)

    def _extract_structured_content(self, elements, file_path: str) -> DocumentContent:
        """提取结构化内容"""
        content_sections = []
        metadata = {
            "file_path": file_path,
            "file_type": self._detect_file_type(file_path),
            "processing_timestamp": datetime.now().isoformat(),
            "element_count": len(elements) if elements else 0,
        }

        if elements:
            for element in elements:
                if hasattr(element, "text") and element.text.strip():
                    content_sections.append(
                        {
                            "type": getattr(element, "category", "text"),
                            "content": element.text.strip(),
                            "metadata": getattr(element, "metadata", {}),
                        }
                    )

        return DocumentContent(
            sections=content_sections,
            metadata=metadata,
            full_text="\n".join([s["content"] for s in content_sections]),
        )

    def _merge_image_content(
        self, doc_content: DocumentContent, image_contents: List[ImageContentInfo]
    ) -> DocumentContent:
        """合并图片内容到文档内容中"""
        try:
            # 为每个处理过的图片添加内容段落
            for img_info in image_contents:
                if img_info.processed_content:
                    img_section = {
                        "type": "image_content",
                        "content": f"\n## 图片内容识别结果 (ID: {img_info.image_id})\n\n{img_info.processed_content}",
                        "metadata": {
                            "image_id": img_info.image_id,
                            "alt_text": img_info.alt_text,
                            "extraction_type": img_info.extraction_type,
                            "source_path": img_info.source_path,
                            "llm_processed": True,
                        },
                    }
                    doc_content.sections.append(img_section)

            # 更新完整文本
            image_texts = [
                section["content"]
                for section in doc_content.sections
                if section["type"] == "image_content"
            ]
            if image_texts:
                doc_content.full_text += "\n" + "\n".join(image_texts)

            # 更新元数据
            doc_content.metadata["image_count"] = len(image_contents)
            doc_content.metadata["llm_multimodal_processed"] = True
            doc_content.metadata["multimodal_provider"] = (
                self.config.multimodal_config.vision_model_provider
                if self.config.multimodal_config
                else None
            )

            # 清理临时文件
            if hasattr(self, "multimodal_processor"):
                self.multimodal_processor.cleanup_temporary_files(image_contents)

            return doc_content

        except Exception as e:
            self.logger.error(f"合并图片内容失败: {e}")
            return doc_content

    def _detect_file_type(self, file_path: str) -> str:
        """检测文件类型"""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "unknown"

    def _fallback_process_document(self, file_path: str) -> DocumentContent:
        """回退处理方案（当unstructured不可用时）"""
        self.logger.info(f"使用回退方案处理: {file_path}")

        try:
            _, extension = os.path.splitext(file_path.lower())

            if extension == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif extension == ".md":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif extension == ".csv":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif extension == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = f"不支持的文件格式: {extension}\n请安装unstructured库以支持更多格式。"

            return DocumentContent(
                sections=[
                    {"type": "text", "content": content, "metadata": {"fallback": True}}
                ],
                metadata={
                    "file_path": file_path,
                    "file_type": extension,
                    "processing_timestamp": datetime.now().isoformat(),
                    "fallback_method": True,
                },
                full_text=content,
            )

        except Exception as e:
            return self._handle_processing_error(file_path, e)

    def _handle_processing_error(
        self, file_path: str, error: Exception
    ) -> DocumentContent:
        """处理处理错误"""
        error_content = f"文档处理失败: {str(error)}"

        return DocumentContent(
            sections=[
                {
                    "type": "error",
                    "content": error_content,
                    "metadata": {"error_type": type(error).__name__},
                }
            ],
            metadata={
                "file_path": file_path,
                "processing_error": str(error),
                "error_type": type(error).__name__,
                "processing_timestamp": datetime.now().isoformat(),
            },
            full_text=error_content,
        )

    def get_supported_formats(self) -> List[str]:
        """获取支持的文档格式列表"""
        if UNSTRUCTURED_AVAILABLE:
            return [
                ".pdf",
                ".docx",
                ".doc",
                ".txt",
                ".md",
                ".rtf",
                ".html",
                ".htm",
                ".xml",
                ".json",
                ".csv",
                ".pptx",
                ".ppt",
                ".xlsx",
                ".xls",
                ".odt",
                ".epub",
                ".mobi",
                ".log",
                ".msg",
            ]
        else:
            return [".txt", ".md", ".csv", ".json"]


# ==================== 备份管理模块 ====================


class BackupManager:
    """文件备份管理器"""

    def __init__(self, backup_dir: str = "./backup/"):
        self.backup_dir = backup_dir
        Path(backup_dir).mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def create_backup(self, file_path: str) -> str:
        """
        创建文件备份

        Args:
            file_path: 原始文件路径

        Returns:
            str: 备份文件路径
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = Path(file_path).name
            backup_name = f"{timestamp}_{file_name}"
            backup_path = Path(self.backup_dir) / backup_name

            # 优先使用硬链接（节省空间）
            try:
                os.link(file_path, str(backup_path))
                self.logger.info(f"创建硬链接备份: {backup_path}")
            except (OSError, AttributeError):
                # 跨平台兼容的回退方案
                shutil.copy2(file_path, str(backup_path))
                self.logger.info(f"创建文件备份: {backup_path}")

            return str(backup_path)

        except Exception as e:
            self.logger.error(f"创建备份失败 {file_path}: {e}")
            raise

    def cleanup_old_backups(self, days_to_keep: int = 30):
        """清理旧备份文件"""
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        cleaned_count = 0

        for backup_file in Path(self.backup_dir).glob("*"):
            try:
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    cleaned_count += 1
            except OSError as e:
                self.logger.warning(f"删除备份文件失败 {backup_file}: {e}")

        self.logger.info(f"清理了 {cleaned_count} 个旧备份文件")
        return cleaned_count

    def restore_backup(self, backup_path: str, original_path: str) -> bool:
        """
        从备份恢复文件

        Args:
            backup_path: 备份文件路径
            original_path: 原始文件路径

        Returns:
            bool: 恢复是否成功
        """
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, original_path)
                self.logger.info(f"从备份恢复文件: {original_path}")
                return True
            else:
                self.logger.error(f"备份文件不存在: {backup_path}")
                return False
        except Exception as e:
            self.logger.error(f"恢复文件失败 {backup_path} -> {original_path}: {e}")
            return False


# ==================== Excel处理模块 ====================


class ExcelLinkProcessor:
    """Excel超链接处理器"""

    def __init__(self, document_processor: UnifiedDocumentProcessor):
        self.document_processor = document_processor
        self.logger = logging.getLogger(__name__)

    def find_hyperlinks(self, sheet) -> List[HyperlinkInfo]:
        """查找Excel中的超链接"""
        links = []

        for row in sheet.iter_rows():
            for cell in row:
                if cell.hyperlink and cell.hyperlink.target:
                    links.append(
                        HyperlinkInfo(
                            cell=cell,
                            target=cell.hyperlink.target,
                            display_text=cell.value,
                        )
                    )

        self.logger.info(f"找到 {len(links)} 个超链接")
        return links

    def resolve_path(self, link_target: str, base_dir: str) -> str:
        """
        解析链接路径，支持相对和绝对路径

        Args:
            link_target: 链接目标路径
            base_dir: Excel文件所在目录

        Returns:
            str: 解析后的绝对路径
        """
        try:
            if os.path.isabs(link_target):
                return link_target

            # 处理相对路径
            resolved_path = os.path.join(base_dir, link_target)
            return os.path.normpath(resolved_path)

        except Exception as e:
            self.logger.error(f"路径解析失败 {link_target}: {e}")
            return link_target


# ==================== 内容格式化模块 ====================


class ContentFormatter:
    """内容格式化器"""

    def __init__(self, config: DocumentProcessingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def format_content(self, doc_content: DocumentContent) -> str:
        """格式化文档内容"""
        if self.config.output_format == "markdown":
            return self._to_markdown(doc_content)
        elif self.config.output_format == "plain_text":
            return doc_content.full_text
        elif self.config.output_format == "json":
            import json

            return json.dumps(doc_content.__dict__, ensure_ascii=False, indent=2)
        else:
            return self._to_markdown(doc_content)  # 默认返回markdown

    def _to_markdown(self, doc_content: DocumentContent) -> str:
        """转换为Markdown格式"""
        markdown_parts = []

        # 添加文件信息头部（如果启用）
        if self.config.include_metadata:
            markdown_parts.append("```metadata")
            markdown_parts.append(
                f"文件: {doc_content.metadata.get('file_path', '未知')}"
            )
            markdown_parts.append(
                f"类型: {doc_content.metadata.get('file_type', '未知')}"
            )
            markdown_parts.append(
                f"处理时间: {doc_content.metadata.get('processing_timestamp', '未知')}"
            )
            if "element_count" in doc_content.metadata:
                markdown_parts.append(
                    f"元素数量: {doc_content.metadata['element_count']}"
                )
            if doc_content.metadata.get("fallback_method"):
                markdown_parts.append("注意: 使用回退方案处理")
            if doc_content.metadata.get("llm_multimodal_processed"):
                markdown_parts.append(
                    f"LLM多模态处理: ✅ ({doc_content.metadata.get('multimodal_provider', 'unknown')})"
                )
                if "image_count" in doc_content.metadata:
                    markdown_parts.append(
                        f"图片数量: {doc_content.metadata['image_count']}"
                    )
            markdown_parts.append("```")
            markdown_parts.append("")

        # 添加内容段落
        for section in doc_content.sections:
            content = section["content"]

            # 内容长度限制
            if len(content) > self.config.max_content_length:
                content = (
                    content[: self.config.max_content_length] + "...\n\n[内容已截断]"
                )

            # 添加类型标识（如果内容不为空）
            if content.strip():
                section_type = section.get("type", "text")
                if section_type == "image_content":
                    markdown_parts.append(f"### 图片内容识别\n\n{content}\n")
                else:
                    markdown_parts.append(f"```\n{content}\n```")

        if not markdown_parts:
            markdown_parts.append("```\n[无内容]\n```")

        return "\n".join(markdown_parts)


# ==================== 主要接口类 ====================


class EnhancedExcelProcessorLLM:
    """增强的Excel处理器 - LLM多模态版"""

    def __init__(self, config: Optional[DocumentProcessingConfig] = None):
        self.config = config or DocumentProcessingConfig()
        self.backup_manager = BackupManager(self.config.backup_location)
        self.document_processor = UnifiedDocumentProcessor(self.config)
        self.content_formatter = ContentFormatter(self.config)
        self.excel_processor = ExcelLinkProcessor(self.document_processor)

        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("excel_processor_llm.log", encoding="utf-8"),
            ],
        )
        self.logger = logging.getLogger(__name__)

        self.logger.info("LLM增强版Excel处理器初始化完成")

    def process_excel_file(
        self, excel_path: str, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        处理Excel文件中的链接文档，支持LLM多模态增强

        Args:
            excel_path: Excel文件路径
            dry_run: 是否为演练模式

        Returns:
            Dict: 处理结果
        """
        results = {
            "file_path": excel_path,
            "processed_at": datetime.now().isoformat(),
            "dry_run": dry_run,
            "total_links": 0,
            "successful": 0,
            "failed": 0,
            "errors": [],
            "backup_path": None,
            "multimodal_processed": False,
        }

        workbook = None
        try:
            # 1. 加载Excel文件
            self.logger.info(f"加载Excel文件: {excel_path}")
            workbook = openpyxl.load_workbook(excel_path)
            sheet = workbook.active

            # 2. 查找超链接
            links = self.excel_processor.find_hyperlinks(sheet)
            results["total_links"] = len(links)

            if not links:
                self.logger.info(f"Excel文件 '{excel_path}' 中未找到超链接")
                return results

            # 3. 创建备份
            backup_path = None
            if not dry_run and self.config.backup_enabled:
                backup_path = self.backup_manager.create_backup(excel_path)
                results["backup_path"] = backup_path
                self.logger.info(f"已创建备份: {backup_path}")

            # 4. 设置目标列
            first_link_col = links[0].cell.column
            content_col = first_link_col + 1

            if not dry_run:
                sheet.insert_cols(content_col)

                # 设置标题
                header_cell = sheet.cell(row=1, column=content_col)
                header_cell.value = "链接文档内容 (LLM增强)"
                header_cell.font = Font(bold=True)
                self.logger.info(f"在第 {get_column_letter(content_col)} 列插入内容列")

            # 5. 处理每个链接
            for link_info in links:
                try:
                    # 解析文件路径
                    base_dir = os.path.dirname(os.path.abspath(excel_path))
                    full_path = self.excel_processor.resolve_path(
                        link_info.target, base_dir
                    )

                    self.logger.info(f"处理链接: {link_info.target} -> {full_path}")

                    # 提取文档内容（包含LLM多模态处理）
                    doc_content = self.document_processor.process_document(full_path)

                    # 检查是否进行了多模态处理
                    if doc_content.metadata.get("llm_multimodal_processed"):
                        results["multimodal_processed"] = True

                    # 格式化内容
                    formatted_content = self.content_formatter.format_content(
                        doc_content
                    )

                    # 更新Excel单元格
                    if not dry_run:
                        content_cell = sheet.cell(
                            row=link_info.cell.row, column=content_col
                        )
                        content_cell.value = formatted_content

                    results["successful"] += 1
                    self.logger.info(f"✅ 处理完成: {link_info.target}")

                except Exception as e:
                    error_msg = f"处理链接 '{link_info.target}' 失败: {str(e)}"
                    results["errors"].append(error_msg)
                    results["failed"] += 1
                    self.logger.error(error_msg)

                    # 如果不继续处理错误，则停止
                    if not self.config.continue_on_error:
                        break

            # 6. 保存文件
            if not dry_run:
                workbook.save(excel_path)
                self.logger.info(f"Excel文件已更新: {excel_path}")

                # 删除备份（处理成功）
                if backup_path and os.path.exists(backup_path):
                    os.remove(backup_path)
                    self.logger.info(f"删除备份文件: {backup_path}")

        except Exception as e:
            error_msg = f"Excel文件处理失败: {str(e)}"
            results["errors"].append(error_msg)
            self.logger.error(error_msg)

            # 恢复备份
            if results["backup_path"] and os.path.exists(results["backup_path"]):
                if self.backup_manager.restore_backup(
                    results["backup_path"], excel_path
                ):
                    self.logger.info(f"文件已从备份恢复: {excel_path}")

        finally:
            if workbook:
                workbook.close()

        return results

    def process_multiple_files(
        self, file_paths: List[str], max_workers: int = None
    ) -> Dict[str, Dict[str, Any]]:
        """批量处理多个Excel文件"""
        if not max_workers:
            max_workers = (
                self.config.max_workers if hasattr(self.config, "max_workers") else 4
            )

        if not self.config.enable_parallel_processing:
            max_workers = 1

        results = {}
        self.logger.info(
            f"开始批量处理 {len(file_paths)} 个文件，使用 {max_workers} 个线程"
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_file = {
                executor.submit(self.process_excel_file, file_path): file_path
                for file_path in file_paths
            }

            # 收集结果
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    results[file_path] = future.result()
                except Exception as e:
                    results[file_path] = {
                        "file_path": file_path,
                        "error": str(e),
                        "successful": 0,
                        "failed": 0,
                        "processed_at": datetime.now().isoformat(),
                    }
                    self.logger.error(f"批量处理文件失败 {file_path}: {e}")

        self.logger.info(
            f"批量处理完成，成功: {sum(r.get('successful', 0) for r in results.values())}"
        )
        return results

    def get_supported_formats(self) -> List[str]:
        """获取支持的文档格式列表"""
        return self.document_processor.get_supported_formats()

    def validate_environment(self) -> Dict[str, Any]:
        """验证运行环境"""
        validation_results = {}

        # 检查基础依赖
        try:
            import unstructured

            validation_results["unstructured"] = True
            validation_results["unstructured_version"] = getattr(
                unstructured, "__version__", "unknown"
            )
        except ImportError:
            validation_results["unstructured"] = False
            validation_results["unstructured_version"] = None

        try:
            import openpyxl

            validation_results["openpyxl"] = True
            validation_results["openpyxl_version"] = getattr(
                openpyxl, "__version__", "unknown"
            )
        except ImportError:
            validation_results["openpyxl"] = False
            validation_results["openpyxl_version"] = None

        # 检查多模态依赖
        try:
            import openai

            validation_results["openai"] = True
            validation_results["openai_version"] = getattr(
                openai, "__version__", "unknown"
            )
        except ImportError:
            validation_results["openai"] = False
            validation_results["openai_version"] = None

        # 检查图片处理依赖
        try:
            import fitz  # PyMuPDF

            validation_results["pymupdf"] = True
        except ImportError:
            validation_results["pymupdf"] = False

        try:
            from bs4 import BeautifulSoup

            validation_results["beautifulsoup4"] = True
        except ImportError:
            validation_results["beautifulsoup4"] = False

        # 检查备份目录
        backup_dir = Path(self.config.backup_location)
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            validation_results["backup_dir"] = True
        except OSError:
            validation_results["backup_dir"] = False

        return validation_results

    def print_environment_report(self):
        """打印环境报告"""
        print("=" * 70)
        print("Excel链接内容提取器 - LLM增强版环境报告")
        print("=" * 70)

        validation = self.validate_environment()

        print(
            f"Unstructured库: {'✅ 已安装' if validation['unstructured'] else '❌ 未安装'}"
        )
        if validation.get("unstructured_version"):
            print(f"  版本: {validation['unstructured_version']}")

        print(f"OpenPyXL库: {'✅ 已安装' if validation['openpyxl'] else '❌ 未安装'}")
        if validation.get("openpyxl_version"):
            print(f"  版本: {validation['openpyxl_version']}")

        print(f"OpenAI库: {'✅ 已安装' if validation['openai'] else '❌ 未安装'}")
        if validation.get("openai_version"):
            print(f"  版本: {validation['openai_version']}")

        print(
            f"PyMuPDF库: {'✅ 已安装' if validation['pymupdf'] else '❌ 未安装'} (PDF图片提取)"
        )
        print(
            f"BeautifulSoup4: {'✅ 已安装' if validation['beautifulsoup4'] else '❌ 未安装'} (HTML图片提取)"
        )

        print(f"备份目录: {'✅ 可写' if validation['backup_dir'] else '❌ 不可写'}")
        print(f"  位置: {self.config.backup_location}")

        print(
            f"\n多模态功能: {'✅ 已启用' if self.config.enable_multimodal else '❌ 未启用'}"
        )
        if self.config.enable_multimodal and self.config.multimodal_config:
            provider = self.config.multimodal_config.vision_model_provider
            print(f"  模型提供商: {provider}")
            print(f"  模型名称: {self.config.multimodal_config.vision_model_name}")
            print(
                f"  图片OCR: {'✅ 启用' if self.config.multimodal_config.enable_vision_ocr else '❌ 禁用'}"
            )

        print("\n支持的文档格式:")
        formats = self.get_supported_formats()
        for i, fmt in enumerate(formats, 1):
            print(f"  {i:2d}. {fmt}")

        print("\n配置信息:")
        print(f"  输出格式: {self.config.output_format}")
        print(f"  分区策略: {self.config.partition_strategy}")
        print(f"  备份启用: {self.config.backup_enabled}")
        print(f"  并行处理: {self.config.enable_parallel_processing}")
        print(f"  最大工作线程: {self.config.max_workers}")
        print(f"  LLM多模态: {self.config.enable_multimodal}")

        if not validation["unstructured"]:
            print("\n⚠️  警告: 未安装unstructured库，将使用基础回退方案")
            print("   建议安装: pip install unstructured[all-docs]")

        if self.config.enable_multimodal and not validation.get("openai"):
            print("\n⚠️  警告: 启用了多模态功能但未安装LLM库")
            print("   建议安装: pip install openai")

        print("=" * 70)


# ==================== 便捷接口 ====================


def create_llm_processor(
    config: Optional[DocumentProcessingConfig] = None,
) -> EnhancedExcelProcessorLLM:
    """创建LLM增强版Excel处理器的便捷函数"""
    return EnhancedExcelProcessorLLM(config)


def process_excel_links_llm(
    excel_path: str,
    config: Optional[DocumentProcessingConfig] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    处理Excel文件中链接的LLM增强版便捷函数

    Args:
        excel_path: Excel文件路径
        config: 处理配置
        dry_run: 是否为演练模式

    Returns:
        Dict: 处理结果
    """
    processor = create_llm_processor(config)
    return processor.process_excel_file(excel_path, dry_run)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("Excel链接内容提取器 v2.0.0 - LLM多模态增强版")
    print("替代传统OCR，采用多模态大模型进行高精度图片内容识别")
    print()

    # 1. 创建多模态配置
    multimodal_config = MultimodalConfig(
        vision_model_provider="qwen",  # 使用qwen提供商
        vision_model_name="qwen-vl-plus",  # 通义千问视觉模型
        api_key=os.environ.get("QWEN_V"),  # 需要设置DashScope API密钥
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",  # OpenAI兼容端点
        enable_vision_ocr=True,
        extract_embedded_images=True,
        vision_prompt="请详细识别和描述这张图片中的所有文本内容，包括标题、正文、表格、图表等，保持原有的格式和结构。如果是表格，请用markdown表格格式输出。",
        max_tokens_per_image=2000,
        enable_caching=True,
    )

    # 2. 创建处理器配置
    config = DocumentProcessingConfig(
        output_format="markdown",
        backup_enabled=True,
        enable_parallel_processing=False,  # 单文件处理设为False
        enable_multimodal=True,  # 启用LLM多模态功能
        multimodal_config=multimodal_config,
    )

    # 3. 创建处理器
    processor = EnhancedExcelProcessorLLM(config)

    # 4. 打印详细环境报告
    processor.print_environment_report()

    # 5. 示例用法（需要修改为实际的Excel文件路径）
    excel_file = "C:\\Users\\Admin\\Desktop\\text\\任务管理.xlsx"

    if os.path.exists(excel_file):
        print(f"\n开始处理Excel文件: {excel_file}")
        print("=" * 60)

        # 首先进行演练
        print("🔍 执行演练模式...")
        result = processor.process_excel_file(excel_file, dry_run=True)
        print(f"演练结果:")
        print(f"  ✅ 成功处理: {result['successful']} 个链接")
        print(f"  ❌ 处理失败: {result['failed']} 个链接")
        print(f"  🖼️  LLM多模态处理: {'是' if result['multimodal_processed'] else '否'}")

        if result["errors"]:
            print(f"  ⚠️  错误信息:")
            for error in result["errors"]:
                print(f"    - {error}")

        # 如果演练成功，执行实际处理
        if result["successful"] > 0:
            print("\n🚀 演练成功，开始实际处理...")
            final_result = processor.process_excel_file(excel_file, dry_run=False)
            print(f"实际处理结果:")
            print(f"  ✅ 成功处理: {final_result['successful']} 个链接")
            print(f"  ❌ 处理失败: {final_result['failed']} 个链接")
            print(
                f"  🖼️  LLM多模态处理: {'是' if final_result['multimodal_processed'] else '否'}"
            )
            print(f"  📁 备份文件: {final_result.get('backup_path', '无')}")
        else:
            print("\n❌ 演练失败，未能处理任何链接")
    else:
        print("💡 使用示例:")
        print("  python excel_link_content_fetcher_LLM.py")
        print()
        print("📝 配置说明:")
        print("  1. 在代码中设置您的Excel文件路径")
        print("  2. 配置您的LLM API密钥")
        print("  3. 根据需要调整多模态处理参数")
        print()
        print("🔑 支持的API密钥:")
        print("  - OpenAI: https://platform.openai.com/api-keys")
        print("  - 通义千问(DashScope): https://dashscope.console.aliyun.com/")
        print()
        print("📦 需要的依赖:")
        print("  pip install openai PyMuPDF beautifulsoup4")
