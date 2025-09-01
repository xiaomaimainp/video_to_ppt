# 课程视频转PPT工具

一个功能强大的课程视频处理工具，可以从视频中提取关键帧、进行语音识别，并生成课程大纲。

## 主要功能

### 1. 视频关键帧提取
- 支持多种视频格式：MP4, AVI, MOV, MKV, WMV, FLV
- 智能关键帧检测，基于帧间差异自动提取
- 可自定义提取参数：
  - 捕获间隔（秒）
  - 最大截图数量
  - 强制提取间隔
- 批量下载和管理关键帧

### 2. 语音识别（ASR）
- 基于Whisper模型的高精度语音识别
- 支持多种语言：中文、英文、日语、韩语、法语、德语、西班牙语、俄语
- 自动生成时间戳对齐的文本转录
- 输出JSON格式的识别结果

### 3. 智能课程大纲生成
- 基于语音转录内容自动生成结构化课程大纲
- 使用本地Ollama模型（qwen2.5:7b）进行内容分析
- 生成专业的Markdown格式大纲
- 包含课程介绍、章节划分、知识要点和总结

### 4. 数据管理
- 完整的数据导入/导出功能
- 支持清空特定目录（mineru_output）
- 历史视频管理和重新加载
- 批量操作支持

## 项目结构

```
video_to_ppt/
├── server.py                 # Flask Web服务器
├── extractor.py             # 视频关键帧提取器
├── asr_processor.py         # 语音识别处理器
├── deep_content_analyzer.py # 课程大纲生成器
├── templates/
│   └── index.html           # Web界面
├── uploads/                 # 上传的视频文件
├── keyframes/              # 提取的关键帧
├── mineru_output/          # MinerU输出目录
│   ├── pdfs/
│   └── results/
└── README.md
```

## 安装和使用

### 环境要求
- Python 3.8+
- FFmpeg
- Ollama（用于课程大纲生成）

### 安装依赖
```bash
pip install flask opencv-python whisper requests pathlib
```

### 启动服务
```bash
python server.py
```

服务将在 `http://localhost:9800` 启动

### 使用步骤

1. **上传视频**
   - 在Web界面中拖拽或选择视频文件
   - 调整提取参数（可选）
   - 点击"提取关键帧"

2. **语音识别**
   - 选择识别语言
   - 点击"提取语音文本"
   - 等待处理完成

3. **生成课程大纲**
   - 运行 `deep_content_analyzer.py`
   - 自动基于ASR结果生成课程大纲
   - 输出保存为 `course_outline.md`

## API接口

### 主要端点
- `POST /upload` - 上传视频文件
- `POST /extract` - 提取关键帧
- `POST /process_asr` - 语音识别处理
- `POST /clear_mineru_output` - 清空mineru_output目录
- `GET /export_data` - 导出所有数据
- `POST /import_data` - 导入数据

### 课程大纲生成
```bash
python deep_content_analyzer.py
```

## 配置说明

### Ollama配置
- 默认使用 `qwen2.5:7b` 模型
- 服务地址：`http://localhost:11434`
- 可在 `deep_content_analyzer.py` 中修改

### 视频处理参数
- **捕获间隔**：关键帧检测的时间间隔
- **最大截图数量**：限制提取的关键帧总数
- **强制提取间隔**：强制提取关键帧的时间间隔

## 输出格式

### 关键帧
- 格式：JPG
- 命名：`keyframe_HH-MM-SS-ms_序号.jpg`
- 包含时间戳信息

### 语音识别结果
- 格式：JSON
- 包含分段文本和时间戳
- 文件名：`视频名_asr.json`

### 课程大纲
- 格式：Markdown
- 包含完整的课程结构
- 文件名：`course_outline.md`

## 特色功能

### 智能关键帧提取
- 基于帧间差异算法
- 自动过滤相似帧
- 支持强制间隔提取

### 多语言语音识别
- 高精度Whisper模型
- 自动语言检测
- 时间戳对齐

### AI课程大纲生成
- 基于实际语音内容
- 结构化输出格式
- 专业教学大纲样式

### 数据管理
- 完整的导入导出
- 选择性数据清理
- 历史记录管理

## 注意事项

1. 确保Ollama服务正在运行（用于课程大纲生成）
2. 视频文件大小限制为500MB
3. 语音识别需要一定处理时间，请耐心等待
4. 建议定期备份重要数据

## 技术栈

- **后端**：Flask, OpenCV, Whisper, Requests
- **前端**：HTML5, CSS3, JavaScript
- **AI模型**：Ollama (qwen2.5:7b), Whisper
- **视频处理**：FFmpeg, OpenCV
- **数据格式**：JSON, Markdown

## 更新日志

### 最新版本
- ✅ 添加课程大纲自动生成功能
- ✅ 优化关键帧提取算法
- ✅ 增强数据管理功能
- ✅ 支持mineru_output目录清理
- ✅ 改进Web界面用户体验

---

如有问题或建议，请提交Issue或联系开发者。