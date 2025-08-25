#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于关键帧和ASR数据生成结构化JSON
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

def parse_timestamp(timestamp_str: str) -> float:
    """将时间戳字符串转换为秒数"""
    try:
        if ':' in timestamp_str:
            parts = timestamp_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = parts
                return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        return float(timestamp_str)
    except:
        return 0.0

def extract_keyframe_info(keyframes_dir: Path) -> List[Dict[str, Any]]:
    """提取关键帧信息"""
    keyframes = []
    
    # 获取所有关键帧文件
    keyframe_files = sorted(
        keyframes_dir.glob("keyframe_*.jpg"),
        key=lambda x: int(x.stem.split('_')[-1])
    )
    
    for i, keyframe_file in enumerate(keyframe_files):
        # 从文件名提取时间戳
        filename = keyframe_file.name
        # 格式: keyframe_HH-MM-SS-mmm_NNNN.jpg
        pattern = r'keyframe_(\d{2})-(\d{2})-(\d{2})-(\d{3})_(\d+)\.jpg'
        match = re.match(pattern, filename)
        
        if match:
            hours, minutes, seconds, milliseconds, frame_num = match.groups()
            timestamp = f"{hours}:{minutes}:{seconds}.{milliseconds}"
            timestamp_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
            
            keyframes.append({
                "frame_number": int(frame_num),
                "timestamp": timestamp,
                "timestamp_seconds": timestamp_seconds,
                "filename": filename,
                "path": str(keyframe_file)
            })
    
    return keyframes

def load_asr_data(asr_file: Path) -> List[Dict[str, Any]]:
    """加载ASR数据"""
    try:
        with open(asr_file, 'r', encoding='utf-8') as f:
            asr_data = json.load(f)
        
        # 提取文本段落
        segments = []
        if isinstance(asr_data, dict) and 'segments' in asr_data:
            for segment in asr_data['segments']:
                segments.append({
                    "start": segment.get('start', 0),
                    "end": segment.get('end', 0),
                    "text": segment.get('text', '').strip()
                })
        elif isinstance(asr_data, list):
            segments = asr_data
        
        return segments
    except Exception as e:
        print(f"加载ASR数据失败: {e}")
        return []

def match_keyframes_with_asr(keyframes: List[Dict], asr_segments: List[Dict]) -> List[Dict[str, Any]]:
    """将关键帧与ASR文本匹配"""
    slides = []
    
    for keyframe in keyframes:
        timestamp_sec = keyframe['timestamp_seconds']
        
        # 查找对应的ASR文本
        matching_texts = []
        for segment in asr_segments:
            # 如果关键帧时间在ASR段落时间范围内，或者接近
            if (segment['start'] <= timestamp_sec <= segment['end']) or \
               (abs(segment['start'] - timestamp_sec) <= 5):  # 5秒容差
                matching_texts.append(segment['text'])
        
        # 创建幻灯片数据
        slide = {
            "slide_number": keyframe['frame_number'] + 1,
            "timestamp": keyframe['timestamp'],
            "timestamp_seconds": timestamp_sec,
            "keyframe": {
                "filename": keyframe['filename'],
                "path": keyframe['path']
            },
            "content": matching_texts,
            "title": "",  # 可以从文本中提取标题
            "speaker_text": " ".join(matching_texts) if matching_texts else ""
        }
        
        # 尝试提取标题（取第一句话作为标题）
        if matching_texts:
            first_text = matching_texts[0]
            sentences = re.split(r'[。！？.!?]', first_text)
            if sentences:
                slide["title"] = sentences[0].strip()[:50]  # 限制标题长度
        
        slides.append(slide)
    
    return slides

def generate_structured_json(video_name: str, keyframes_dir: Path, asr_file: Path, output_file: Path):
    """生成结构化JSON"""
    try:
        print(f"开始处理视频: {video_name}")
        
        # 1. 提取关键帧信息
        print("提取关键帧信息...")
        keyframes = extract_keyframe_info(keyframes_dir)
        print(f"找到 {len(keyframes)} 个关键帧")
        
        # 2. 加载ASR数据
        print("加载ASR数据...")
        asr_segments = load_asr_data(asr_file)
        print(f"找到 {len(asr_segments)} 个ASR段落")
        
        # 3. 匹配关键帧与ASR
        print("匹配关键帧与ASR文本...")
        slides = match_keyframes_with_asr(keyframes, asr_segments)
        
        # 4. 生成统计信息
        total_duration = keyframes[-1]['timestamp_seconds'] if keyframes else 0
        total_text_length = sum(len(slide['speaker_text']) for slide in slides)
        
        # 5. 构建最终JSON结构
        structured_data = {
            "metadata": {
                "video_name": video_name,
                "processed_at": datetime.now().isoformat(),
                "total_slides": len(slides),
                "total_keyframes": len(keyframes),
                "total_asr_segments": len(asr_segments),
                "duration_seconds": total_duration,
                "duration_formatted": f"{int(total_duration//60):02d}:{int(total_duration%60):02d}",
                "source_files": {
                    "keyframes_directory": str(keyframes_dir),
                    "asr_file": str(asr_file)
                }
            },
            "slides": slides,
            "summary": {
                "content_analysis": {
                    "total_text_length": total_text_length,
                    "average_text_per_slide": total_text_length / len(slides) if slides else 0,
                    "slides_with_text": len([s for s in slides if s['speaker_text']]),
                    "slides_without_text": len([s for s in slides if not s['speaker_text']])
                },
                "timeline": [
                    {
                        "slide_number": slide['slide_number'],
                        "timestamp": slide['timestamp'],
                        "title": slide['title'] or f"幻灯片 {slide['slide_number']}",
                        "has_text": bool(slide['speaker_text']),
                        "text_length": len(slide['speaker_text'])
                    }
                    for slide in slides
                ],
                "key_topics": list(set([
                    slide['title'] for slide in slides 
                    if slide['title'] and len(slide['title']) > 5
                ]))
            }
        }
        
        # 6. 保存JSON文件
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, ensure_ascii=False, indent=2)
        
        print(f"结构化JSON已保存: {output_file}")
        print(f"包含 {len(slides)} 个幻灯片，总时长 {total_duration:.1f} 秒")
        
        return structured_data
        
    except Exception as e:
        print(f"生成结构化JSON失败: {e}")
        return None

def main():
    """主函数"""
    # 配置路径
    video_name = "1.5__35858e88-211d-4a44-aa48-5ea04074b466"
    keyframes_dir = Path(f"keyframes/{video_name}")
    asr_file = keyframes_dir / f"{video_name}_asr.json"
    output_file = Path(f"mineru_output/{video_name}_structured.json")
    
    # 检查文件是否存在
    if not keyframes_dir.exists():
        print(f"关键帧目录不存在: {keyframes_dir}")
        return
    
    if not asr_file.exists():
        print(f"ASR文件不存在: {asr_file}")
        return
    
    # 生成结构化JSON
    result = generate_structured_json(video_name, keyframes_dir, asr_file, output_file)
    
    if result:
        print("\n✅ 结构化JSON生成成功！")
        print(f"📁 输出文件: {output_file}")
        print(f"📊 幻灯片数量: {result['metadata']['total_slides']}")
        print(f"⏱️  视频时长: {result['metadata']['duration_formatted']}")
    else:
        print("\n❌ 结构化JSON生成失败")

if __name__ == "__main__":
    main()