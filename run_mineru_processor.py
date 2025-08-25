#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行MinerU关键帧处理器的脚本
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from mineru_keyframe_processor import MinerUKeyframeProcessor

def main():
    """主函数"""
    print("=" * 60)
    print("MinerU关键帧处理器")
    print("=" * 60)
    
    # 检查关键帧目录
    keyframes_dir = current_dir / "keyframes"
    if not keyframes_dir.exists():
        print(f"错误: 关键帧目录不存在: {keyframes_dir}")
        return
    
    # 创建处理器
    processor = MinerUKeyframeProcessor(
        keyframes_dir=str(keyframes_dir),
        output_dir="mineru_output"
    )
    
    try:
        print("开始处理关键帧...")
        results = processor.process_all_videos()
        
        print(f"\n处理完成！")
        print(f"共处理 {len(results)} 个视频")
        
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "error"]
        
        print(f"成功: {len(successful)} 个")
        print(f"失败: {len(failed)} 个")
        
        if successful:
            print(f"\n✅ 成功处理的视频:")
            for result in successful:
                video_name = result['video_name']
                print(f"  - {video_name}")
                
                # 显示提取的关键信息
                key_info = result.get('key_information', {})
                if key_info and not key_info.get('error'):
                    stats = key_info.get('statistics', {})
                    print(f"    📊 统计: {stats.get('total_text_blocks', 0)} 个文本块, "
                          f"Markdown长度: {stats.get('markdown_length', 0)}")
                    
                    if stats.get('has_images'):
                        print(f"    🖼️  包含图像")
                    if stats.get('has_tables'):
                        print(f"    📋 包含表格")
                    if stats.get('has_formulas'):
                        print(f"    🧮 包含公式")
        
        if failed:
            print(f"\n❌ 处理失败的视频:")
            for result in failed:
                print(f"  - {result['video_name']}: {result.get('error', '未知错误')}")
        
        print(f"\n📁 结果保存在: {processor.output_dir}")
        print(f"📄 详细日志: mineru_processor.log")
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()