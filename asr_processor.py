#!/usr/bin/env python3
"""
视频语音识别处理器
使用Whisper模型进行语音识别，并输出带时间戳的文本
"""

import os
import json
import torch
import whisper
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import re
import nltk
from nltk.tokenize import sent_tokenize

# 尝试下载NLTK数据，如果尚未下载
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class ASRProcessor:
    """语音识别处理器"""
    
    def __init__(self, model_name: str = "base", device: str = None):
        """
        初始化语音识别处理器
        
        Args:
            model_name: Whisper模型名称 (tiny, base, small, medium, large)
            device: 设备 (cuda, cpu)，如果为None则自动选择
        """
        # 如果没有指定设备，则自动选择
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.device = device
        self.model_name = model_name
        print(f"正在加载Whisper模型 '{model_name}' 到 {device} 设备...")
        self.model = whisper.load_model(model_name, device=device)
        print(f"Whisper模型加载完成")
    
    def process_video(self, video_path: str, language: str = "zh", output_dir: str = None) -> Dict[str, Any]:
        """
        处理视频文件，提取语音并进行识别
        
        Args:
            video_path: 视频文件路径
            language: 语言代码 (zh: 中文, en: 英文, etc.)
            output_dir: 输出目录，如果为None则使用视频所在目录
            
        Returns:
            Dict: 包含识别结果的字典
        """
        print(f"开始处理视频: {video_path}")
        
        # 设置输出目录
        if output_dir is None:
            output_dir = os.path.dirname(video_path)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用Whisper进行语音识别
        print("开始语音识别...")
        result = self.model.transcribe(
            video_path, 
            language=language,
            verbose=True,
            word_timestamps=True  # 启用单词级时间戳
        )
        
        # 处理识别结果，添加分句
        processed_result = self.process_transcription(result)
        
        # 生成输出文件名
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_asr.json")
        
        # 保存结果到JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_result, f, ensure_ascii=False, indent=2)
        
        print(f"语音识别完成，结果已保存到: {output_path}")
        
        return {
            "success": True,
            "message": "语音识别完成",
            "output_path": output_path,
            "result": processed_result
        }
    
    def process_transcription(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理转录结果，添加分句和时间戳
        
        Args:
            result: Whisper转录结果
            
        Returns:
            Dict: 处理后的结果
        """
        # 提取原始文本和段落
        full_text = result.get("text", "")
        segments = result.get("segments", [])
        
        # 创建处理后的结果
        processed_result = {
            "full_text": full_text,
            "segments": segments,
            "sentences": []
        }
        
        # 如果没有段落，直接返回
        if not segments:
            return processed_result
        
        # 合并相邻的段落，形成更完整的句子
        merged_segments = self.merge_segments(segments)
        
        # 对每个合并后的段落进行分句
        all_sentences = []
        
        for segment in merged_segments:
            text = segment["text"].strip()
            start = segment["start"]
            end = segment["end"]
            
            # 使用NLTK进行分句
            sentences = sent_tokenize(text)
            
            # 如果只有一个句子，直接使用段落的时间戳
            if len(sentences) == 1:
                all_sentences.append({
                    "text": sentences[0],
                    "start": start,
                    "end": end
                })
            else:
                # 如果有多个句子，估计每个句子的时间戳
                total_chars = sum(len(s) for s in sentences)
                current_pos = 0
                
                for sentence in sentences:
                    sentence_len = len(sentence)
                    sentence_ratio = sentence_len / total_chars if total_chars > 0 else 0
                    sentence_duration = (end - start) * sentence_ratio
                    
                    sentence_start = start + (end - start) * (current_pos / total_chars) if total_chars > 0 else start
                    sentence_end = sentence_start + sentence_duration
                    
                    all_sentences.append({
                        "text": sentence,
                        "start": round(sentence_start, 2),
                        "end": round(sentence_end, 2)
                    })
                    
                    current_pos += sentence_len
        
        # 添加句子到结果中
        processed_result["sentences"] = all_sentences
        
        return processed_result
    
    def merge_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并相邻的段落，形成更完整的句子
        
        Args:
            segments: 段落列表
            
        Returns:
            List[Dict]: 合并后的段落列表
        """
        if not segments:
            return []
        
        merged = []
        current = segments[0].copy()
        
        for i in range(1, len(segments)):
            next_segment = segments[i]
            
            # 如果当前段落以标点符号结束，或者下一个段落以大写字母开头，则认为是新句子
            current_text = current["text"].strip()
            next_text = next_segment["text"].strip()
            
            if (current_text.endswith(('.', '!', '?', '。', '！', '？')) or 
                (next_text and next_text[0].isupper())):
                merged.append(current)
                current = next_segment.copy()
            else:
                # 合并段落
                current["text"] += " " + next_text
                current["end"] = next_segment["end"]
                if "words" in current and "words" in next_segment:
                    current["words"].extend(next_segment["words"])
        
        # 添加最后一个段落
        merged.append(current)
        
        return merged
    
    def format_timestamp(self, seconds: float) -> str:
        """
        将秒数格式化为 HH:MM:SS.ms 格式
        
        Args:
            seconds: 秒数
            
        Returns:
            str: 格式化后的时间字符串
        """
        ms = int((seconds % 1) * 1000)
        s = int(seconds)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"