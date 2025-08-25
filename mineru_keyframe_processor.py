#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键帧图片转PDF并使用MinerU进行内容提取处理器
"""

import os
import sys
import json
import re
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# 图像处理
from PIL import Image
import cv2
import numpy as np

# PDF处理
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mineru_processor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MinerUKeyframeProcessor:
    """使用MinerU处理关键帧图片的处理器"""
    
    def __init__(self, keyframes_dir: str = "keyframes", output_dir: str = "mineru_output"):
        """
        初始化处理器
        
        Args:
            keyframes_dir: 关键帧图片目录
            output_dir: 输出目录
        """
        self.keyframes_dir = Path(keyframes_dir)
        self.output_dir = Path(output_dir)
        self.pdf_dir = self.output_dir / "pdfs"
        self.results_dir = self.output_dir / "results"
        
        # 创建输出目录
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"初始化MinerU关键帧处理器")
        logger.info(f"关键帧目录: {self.keyframes_dir}")
        logger.info(f"输出目录: {self.output_dir}")
    
    def extract_timestamp_from_filename(self, filename: str) -> Optional[str]:
        """
        从文件名中提取时间戳
        
        Args:
            filename: 文件名，格式如 keyframe_00-01-23-456_0001.jpg
            
        Returns:
            时间戳字符串，如 "00:01:23.456"
        """
        # 匹配格式: keyframe_HH-MM-SS-mmm_NNNN.jpg
        pattern = r'keyframe_(\d{2})-(\d{2})-(\d{2})-(\d{3})_\d+\.jpg'
        match = re.match(pattern, filename)
        
        if match:
            hours, minutes, seconds, milliseconds = match.groups()
            return f"{hours}:{minutes}:{seconds}.{milliseconds}"
        
        return None
    
    def get_video_folders(self) -> List[Path]:
        """获取所有视频文件夹"""
        video_folders = []
        
        if not self.keyframes_dir.exists():
            logger.error(f"关键帧目录不存在: {self.keyframes_dir}")
            return video_folders
        
        for item in self.keyframes_dir.iterdir():
            if item.is_dir():
                # 检查是否包含关键帧图片
                jpg_files = list(item.glob("keyframe_*.jpg"))
                if jpg_files:
                    video_folders.append(item)
                    logger.info(f"发现视频文件夹: {item.name}, 包含 {len(jpg_files)} 个关键帧")
        
        return video_folders
    
    def create_pdf_from_images(self, image_folder: Path, output_pdf_path: Path) -> bool:
        """
        将图片文件夹中的关键帧转换为PDF
        
        Args:
            image_folder: 图片文件夹路径
            output_pdf_path: 输出PDF路径
            
        Returns:
            是否成功创建PDF
        """
        try:
            # 获取所有关键帧图片并按序号排序
            image_files = sorted(
                image_folder.glob("keyframe_*.jpg"),
                key=lambda x: int(x.stem.split('_')[-1])
            )
            
            if not image_files:
                logger.warning(f"文件夹 {image_folder} 中没有找到关键帧图片")
                return False
            
            logger.info(f"开始创建PDF: {output_pdf_path}")
            logger.info(f"处理 {len(image_files)} 个关键帧图片")
            
            # 创建PDF
            c = canvas.Canvas(str(output_pdf_path), pagesize=A4)
            page_width, page_height = A4
            
            for i, image_file in enumerate(image_files):
                try:
                    # 提取时间戳
                    timestamp = self.extract_timestamp_from_filename(image_file.name)
                    
                    # 打开图片
                    with Image.open(image_file) as img:
                        # 转换为RGB模式
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # 计算缩放比例以适应页面
                        img_width, img_height = img.size
                        scale_x = (page_width - 2 * inch) / img_width
                        scale_y = (page_height - 3 * inch) / img_height
                        scale = min(scale_x, scale_y)
                        
                        new_width = img_width * scale
                        new_height = img_height * scale
                        
                        # 居中位置
                        x = (page_width - new_width) / 2
                        y = (page_height - new_height) / 2
                        
                        # 添加图片到PDF
                        c.drawImage(ImageReader(img), x, y, new_width, new_height)
                        
                        # 添加时间戳标注
                        if timestamp:
                            c.setFont("Helvetica", 12)
                            c.drawString(50, page_height - 50, f"时间戳: {timestamp}")
                        
                        # 添加页码
                        c.setFont("Helvetica", 10)
                        c.drawString(50, 30, f"第 {i+1} 页 / 共 {len(image_files)} 页")
                        c.drawString(50, 15, f"文件: {image_file.name}")
                        
                        # 新建页面（除了最后一页）
                        if i < len(image_files) - 1:
                            c.showPage()
                
                except Exception as e:
                    logger.error(f"处理图片 {image_file} 时出错: {e}")
                    continue
            
            # 保存PDF
            c.save()
            logger.info(f"PDF创建成功: {output_pdf_path}")
            return True
            
        except Exception as e:
            logger.error(f"创建PDF时出错: {e}")
            return False
    
    def process_pdf_with_mineru(self, pdf_path: Path, video_name: str) -> Dict[str, Any]:
        """
        使用MinerU命令行工具处理PDF文件，只保留关键结果
        
        Args:
            pdf_path: PDF文件路径
            video_name: 视频名称
            
        Returns:
            处理结果字典
        """
        try:
            logger.info(f"开始使用MinerU处理PDF: {pdf_path}")
            
            # 创建临时输出目录
            temp_output_dir = self.results_dir / f"{video_name}_temp"
            temp_output_dir.mkdir(parents=True, exist_ok=True)
            
            # 构建magic-pdf命令
            cmd = [
                "magic-pdf",
                "-p", str(pdf_path),
                "-o", str(temp_output_dir),
                "-m", "auto"
            ]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                logger.info(f"MinerU处理成功: {video_name}")
                
                # 查找并提取关键内容
                key_content = self.extract_key_content_only(video_name)
                
                # 清理临时文件，只保留关键JSON
                self.cleanup_redundant_files(temp_output_dir, video_name)
                
                return {
                    "video_name": video_name,
                    "pdf_path": str(pdf_path),
                    "status": "success",
                    "key_content": key_content,
                    "processing_time": datetime.now().isoformat()
                }
            else:
                logger.error(f"MinerU处理失败: {result.stderr}")
                return {
                    "video_name": video_name,
                    "pdf_path": str(pdf_path),
                    "status": "error",
                    "error": result.stderr,
                    "processing_time": datetime.now().isoformat()
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"MinerU处理超时: {video_name}")
            return {
                "video_name": video_name,
                "pdf_path": str(pdf_path),
                "status": "error",
                "error": "处理超时",
                "processing_time": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"MinerU处理PDF时出错: {e}")
            return {
                "video_name": video_name,
                "pdf_path": str(pdf_path),
                "error": str(e),
                "status": "error",
                "processing_time": datetime.now().isoformat()
            }
    
    def find_generated_files(self, output_dir: Path) -> Dict[str, str]:
        """
        查找MinerU生成的文件
        
        Args:
            output_dir: 输出目录
            
        Returns:
            生成的文件路径字典
        """
        generated_files = {}
        
        try:
            # 递归查找所有文件
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    file_ext = file_path.suffix.lower()
                    file_name = file_path.name
                    
                    # 分类文件
                    if file_ext == ".md":
                        generated_files["markdown"] = str(file_path)
                    elif file_ext == ".json":
                        if "content" in file_name.lower():
                            generated_files["content_json"] = str(file_path)
                        elif "middle" in file_name.lower():
                            generated_files["middle_json"] = str(file_path)
                        else:
                            generated_files["other_json"] = str(file_path)
                    elif file_ext in [".png", ".jpg", ".jpeg"]:
                        if "images" not in generated_files:
                            generated_files["images"] = []
                        generated_files["images"].append(str(file_path))
                    elif file_ext == ".pdf":
                        if "layout" in file_name.lower():
                            generated_files["layout_pdf"] = str(file_path)
                        elif "span" in file_name.lower():
                            generated_files["spans_pdf"] = str(file_path)
            
            logger.info(f"找到生成的文件: {list(generated_files.keys())}")
            
        except Exception as e:
            logger.error(f"查找生成文件时出错: {e}")
        
        return generated_files
    
    def read_generated_content(self, generated_files: Dict[str, str]) -> Dict[str, Any]:
        """
        读取生成的内容文件
        
        Args:
            generated_files: 生成的文件路径字典
            
        Returns:
            内容数据字典
        """
        content_data = {}
        
        try:
            # 读取Markdown文件
            if "markdown" in generated_files:
                try:
                    with open(generated_files["markdown"], 'r', encoding='utf-8') as f:
                        content_data["markdown_content"] = f.read()
                except Exception as e:
                    logger.error(f"读取Markdown文件出错: {e}")
            
            # 读取JSON文件
            for json_key in ["content_json", "middle_json", "other_json"]:
                if json_key in generated_files:
                    try:
                        with open(generated_files[json_key], 'r', encoding='utf-8') as f:
                            content_data[json_key] = json.load(f)
                    except Exception as e:
                        logger.error(f"读取{json_key}文件出错: {e}")
            
            # 统计图片数量
            if "images" in generated_files:
                content_data["image_count"] = len(generated_files["images"])
            
        except Exception as e:
            logger.error(f"读取生成内容时出错: {e}")
        
        return content_data
    
    def extract_key_information(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        从MinerU结果中提取关键信息
        
        Args:
            result: MinerU处理结果
            
        Returns:
            提取的关键信息
        """
        try:
            if result.get("status") != "success":
                return {"error": "处理失败", "details": result.get("error", "未知错误")}
            
            content_data = result.get("content_data", {})
            
            # 分析Markdown内容
            md_content = content_data.get("markdown_content", "")
            
            # 提取文本内容
            text_blocks = []
            if md_content:
                # 简单的文本块提取
                lines = md_content.split('\n')
                current_block = []
                
                for line in lines:
                    line = line.strip()
                    if line:
                        current_block.append(line)
                    else:
                        if current_block:
                            text_blocks.append('\n'.join(current_block))
                            current_block = []
                
                if current_block:
                    text_blocks.append('\n'.join(current_block))
            
            # 统计信息
            stats = {
                "total_text_blocks": len(text_blocks),
                "markdown_length": len(md_content),
                "has_images": "images" in md_content.lower() or content_data.get("image_count", 0) > 0,
                "has_tables": "table" in md_content.lower() or "|" in md_content,
                "has_formulas": "$" in md_content or "formula" in md_content.lower(),
                "image_count": content_data.get("image_count", 0)
            }
            
            return {
                "video_name": result.get("video_name"),
                "text_blocks": text_blocks,
                "markdown_content": md_content,
                "statistics": stats,
                "generated_files": result.get("generated_files", {}),
                "extraction_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"提取关键信息时出错: {e}")
            return {"error": f"提取失败: {e}"}
    
    def process_all_videos(self) -> List[Dict[str, Any]]:
        """
        处理所有视频文件夹
        
        Returns:
            所有处理结果的列表
        """
        video_folders = self.get_video_folders()
        
        if not video_folders:
            logger.warning("没有找到包含关键帧的视频文件夹")
            return []
        
        all_results = []
        
        for video_folder in video_folders:
            video_name = video_folder.name
            logger.info(f"开始处理视频: {video_name}")
            
            try:
                # 1. 创建PDF
                pdf_path = self.pdf_dir / f"{video_name}.pdf"
                if self.create_pdf_from_images(video_folder, pdf_path):
                    
                    # 2. 使用MinerU处理PDF
                    mineru_result = self.process_pdf_with_mineru(pdf_path, video_name)
                    
                    # 3. 提取关键信息
                    key_info = self.extract_key_information(mineru_result)
                    
                    # 4. 合并结果
                    final_result = {
                        **mineru_result,
                        "key_information": key_info,
                        "pdf_created": True
                    }
                    
                else:
                    final_result = {
                        "video_name": video_name,
                        "error": "PDF创建失败",
                        "status": "error",
                        "pdf_created": False
                    }
                
                all_results.append(final_result)
                
                # 保存单个结果
                result_file = self.results_dir / video_name / f"{video_name}_processing_result.json"
                result_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(final_result, f, ensure_ascii=False, indent=2)
                
                logger.info(f"视频 {video_name} 处理完成")
                
            except Exception as e:
                logger.error(f"处理视频 {video_name} 时出错: {e}")
                error_result = {
                    "video_name": video_name,
                    "error": str(e),
                    "status": "error",
                    "processing_time": datetime.now().isoformat()
                }
                all_results.append(error_result)
        
        # 保存总结果
        summary_file = self.output_dir / "processing_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                "total_videos": len(video_folders),
                "processed_videos": len(all_results),
                "successful_videos": len([r for r in all_results if r.get("status") == "success"]),
                "failed_videos": len([r for r in all_results if r.get("status") == "error"]),
                "processing_time": datetime.now().isoformat(),
                "results": all_results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"所有视频处理完成，共处理 {len(all_results)} 个视频")
        return all_results

    def cleanup_redundant_files(self, result_dir: Path, session_id: str) -> None:
        """清理冗余文件，只保留关键的JSON文件和图片"""
        try:
            # 查找并删除冗余文件
            redundant_patterns = [
                "*_origin.pdf",
                "*_layout.pdf", 
                "*_spans.pdf",
                "*_middle.json",
                "*_model.json",
                "*_content_list.json"
            ]
            
            for pattern in redundant_patterns:
                for file_path in result_dir.rglob(pattern):
                    try:
                        file_path.unlink()
                        logger.info(f"已删除冗余文件: {file_path}")
                    except Exception as e:
                        logger.warning(f"删除文件失败 {file_path}: {e}")
            
            # 删除空目录
            for dir_path in result_dir.rglob("*"):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    try:
                        dir_path.rmdir()
                        self.logger.info(f"已删除空目录: {dir_path}")
                        logger.info(f"已删除空目录: {dir_path}")
                    except Exception as e:
                        logger.warning(f"删除空目录失败 {dir_path}: {e}")
                        
        except Exception as e:
            logger.error(f"清理冗余文件时出错: {e}")

    def extract_key_content_only(self, session_id: str) -> Dict[str, Any]:
        """只提取关键内容，不生成冗余文件"""
        try:
            # 检查PDF是否已存在
            pdf_path = self.output_dir / "pdfs" / f"{session_id}.pdf"
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
            # 检查MinerU结果是否已存在
            temp_output_dir = self.output_dir / "results" / f"{session_id}_temp"
            result_dir = temp_output_dir / session_id / "auto"
            
            if not result_dir.exists():
                raise FileNotFoundError(f"MinerU处理结果不存在: {result_dir}")
            
            # 创建最终输出目录
            final_output_dir = self.output_dir / "results" / session_id
            final_output_dir.mkdir(parents=True, exist_ok=True)
            
            # 提取关键内容
            md_file = result_dir / f"{session_id}.md"
            images_dir = result_dir / "images"
            
            if not md_file.exists():
                raise FileNotFoundError(f"Markdown文件不存在: {md_file}")
            
            # 读取并处理Markdown内容
            content = md_file.read_text(encoding='utf-8')
            
            # 统计信息
            line_count = len(content.split('\n'))
            image_count = len(list(images_dir.glob('*.jpg'))) if images_dir.exists() else 0
            
            # 生成结构化JSON
            structured_json = self.parse_markdown_to_json(content, str(md_file), str(images_dir))
            
            # 保存结构化JSON
            json_output_file = final_output_dir / f"{session_id}_structured.json"
            with open(json_output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_json, f, ensure_ascii=False, indent=2)
            
            # 保存处理结果
            result = {
                "session_id": session_id,
                "status": "success",
                "content_file": str(md_file),
                "images_dir": str(images_dir) if images_dir.exists() else None,
                "structured_json_file": str(json_output_file),
                "line_count": line_count,
                "image_count": image_count,
                "processed_at": datetime.now().isoformat()
            }
            
            # 保存结果到JSON文件
            result_file = final_output_dir / f"{session_id}_processing_result.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"内容提取完成: {line_count}行文档, {image_count}张图片")
            logger.info(f"结构化JSON已保存: {json_output_file}")
            
            return result
            
        except Exception as e:
            logger.error(f"提取关键内容时出错: {e}")
            raise

    def parse_markdown_to_json(self, content: str, md_file_path: str, images_dir: str) -> Dict[str, Any]:
        """
        将Markdown内容解析为结构化JSON
        
        Args:
            content: Markdown内容
            md_file_path: Markdown文件路径
            images_dir: 图片目录路径
            
        Returns:
            结构化的JSON数据
        """
        try:
            slides = []
            current_slide = None
            
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 检测时间戳
                timestamp_match = re.match(r':(\d{2}):(\d{2}):(\d{2})\.(\d{3})', line)
                if timestamp_match:
                    # 保存上一个幻灯片
                    if current_slide:
                        slides.append(current_slide)
                    
                    # 创建新幻灯片
                    hours, minutes, seconds, milliseconds = timestamp_match.groups()
                    timestamp = f"{hours}:{minutes}:{seconds}.{milliseconds}"
                    
                    current_slide = {
                        "timestamp": timestamp,
                        "timestamp_seconds": int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000,
                        "title": "",
                        "content": [],
                        "images": [],
                        "formulas": []
                    }
                    continue
                
                # 检测标题
                if line.startswith('# ') and current_slide:
                    current_slide["title"] = line[2:].strip()
                    continue
                
                # 检测图片
                image_match = re.match(r'!\[\]\(images/([^)]+)\)', line)
                if image_match and current_slide:
                    image_filename = image_match.group(1)
                    current_slide["images"].append({
                        "filename": image_filename,
                        "path": f"images/{image_filename}",
                        "full_path": f"{images_dir}/{image_filename}" if images_dir else f"images/{image_filename}"
                    })
                    continue
                
                # 检测数学公式
                if line.startswith('$$') and current_slide:
                    formula_lines = [line[2:]]  # 去掉开头的$$
                    continue
                elif line.endswith('$$') and current_slide:
                    formula_lines.append(line[:-2])  # 去掉结尾的$$
                    formula = '\n'.join(formula_lines).strip()
                    if formula:
                        current_slide["formulas"].append(formula)
                    continue
                
                # 普通文本内容
                if line and current_slide and not line.startswith(':'):
                    current_slide["content"].append(line)
            
            # 添加最后一个幻灯片
            if current_slide:
                slides.append(current_slide)
            
            # 生成统计信息
            total_slides = len(slides)
            total_images = sum(len(slide["images"]) for slide in slides)
            total_formulas = sum(len(slide["formulas"]) for slide in slides)
            
            # 提取主要主题
            titles = [slide["title"] for slide in slides if slide["title"]]
            main_topic = titles[0] if titles else "未知主题"
            
            return {
                "metadata": {
                    "source_file": md_file_path,
                    "images_directory": images_dir,
                    "processed_at": datetime.now().isoformat(),
                    "total_slides": total_slides,
                    "total_images": total_images,
                    "total_formulas": total_formulas,
                    "main_topic": main_topic,
                    "duration_seconds": slides[-1]["timestamp_seconds"] if slides else 0
                },
                "slides": slides,
                "summary": {
                    "key_topics": list(set(titles)),
                    "image_distribution": {
                        f"slide_{i+1}": len(slide["images"]) 
                        for i, slide in enumerate(slides)
                    },
                    "content_types": {
                        "has_formulas": total_formulas > 0,
                        "has_images": total_images > 0,
                        "has_text": any(slide["content"] for slide in slides)
                    },
                    "timeline": [
                        {
                            "slide_number": i + 1,
                            "timestamp": slide["timestamp"],
                            "title": slide["title"] or f"幻灯片 {i + 1}",
                            "image_count": len(slide["images"]),
                            "content_length": len(' '.join(slide["content"]))
                        }
                        for i, slide in enumerate(slides)
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"解析Markdown为JSON时出错: {e}")
            return {
                "error": f"解析失败: {e}",
                "source_file": md_file_path,
                "processed_at": datetime.now().isoformat()
            }


def main():
    """主函数"""
    processor = MinerUKeyframeProcessor()
    
    try:
        results = processor.process_all_videos()
        
        print(f"\n处理完成！")
        print(f"共处理 {len(results)} 个视频")
        
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "error"]
        
        print(f"成功: {len(successful)} 个")
        print(f"失败: {len(failed)} 个")
        
        if successful:
            print(f"\n成功处理的视频:")
            for result in successful:
                print(f"  - {result['video_name']}")
        
        if failed:
            print(f"\n处理失败的视频:")
            for result in failed:
                print(f"  - {result['video_name']}: {result.get('error', '未知错误')}")
        
        print(f"\n结果保存在: {processor.output_dir}")
        
    except Exception as e:
        logger.error(f"主程序执行出错: {e}")
        print(f"程序执行失败: {e}")


if __name__ == "__main__":
    main()