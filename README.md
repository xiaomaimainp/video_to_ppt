# 视频转PPT

## 功能步骤
1. ✅ 视频关键帧提取  
2. ✅ 视频ASR语音识别提取  
3. ⬜ 本地大模型生成框架  
4. ⬜ 生成PPT
5. ⬜ PPT编辑     

## 部署指南

### 环境要求
- Python 3.8+
- CUDA支持（用于Whisper语音识别，推荐但非必须）
- 足够的磁盘空间用于存储视频和关键帧

### 安装步骤

1. **克隆代码库**
   ```bash
   git clone https://github.com/yourusername/video_to_ppt.git
   cd video_to_ppt
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **下载Whisper模型**   我是默认base模型，如果你想使用其他模型，可以修改代码中的模型名称。
   ```bash
   # 创建下载脚本
   cat > download_whisper_model.py << 'EOF'
   #!/usr/bin/env python3
   import whisper
   print("开始下载Whisper模型: base")
   model = whisper.load_model("base")
   print("模型下载完成!")
   EOF
   
   # 运行下载脚本
   python download_whisper_model.py
   ```

4. **创建必要的目录**
   ```bash
   mkdir -p uploads keyframes
   chmod 777 uploads keyframes
   ```

### 启动服务

```bash
python server.py
```

服务将在 http://localhost:9800 启动，可以通过浏览器访问。

### 使用Docker部署（可选）

1. **创建Dockerfile**
   ```bash
   cat > Dockerfile << 'EOF'
   FROM python:3.9-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   # 创建必要的目录并设置权限
   RUN mkdir -p uploads keyframes && chmod 777 uploads keyframes
   
   # 下载Whisper模型
   RUN python -c "import whisper; whisper.load_model('base')"
   
   EXPOSE 9800
   
   CMD ["python", "server.py"]
   EOF
   ```

2. **构建并运行Docker容器**
   ```bash
   docker build -t video-to-ppt .
   docker run -p 9800:9800 -v $(pwd)/uploads:/app/uploads -v $(pwd)/keyframes:/app/keyframes video-to-ppt
   ```

### 常见问题排查

1. **上传视频失败**
   - 检查uploads和keyframes目录权限：`chmod 777 uploads keyframes`
   - 检查磁盘空间是否充足

2. **语音识别不工作**
   - 确保已下载Whisper模型：`python download_whisper_model.py`
   - 检查是否安装了PyTorch和CUDA（可选但推荐）

3. **服务器启动失败**
   - 检查端口9800是否被占用：`lsof -i:9800`
   - 检查Python版本是否兼容：`python --version`

### 系统配置

- 默认端口：9800（可在server.py中修改）
- 上传文件大小限制：500MB（可在server.py中修改）
- 支持的视频格式：MP4, AVI, MOV, MKV, WMV, FLV


## 贡献指南 

欢迎提交PR！
