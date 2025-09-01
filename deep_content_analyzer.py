#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import requests
from pathlib import Path
from typing import Dict, List, Any

class CleanCourseGenerator:
    """清洁的课程大纲生成器 - 只生成你需要的格式"""
    
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url
        self.project_dir = Path("/home/huangshiang/video_to_ppt")
        self.use_ollama = False
        
    def check_ollama_status(self) -> bool:
        """检查ollama服务状态"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get('models', [])
                if models:
                    print(f"✓ ollama可用，模型数量: {len(models)}")
                    self.use_ollama = True
                    return True
        except:
            pass
        print("✗ ollama不可用")
        return False
    
    def load_asr_content(self) -> str:
        """加载ASR语音识别内容"""
        asr_file = self.project_dir / "keyframes" / "4.2.1---I_a9ee63e6-47e4-4aa2-b982-36d672defb6f" / "4.2.1---I_a9ee63e6-47e4-4aa2-b982-36d672defb6f_asr.json"
        
        try:
            with open(asr_file, 'r', encoding='utf-8') as f:
                asr_data = json.load(f)
            
            if isinstance(asr_data, list):
                # 直接处理segments列表
                segments = asr_data
            elif 'segments' in asr_data:
                segments = asr_data['segments']
            else:
                return ""
            
            # 提取所有文本内容
            full_text = []
            for segment in segments:
                if isinstance(segment, dict) and 'text' in segment:
                    full_text.append(segment['text'].strip())
            
            transcript = ' '.join(full_text)
            print(f"✓ ASR内容加载完成: {len(segments)}个片段, {len(transcript)}字符")
            return transcript
            
        except Exception as e:
            print(f"✗ ASR内容加载失败: {e}")
            return ""
    
    def generate_course_outline(self, asr_content: str) -> str:
        """使用ollama生成课程大纲"""
        if not self.use_ollama or not asr_content:
            return ""
        
        # 构建清洁的提示词
        prompt = f"""基于以下实际课程内容，请生成结构化的课程大纲：

实际语音转录内容：
{asr_content[:1200]}

请严格按照以下格式生成课程大纲：

# [课程主题] - [副标题]

## 课程介绍
- 主讲人：[从内容中识别]
- 课程性质：[根据内容判断]
- 学习目标：[基于实际内容提取3-4个目标]

## 第一章：[章节标题]
- [具体知识点]
- [具体知识点]
- [具体知识点]

## 第二章：[章节标题]
- [具体知识点]
- [具体知识点]
- [具体知识点]

## 第三章：[章节标题]
- [具体知识点]
- [具体知识点]
- [具体知识点]

## 第四章：[章节标题]
- [具体知识点]
- [具体知识点]
- [具体知识点]

## 总结与展望
- [总结要点]
- [总结要点]
- [总结要点]

要求：
1. 严格遵循上述markdown格式
2. 基于实际的语音转录内容生成章节
3. 每个要点要具体实用，不要空泛，直接写要点内容，不要"[要点]："这样的标记
4. 章节标题要反映实际教学内容
5. 每章的要点数量可以根据内容需要灵活调整（3-6个）
6. 用中文回答，保持专业性
7. 只输出课程大纲，不要其他内容
8. 要点格式示例：- 可微与可导的关系（直接写具体内容，不要标记符号）"""
        
        try:
            print("正在使用AI生成课程大纲...")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json().get('response', '')
                print(f"✓ AI课程大纲生成完成，长度: {len(result)}字符")
                return result
            else:
                print(f"✗ API错误: {response.status_code}")
                return ""
        except Exception as e:
            print(f"✗ 调用ollama失败: {e}")
            return ""
    
    def run(self):
        """运行生成器"""
        print("=== 清洁课程大纲生成器 ===")
        
        # 检查ollama
        if not self.check_ollama_status():
            return
        
        # 加载ASR内容
        print("正在加载ASR内容...")
        asr_content = self.load_asr_content()
        
        if not asr_content:
            print("✗ 无法加载ASR内容")
            return
        
        # 生成课程大纲
        course_outline = self.generate_course_outline(asr_content)
        
        if course_outline:
            # 只保存课程大纲
            with open('course_outline.md', 'w', encoding='utf-8') as f:
                f.write(course_outline)
            print("✓ 课程大纲已保存到: course_outline.md")
            
            # 显示生成的内容
            print("\n" + "="*50)
            print("生成的课程大纲:")
            print("="*50)
            print(course_outline)
        else:
            print("✗ 课程大纲生成失败")

def main():
    generator = CleanCourseGenerator()
    generator.run()

if __name__ == "__main__":
    main()