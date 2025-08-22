# 视频关键帧提取器

这是一个高效的视频关键帧提取工具，可以自动从视频中提取关键帧（场景变化明显的帧），适用于视频摘要、幻灯片生成等场景。

## 特点

- **自适应阈值算法**：根据视频内容动态调整差异阈值
- **高效处理**：针对不同长度和格式的视频优化采样策略
- **进度反馈**：支持实时进度回调
- **易于使用**：简单的API和命令行界面
- **高质量输出**：保存为高质量JPEG图像

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

### 命令行使用

```bash
python -m video_keyframe_extractor.cli 你的视频.mp4 --output-dir 输出目录 --interval 1.5 --max-frames 50 --debug
```

参数说明:
- `--output-dir`, `-o`: 输出目录 (默认: keyframes)
- `--interval`, `-i`: 捕获间隔(秒) (默认: 1.0)
- `--max-frames`, `-m`: 最大截图数量 (默认: 50)
- `--debug`, `-d`: 启用调试输出

### 代码中使用

```python
from video_keyframe_extractor import VideoKeyframeExtractor

# 创建提取器
extractor = VideoKeyframeExtractor(debug_enabled=True)

# 提取关键帧
keyframes = extractor.extract_keyframes(
    video_path="你的视频.mp4",
    output_dir="输出目录",
    capture_interval=1.5,  # 每1.5秒检查一次
    max_screenshots=50     # 最多50张截图
)

print(f"提取了 {len(keyframes)} 个关键帧")
```

### 带进度回调的示例

```python
from video_keyframe_extractor import VideoKeyframeExtractor

# 创建提取器
extractor = VideoKeyframeExtractor(debug_enabled=False)

# 进度回调函数
def show_progress(progress: float):
    print(f"进度: {progress:.1f}%")

# 提取关键帧
keyframes = extractor.extract_keyframes(
    video_path="你的视频.mp4",
    output_dir="输出目录",
    capture_interval=2.0,
    max_screenshots=30,
    progress_callback=show_progress
)
```

## 更多示例

查看 `examples.py` 文件获取更多使用示例，包括:
- 简单使用示例
- 高级使用示例（带进度回调）
- 批量处理示例

## 工作原理

1. **预处理阶段**：分析视频内容，计算最佳差异阈值
2. **提取阶段**：按指定间隔采样帧，计算相邻帧差异，保存超过阈值的帧
3. **后处理**：生成高质量JPEG图像

## 许可证

MIT