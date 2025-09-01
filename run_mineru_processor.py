#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行MinerU关键帧处理器的脚本
"""

import sys
import os
from pathlib import Path
import subprocess

def activate_conda_and_run():
    """检查并激活conda环境，然后重新运行脚本"""
    # 检查是否在mineru1.3.2环境中
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', '')
    if conda_env != 'mineru1.3.2':
        # 尝试激活conda环境并重新运行
        try:
            # 获取conda初始化命令
            conda_init = subprocess.check_output(['conda', 'shell.bash', 'hook'], 
                                               stderr=subprocess.DEVNULL, 
                                               universal_newlines=True)
            
            # 构造完整的命令来激活环境并运行脚本
            cmd = f"""
            {conda_init}
            conda activate mineru1.3.2
            python {" ".join(sys.argv)}
            """
            
            # 在bash中执行命令
            result = subprocess.run(['bash', '-c', cmd], 
                                  cwd=os.path.dirname(os.path.abspath(__file__)))
            return result.returncode
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("警告: 无法自动激活conda环境'mineru1.3.2'")
            print("请手动激活环境后运行: conda activate mineru1.3.2 && python run_mineru_processor.py")
            return 1
    else:
        # 已在正确的环境中，继续执行主逻辑
        return None

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
    # 检查是否需要激活conda环境
    result = activate_conda_and_run()
    if result is not None:
        sys.exit(result)
    
    # 如果不需要重新运行或已在正确环境中，则执行主函数
    main()