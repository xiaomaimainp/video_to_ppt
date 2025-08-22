#!/usr/bin/env python3
"""
视频关键帧提取器核心实现
专为web服务器端口9800设计
"""

import os
import cv2
import numpy as np
import time
import datetime
from dataclasses import dataclass
from typing import List, Callable, Optional, Dict, Tuple, Any

@dataclass
class KeyframeInfo:
    """关键帧信息"""
    path: str  # 文件路径
    timestamp: float  # 时间戳（秒）
    frame_number: int  # 帧号
    difference: float = 0.0  # 与前一帧的差异度
    
    def format_timestamp(self) -> str:
        """将时间戳格式化为 HH:MM:SS.ms 格式"""
        ms = int((self.timestamp % 1) * 1000)
        s = int(self.timestamp)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

class VideoKeyframeExtractor:
    """视频关键帧提取器"""
    
    def __init__(self, debug_enabled: bool = False):
        """
        初始化提取器
        
        Args:
            debug_enabled: 是否启用调试输出
        """
        self.debug_enabled = debug_enabled
        self.last_progress_update = 0
        self.video_duration = 0.0  # 视频总时长（秒）
    
    def debug(self, message: str) -> None:
        """输出调试信息"""
        if self.debug_enabled:
            print(f"[DEBUG] {message}")
    
    def calculate_frame_difference(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """
        计算两帧之间的差异度
        
        Args:
            frame1: 第一帧
            frame2: 第二帧
            
        Returns:
            float: 差异度 (0-1)
        """
        # 转换为灰度图
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # 计算绝对差异
        diff = cv2.absdiff(gray1, gray2)
        
        # 计算平均差异
        mean_diff = np.mean(diff) / 255.0
        
        return mean_diff
    
    def calculate_adaptive_threshold(self, video_path: str, sample_count: int = 10) -> float:
        """
        计算自适应阈值
        
        Args:
            video_path: 视频文件路径
            sample_count: 采样帧数
            
        Returns:
            float: 自适应阈值
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        # 获取视频信息
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if frame_count <= 1:
            cap.release()
            return 0.1  # 默认阈值
        
        # 计算采样间隔
        interval = max(1, frame_count // (sample_count + 1))
        
        # 采样并计算差异
        differences = []
        prev_frame = None
        
        for i in range(sample_count + 1):
            frame_pos = i * interval
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            
            if not ret:
                break
                
            if prev_frame is not None:
                diff = self.calculate_frame_difference(prev_frame, frame)
                differences.append(diff)
                
            prev_frame = frame
        
        cap.release()
        
        # 计算阈值
        if not differences:
            return 0.1  # 默认阈值
            
        # 使用差异的平均值和标准差计算阈值
        mean_diff = np.mean(differences)
        std_diff = np.std(differences)
        
        # 阈值 = 平均值 + 0.5 * 标准差
        threshold = mean_diff + 0.5 * std_diff
        
        # 确保阈值在合理范围内
        threshold = max(0.05, min(threshold, 0.3))
        
        self.debug(f"自适应阈值: {threshold:.4f} (平均差异: {mean_diff:.4f}, 标准差: {std_diff:.4f})")
        
        return threshold
    
    def get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            float: 视频时长（秒）
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        # 获取帧率和总帧数
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0  # 默认帧率
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 计算视频时长（秒）
        duration = frame_count / fps if frame_count > 0 and fps > 0 else 0
        
        cap.release()
        
        return duration
    
    def format_duration(self, seconds: float) -> str:
        """
        将秒数格式化为 HH:MM:SS 格式
        
        Args:
            seconds: 秒数
            
        Returns:
            str: 格式化后的时间字符串
        """
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    
    def extract_keyframes(
        self, 
        video_path: str, 
        output_dir: str = "keyframes",
        capture_interval: float = 1.0,
        max_screenshots: int = 50,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        从视频中提取关键帧
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            capture_interval: 捕获间隔（秒）
            max_screenshots: 最大截图数量
            progress_callback: 进度回调函数
            
        Returns:
            List[Dict[str, Any]]: 关键帧信息列表，包含路径、时间戳等信息
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0  # 默认帧率
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if frame_count > 0 else 0
        
        self.debug(f"视频信息: 路径={video_path}, 时长={duration:.2f}秒, 帧率={fps:.2f}, 总帧数={frame_count}")
        
        # 计算自适应阈值
        threshold = self.calculate_adaptive_threshold(video_path)
        self.debug(f"使用差异阈值: {threshold:.4f}")
        
        # 计算帧间隔
        frame_interval = int(capture_interval * fps)
        if frame_interval < 1:
            frame_interval = 1
        
        # 获取视频总时长
        self.video_duration = self.get_video_duration(video_path)
        duration_formatted = self.format_duration(self.video_duration)
        self.debug(f"视频总时长: {self.video_duration:.2f}秒 ({duration_formatted})")
        
        # 初始化变量
        keyframes_info = []
        prev_frame = None
        frame_position = 0
        screenshot_count = 0
        
        # 计算总处理帧数
        total_frames_to_process = min(frame_count, int(frame_count / frame_interval) * frame_interval)
        
        # 开始处理
        start_time = time.time()
        
        while frame_position < frame_count and screenshot_count < max_screenshots:
            # 设置帧位置
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # 计算当前时间戳（秒）
            timestamp = frame_position / fps
            timestamp_formatted = self.format_timestamp(timestamp)
            
            # 计算进度
            progress = (frame_position / total_frames_to_process) * 100 if total_frames_to_process > 0 else 0
            
            # 更新进度（限制更新频率）
            current_time = time.time()
            if progress_callback and (current_time - self.last_progress_update > 0.5 or progress >= 100):
                progress_callback(progress)
                self.last_progress_update = current_time
            
            # 第一帧总是保存
            if prev_frame is None:
                # 生成文件名，包含时间戳
                filename = f"keyframe_{timestamp_formatted}_{screenshot_count:04d}.jpg"
                output_path = os.path.join(output_dir, filename)
                
                # 保存关键帧
                cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                # 记录关键帧信息
                keyframe_info = {
                    "path": output_path,
                    "timestamp": timestamp,
                    "timestamp_formatted": timestamp_formatted,
                    "frame_number": frame_position,
                    "difference": 0.0
                }
                keyframes_info.append(keyframe_info)
                
                screenshot_count += 1
                self.debug(f"保存第一帧: {output_path} (时间: {timestamp_formatted})")
            else:
                # 计算与前一帧的差异
                diff = self.calculate_frame_difference(prev_frame, frame)
                
                # 如果差异超过阈值，保存为关键帧
                if diff > threshold:
                    # 生成文件名，包含时间戳
                    filename = f"keyframe_{timestamp_formatted}_{screenshot_count:04d}.jpg"
                    output_path = os.path.join(output_dir, filename)
                    
                    # 保存关键帧
                    cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    
                    # 记录关键帧信息
                    keyframe_info = {
                        "path": output_path,
                        "timestamp": timestamp,
                        "timestamp_formatted": timestamp_formatted,
                        "frame_number": frame_position,
                        "difference": diff
                    }
                    keyframes_info.append(keyframe_info)
                    
                    screenshot_count += 1
                    self.debug(f"保存关键帧: {output_path}, 时间: {timestamp_formatted}, 差异: {diff:.4f}")
            
            # 更新前一帧
            prev_frame = frame.copy()
            
            # 移动到下一个位置
            frame_position += frame_interval
        
        # 释放资源
        cap.release()
        
        # 最后一次更新进度
        if progress_callback:
            progress_callback(100)
        
        # 计算处理时间
        elapsed_time = time.time() - start_time
        self.debug(f"处理完成，耗时: {elapsed_time:.2f}秒, 提取了 {len(keyframes_info)} 个关键帧")
        
        return keyframes_info
    
    def format_timestamp(self, seconds: float) -> str:
        """
        将秒数格式化为文件名友好的时间戳格式 (HH-MM-SS-ms)
        
        Args:
            seconds: 秒数
            
        Returns:
            str: 格式化后的时间字符串
        """
        ms = int((seconds % 1) * 1000)
        s = int(seconds)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}-{m:02d}-{s:02d}-{ms:03d}"
