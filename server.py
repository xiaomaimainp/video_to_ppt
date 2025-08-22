#!/usr/bin/env python3
"""
视频关键帧提取器 - Web服务器
在端口9800运行，提供视频上传和关键帧提取功能
"""

import os
import uuid
import json
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from extractor import VideoKeyframeExtractor

# 创建Flask应用
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 限制上传文件大小为500MB

# 配置文件夹
UPLOAD_FOLDER = 'uploads'
KEYFRAMES_FOLDER = 'keyframes'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'}

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(KEYFRAMES_FOLDER, exist_ok=True)

# 创建提取器实例
extractor = VideoKeyframeExtractor(debug_enabled=False)

# 检查文件扩展名是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    if 'video' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['video']
    
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        # 生成唯一文件名
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        base_name, extension = os.path.splitext(filename)
        unique_filename = f"{base_name}_{unique_id}{extension}"
        
        # 保存上传的文件
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'filename': unique_filename,
            'original_name': filename
        })
    
    return jsonify({'error': '不支持的文件类型'}), 400

@app.route('/extract', methods=['POST'])
def extract_keyframes():
    """提取关键帧"""
    data = request.json
    
    if not data or 'filename' not in data:
        return jsonify({'error': '缺少文件名'}), 400
    
    filename = data['filename']
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(video_path):
        return jsonify({'error': '文件不存在'}), 404
    
    # 提取参数
    capture_interval = float(data.get('interval', 1.0))
    max_screenshots = int(data.get('max_frames', 50))
    
    # 创建输出目录
    output_dir = os.path.join(KEYFRAMES_FOLDER, os.path.splitext(filename)[0])
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 获取视频时长
        video_duration = extractor.get_video_duration(video_path)
        duration_formatted = extractor.format_duration(video_duration)
        
        # 提取关键帧
        keyframes_info = extractor.extract_keyframes(
            video_path=video_path,
            output_dir=output_dir,
            capture_interval=capture_interval,
            max_screenshots=max_screenshots
        )
        
        # 准备返回数据
        keyframe_data = []
        for kf in keyframes_info:
            relative_path = os.path.relpath(kf["path"], start=os.path.dirname(KEYFRAMES_FOLDER))
            url = f"/keyframes/{os.path.basename(output_dir)}/{os.path.basename(kf['path'])}"
            
            keyframe_data.append({
                'url': url,
                'timestamp': kf['timestamp'],
                'timestamp_formatted': kf['timestamp_formatted'].replace('-', ':'),
                'frame_number': kf['frame_number'],
                'difference': kf['difference']
            })
        
        return jsonify({
            'success': True,
            'message': f'成功提取 {len(keyframes_info)} 个关键帧',
            'video_duration': video_duration,
            'video_duration_formatted': duration_formatted,
            'keyframes': keyframe_data,
            'output_dir': f"/keyframes/{os.path.basename(output_dir)}"
        })
        
    except Exception as e:
        return jsonify({'error': f'提取失败: {str(e)}'}), 500

@app.route('/keyframes/<path:filename>')
def serve_keyframe(filename):
    """提供关键帧图片"""
    return send_from_directory(KEYFRAMES_FOLDER, filename)

@app.route('/list_videos')
def list_videos():
    """列出已上传的视频"""
    videos = []
    for filename in os.listdir(UPLOAD_FOLDER):
        if allowed_file(filename):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            videos.append({
                'filename': filename,
                'size': os.path.getsize(file_path),
                'upload_time': os.path.getctime(file_path)
            })
    
    return jsonify({'videos': videos})

@app.route('/list_keyframes/<filename>')
def list_keyframes(filename):
    """列出视频的关键帧"""
    base_name = os.path.splitext(filename)[0]
    keyframes_dir = os.path.join(KEYFRAMES_FOLDER, base_name)
    
    if not os.path.exists(keyframes_dir):
        return jsonify({'error': '没有找到关键帧'}), 404
    
    # 获取视频路径
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    video_duration = 0
    duration_formatted = "00:00:00"
    
    if os.path.exists(video_path):
        try:
            video_duration = extractor.get_video_duration(video_path)
            duration_formatted = extractor.format_duration(video_duration)
        except Exception as e:
            print(f"获取视频时长失败: {e}")
    
    # 收集关键帧信息
    keyframe_data = []
    for img in sorted(os.listdir(keyframes_dir)):
        if img.lower().endswith(('.jpg', '.jpeg', '.png')):
            # 尝试从文件名中提取时间戳
            timestamp_str = ""
            timestamp = 0
            
            # 新格式: keyframe_HH-MM-SS-ms_0001.jpg
            parts = img.split('_')
            if len(parts) >= 3 and '-' in parts[1]:
                try:
                    time_parts = parts[1].split('-')
                    if len(time_parts) >= 3:
                        h = int(time_parts[0])
                        m = int(time_parts[1])
                        s = int(time_parts[2])
                        ms = int(time_parts[3]) if len(time_parts) > 3 else 0
                        
                        timestamp = h * 3600 + m * 60 + s + ms / 1000
                        timestamp_str = f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
                except Exception:
                    pass
            
            keyframe_data.append({
                'url': f"/keyframes/{base_name}/{img}",
                'filename': img,
                'timestamp': timestamp,
                'timestamp_formatted': timestamp_str
            })
    
    # 按时间戳排序
    keyframe_data.sort(key=lambda x: x['timestamp'])
    
    return jsonify({
        'keyframes': keyframe_data,
        'video_duration': video_duration,
        'video_duration_formatted': duration_formatted
    })

if __name__ == '__main__':
    print(f"启动视频关键帧提取服务器，端口: 9800")
    app.run(host='0.0.0.0', port=9800, debug=True)