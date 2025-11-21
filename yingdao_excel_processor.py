# -*- coding: utf-8 -*-
"""
影刀RPA调用的Excel处理函数
适配影刀平台的调用方式，传入Excel路径和API密钥进行处理
"""

import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# 添加当前目录到Python路径，确保能找到excel_link_content_fetcher_LLM模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from excel_link_content_fetcher_LLM import (
        MultimodalConfig,
        DocumentProcessingConfig,
        EnhancedExcelProcessorLLM,
        DocumentProcessingConfig,
    )
except ImportError as e:
    raise ImportError(f"无法导入excel_link_content_fetcher_LLM模块: {e}")


def process_excel_with_qwen(
    excel_path: str,
    api_key: str,
    output_format: str = "markdown",
    max_workers: int = 1,
    enable_multimodal: bool = True,
    vision_prompt: Optional[str] = None,
    continue_on_error: bool = True,
) -> Dict[str, Any]:
    """
    影刀RPA调用的Excel超链接内容提取函数

    Args:
        excel_path: Excel文件路径
        api_key: Qwen/Vision API密钥
        output_format: 输出格式 (markdown/plain_text/json)
        max_workers: 最大并发线程数 (影刀调用建议设为1)
        enable_multimodal: 是否启用LLM多模态处理
        vision_prompt: 自定义视觉识别提示词
        continue_on_error: 遇到错误是否继续处理

    Returns:
        Dict: 处理结果，包含success、message、data等字段
    """

    # 验证输入参数
    if not excel_path:
        return {
            "success": False,
            "message": "Excel文件路径不能为空",
            "data": None,
            "timestamp": datetime.now().isoformat(),
        }

    if not api_key:
        return {
            "success": False,
            "message": "API密钥不能为空",
            "data": None,
            "timestamp": datetime.now().isoformat(),
        }

    # 检查Excel文件是否存在
    if not os.path.exists(excel_path):
        return {
            "success": False,
            "message": f"Excel文件不存在: {excel_path}",
            "data": None,
            "timestamp": datetime.now().isoformat(),
        }

    try:
        # 1. 配置Qwen多模态模型
        multimodal_config = MultimodalConfig(
            vision_model_provider="qwen",  # 使用Qwen提供商
            vision_model_name="qwen-vl-plus",  # Qwen视觉模型
            api_key=api_key,
            api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",  # OpenAI兼容端点
            enable_vision_ocr=True,
            extract_embedded_images=True,
            vision_prompt=vision_prompt
            or "请详细识别和描述这张图片中的所有文本内容，包括标题、正文、表格、图表等，保持原有的格式和结构。如果是表格，请用markdown表格格式输出。",
            max_tokens_per_image=2000,
            enable_caching=True,
        )

        # 2. 创建处理器配置
        config = DocumentProcessingConfig(
            output_format=output_format,
            enable_parallel_processing=False,  # 影刀调用时建议关闭并行处理
            max_workers=max_workers,
            enable_multimodal=enable_multimodal,
            multimodal_config=multimodal_config,
            continue_on_error=continue_on_error,
            download_timeout=60,  # 下载超时时间
        )

        # 3. 创建处理器
        processor = EnhancedExcelProcessorLLM(config)

        # 4. 处理Excel文件
        result = processor.process_excel_file(excel_path)

        # 5. 格式化返回结果，适配影刀调用
        processing_result = {
            "success": True,
            "message": "处理完成",
            "data": {
                "file_path": result.get("file_path"),
                "processed_at": result.get("processed_at"),
                "summary": {
                    "total_links": result.get("total_links", 0),
                    "successful": result.get("successful", 0),
                    "failed": result.get("failed", 0),
                    "error_count": len(result.get("errors", [])),
                    "multimodal_processed": result.get("multimodal_processed", False),
                },
                "errors": result.get("errors", []),
                "supported_formats": processor.get_supported_formats(),
            },
            "timestamp": datetime.now().isoformat(),
        }

        return processing_result

    except Exception as e:
        # 异常处理
        return {
            "success": False,
            "message": f"处理失败: {str(e)}",
            "data": {
                "excel_path": excel_path,
                "error_type": type(e).__name__,
                "full_traceback": str(e),
            },
            "timestamp": datetime.now().isoformat(),
        }


def batch_process_excels_with_qwen(
    excel_paths: list,
    api_key: str,
    output_format: str = "markdown",
    max_workers: int = 2,
) -> Dict[str, Any]:
    """
    批量处理多个Excel文件的函数

    Args:
        excel_paths: Excel文件路径列表
        api_key: Qwen/Vision API密钥
        output_format: 输出格式
        max_workers: 最大并发线程数

    Returns:
        Dict: 批量处理结果
    """

    if not excel_paths:
        return {
            "success": False,
            "message": "Excel文件路径列表不能为空",
            "data": None,
            "timestamp": datetime.now().isoformat(),
        }

    try:
        # 配置多模态模型
        multimodal_config = MultimodalConfig(
            vision_model_provider="qwen",
            vision_model_name="qwen-vl-plus",
            api_key=api_key,
            api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            enable_vision_ocr=True,
            extract_embedded_images=True,
            max_tokens_per_image=2000,
            enable_caching=True,
        )

        # 创建配置
        config = DocumentProcessingConfig(
            output_format=output_format,
            enable_parallel_processing=True,
            max_workers=max_workers,
            enable_multimodal=True,
            multimodal_config=multimodal_config,
        )

        # 创建处理器
        processor = EnhancedExcelProcessorLLM(config)

        # 批量处理
        results = processor.process_multiple_files(excel_paths, max_workers=max_workers)

        # 统计结果
        total_successful = sum(r.get("successful", 0) for r in results.values())
        total_failed = sum(r.get("failed", 0) for r in results.values())
        total_files = len(excel_paths)

        return {
            "success": True,
            "message": f"批量处理完成: {total_files}个文件, 成功: {total_successful}, 失败: {total_failed}",
            "data": {
                "total_files": total_files,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "results": results,
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"批量处理失败: {str(e)}",
            "data": None,
            "timestamp": datetime.now().isoformat(),
        }


# 影刀RPA调用的主函数
def main(excel_path: str, api_key: str, **kwargs) -> str:
    """
    影刀RPA平台调用的主函数

    Args:
        excel_path: Excel文件路径
        api_key: Qwen API密钥
        **kwargs: 其他可选参数

    Returns:
        str: JSON格式的处理结果字符串
    """
    import json

    try:
        # 调用处理函数
        result = process_excel_with_qwen(
            excel_path=excel_path, api_key=api_key, **kwargs
        )

        # 返回JSON字符串
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        error_result = {
            "success": False,
            "message": f"函数调用失败: {str(e)}",
            "data": None,
            "timestamp": datetime.now().isoformat(),
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


# 便捷函数 - 供影刀直接调用
def yingdao_excel_processor(excel_path: str, api_key: str) -> str:
    """
    影刀调用的便捷函数（使用默认参数）

    Args:
        excel_path: Excel文件路径
        api_key: Qwen API密钥

    Returns:
        str: JSON格式结果
    """
    return main(excel_path, api_key)


if __name__ == "__main__":
    # 测试代码
    print("影刀Excel处理器 - 测试模式")

    # 示例API密钥（需要替换为实际的）
    test_api_key = "YOUR_QWEN_API_KEY"

    # 示例Excel路径（需要替换为实际的）
    test_excel_path = "C:\\Users\\Admin\\Desktop\\test.xlsx"

    if test_api_key != "YOUR_QWEN_API_KEY" and os.path.exists(test_excel_path):
        result = yingdao_excel_processor(test_excel_path, test_api_key)
        print("测试结果:")
        print(result)
    else:
        print("请设置正确的API密钥和Excel文件路径进行测试")
