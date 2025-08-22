#!/usr/bin/env python3
"""
视频关键帧提取器 - Web服务器
在端口9800运行，提供视频上传、关键帧提取和语音识别功能
"""

import os
import uuid
import json
from flask import Flask, request, render_template, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from extractor import VideoKeyframeExtractor
from asr_processor import ASRProcessor

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

# 创建ASR处理器实例（延迟加载，首次使用时才会加载模型）
asr_processor = None
def get_asr_processor():
    global asr_processor
    if asr_processor is None:
        # 使用已经成功下载的base模型
        asr_processor = ASRProcessor(model_name="base")
    return asr_processor

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
    max_screenshots = int(data.get('max_frames', 5000))
    force_interval = float(data.get('force_interval', 25.0))  
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
            max_screenshots=max_screenshots,
            force_interval=force_interval
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

@app.route('/delete_file', methods=['POST'])
def delete_file():
    """删除文件及其关键帧"""
    data = request.json
    
    if not data or 'filename' not in data:
        return jsonify({'error': '缺少文件名'}), 400
    
    filename = data['filename']
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    
    # 检查文件是否存在
    if not os.path.exists(video_path):
        return jsonify({'error': '文件不存在'}), 404
    
    try:
        # 删除视频文件
        os.remove(video_path)
        
        # 删除关键帧目录
        base_name = os.path.splitext(filename)[0]
        keyframes_dir = os.path.join(KEYFRAMES_FOLDER, base_name)
        
        if os.path.exists(keyframes_dir):
            # 删除目录中的所有文件
            for file in os.listdir(keyframes_dir):
                file_path = os.path.join(keyframes_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            # 删除目录
            os.rmdir(keyframes_dir)
        
        return jsonify({
            'success': True,
            'message': f'成功删除文件 {filename} 及其关键帧'
        })
        
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

@app.route('/delete_keyframes', methods=['POST'])
def delete_keyframes():
    """删除选中的关键帧"""
    data = request.json
    
    if not data or 'filename' not in data or 'urls' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    filename = data['filename']
    urls = data['urls']
    
    if not urls or not isinstance(urls, list):
        return jsonify({'error': '无效的URL列表'}), 400
    
    base_name = os.path.splitext(filename)[0]
    keyframes_dir = os.path.join(KEYFRAMES_FOLDER, base_name)
    
    if not os.path.exists(keyframes_dir):
        return jsonify({'error': '关键帧目录不存在'}), 404
    
    try:
        deleted_count = 0
        
        for url in urls:
            # 从URL中提取文件名
            keyframe_filename = url.split('/')[-1]
            keyframe_path = os.path.join(keyframes_dir, keyframe_filename)
            
            if os.path.exists(keyframe_path):
                os.remove(keyframe_path)
                deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个关键帧'
        })
        
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

@app.route('/process_asr', methods=['POST'])
def process_asr():
    """处理视频ASR（自动语音识别）"""
    data = request.json
    
    if not data or 'filename' not in data:
        return jsonify({'error': '缺少文件名'}), 400
    
    filename = data['filename']
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(video_path):
        return jsonify({'error': '文件不存在'}), 404
    
    # 设置语言（默认为中文）
    language = data.get('language', 'zh')
    
    # 设置输出目录
    base_name = os.path.splitext(filename)[0]
    output_dir = os.path.join(KEYFRAMES_FOLDER, base_name)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 获取ASR处理器实例
        processor = get_asr_processor()
        
        # 处理视频
        result = processor.process_video(
            video_path=video_path,
            language=language,
            output_dir=output_dir
        )
        
        # 构建ASR结果的URL
        asr_filename = f"{base_name}_asr.json"
        asr_path = os.path.join(output_dir, asr_filename)
        asr_url = f"/keyframes/{base_name}/{asr_filename}"
        
        return jsonify({
            'success': True,
            'message': '语音识别完成',
            'asr_url': asr_url,
            'sentences_count': len(result.get('result', {}).get('sentences', [])),
            'duration': result.get('result', {}).get('segments', [{}])[-1].get('end', 0) if result.get('result', {}).get('segments') else 0
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'语音识别失败: {str(e)}'}), 500

@app.route('/keyframes/<path:filename>')
def serve_keyframes(filename):
    """提供关键帧文件访问"""
    return send_from_directory(KEYFRAMES_FOLDER, filename)

@app.route('/clear_all', methods=['POST'])
def clear_all():
    """清空所有上传的视频和关键帧"""
    try:
        # 删除上传文件夹中的所有文件
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # 删除关键帧文件夹中的所有内容
        for dirname in os.listdir(KEYFRAMES_FOLDER):
            dir_path = os.path.join(KEYFRAMES_FOLDER, dirname)
            if os.path.isdir(dir_path):
                # 删除目录中的所有文件
                for file in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                # 删除目录
                os.rmdir(dir_path)
        
        return jsonify({
            'success': True,
            'message': '成功清空所有视频和关键帧'
        })
        
    except Exception as e:
        return jsonify({'error': f'清空失败: {str(e)}'}), 500

@app.route('/export_data', methods=['GET'])
def export_data():
    """导出所有数据为ZIP文件"""
    import zipfile
    import tempfile
    import shutil
    
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'video_to_ppt_data.zip')
            
            # 创建ZIP文件
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加上传的视频
                for filename in os.listdir(UPLOAD_FOLDER):
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.isfile(file_path):
                        zipf.write(file_path, os.path.join('uploads', filename))
                
                # 添加关键帧
                for dirname in os.listdir(KEYFRAMES_FOLDER):
                    dir_path = os.path.join(KEYFRAMES_FOLDER, dirname)
                    if os.path.isdir(dir_path):
                        for file in os.listdir(dir_path):
                            file_path = os.path.join(dir_path, file)
                            if os.path.isfile(file_path):
                                zipf.write(file_path, os.path.join('keyframes', dirname, file))
            
            # 发送ZIP文件
            return send_from_directory(temp_dir, 'video_to_ppt_data.zip', as_attachment=True)
            
    except Exception as e:
        return jsonify({'error': f'导出失败: {str(e)}'}), 500

@app.route('/import_data', methods=['POST'])
def import_data():
    """导入ZIP文件中的数据"""
    import zipfile
    import tempfile
    
    if 'zip_file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['zip_file']
    
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if not file.filename.endswith('.zip'):
        return jsonify({'error': '请上传ZIP文件'}), 400
    
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'uploaded.zip')
            file.save(zip_path)
            
            # 解压ZIP文件
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # 提取所有文件
                zipf.extractall(temp_dir)
                
                # 复制上传的视频
                uploads_dir = os.path.join(temp_dir, 'uploads')
                if os.path.exists(uploads_dir):
                    for filename in os.listdir(uploads_dir):
                        src_path = os.path.join(uploads_dir, filename)
                        dst_path = os.path.join(UPLOAD_FOLDER, filename)
                        if os.path.isfile(src_path):
                            shutil.copy2(src_path, dst_path)
                
                # 复制关键帧
                keyframes_dir = os.path.join(temp_dir, 'keyframes')
                if os.path.exists(keyframes_dir):
                    for dirname in os.listdir(keyframes_dir):
                        src_dir = os.path.join(keyframes_dir, dirname)
                        dst_dir = os.path.join(KEYFRAMES_FOLDER, dirname)
                        if os.path.isdir(src_dir):
                            os.makedirs(dst_dir, exist_ok=True)
                            for filename in os.listdir(src_dir):
                                src_path = os.path.join(src_dir, filename)
                                dst_path = os.path.join(dst_dir, filename)
                                if os.path.isfile(src_path):
                                    shutil.copy2(src_path, dst_path)
        
        return jsonify({
            'success': True,
            'message': '成功导入数据'
        })
        
    except Exception as e:
        return jsonify({'error': f'导入失败: {str(e)}'}), 500

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