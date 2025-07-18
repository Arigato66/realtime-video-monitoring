#!/usr/bin/env python3
"""
测试视频片段保存和回放功能
"""

import os
import sys
import cv2
import numpy as np
import time
from datetime import datetime

# 添加backend路径到sys.path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# 设置工作目录到backend
os.chdir(backend_path)

from app.services.video_clip_service import get_video_clip_manager
from app.services.alerts import add_alert, add_frame_to_stream_buffer

def create_test_video_frames(num_frames=150):
    """创建测试视频帧"""
    frames = []
    for i in range(num_frames):
        # 创建一个简单的测试帧
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 添加一些动态内容
        cv2.rectangle(frame, (50 + i*2, 50), (150 + i*2, 150), (0, 255, 0), 2)
        cv2.putText(frame, f'Frame {i}', (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, datetime.now().strftime('%H:%M:%S.%f')[:-3], (200, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        frames.append(frame)
    
    return frames

def test_video_clip_functionality():
    """测试视频片段功能"""
    print("🎬 开始测试视频片段功能...")
    
    # 获取视频片段管理器
    clip_manager = get_video_clip_manager()
    
    # 创建测试帧
    print("📹 创建测试视频帧...")
    test_frames = create_test_video_frames(150)  # 5秒的视频（30fps）
    
    # 模拟视频流处理
    stream_id = "test_stream"
    
    print("🔄 模拟视频流处理...")
    # 添加前50帧到缓存（模拟告警前的缓存）
    for i, frame in enumerate(test_frames[:50]):
        add_frame_to_stream_buffer(stream_id, frame)
        time.sleep(0.01)  # 模拟实时处理
    
    print("🚨 触发告警...")
    # 触发告警
    add_alert(
        "测试告警：检测到异常行为", 
        stream_id=stream_id, 
        alert_type="test_alert", 
        severity="high"
    )
    
    # 继续添加告警后的帧
    for i, frame in enumerate(test_frames[50:100]):
        add_frame_to_stream_buffer(stream_id, frame)
        time.sleep(0.01)
    
    print("⏹️ 等待视频保存完成...")
    time.sleep(8)  # 等待视频保存完成
    
    # 列出保存的视频片段
    print("📋 列出保存的视频片段...")
    clips = clip_manager.list_clips()
    
    if clips:
        print(f"✅ 成功保存了 {len(clips)} 个视频片段:")
        for clip in clips:
            print(f"  - 片段ID: {clip['clip_id']}")
            print(f"    告警类型: {clip.get('alert_info', {}).get('type', 'unknown')}")
            print(f"    创建时间: {clip['created_at']}")
            print(f"    视频时长: {clip.get('duration', 0):.2f}秒")
            print(f"    文件大小: {clip.get('file_size', 0)} 字节")
            print(f"    视频路径: {clip.get('video_path', 'N/A')}")
            print(f"    截图路径: {clip.get('snapshot_path', 'N/A')}")
            print()
            
            # 验证文件是否存在
            video_path = clip.get('video_path')
            snapshot_path = clip.get('snapshot_path')
            
            if video_path and os.path.exists(video_path):
                print(f"    ✅ 视频文件存在: {video_path}")
            else:
                print(f"    ❌ 视频文件不存在: {video_path}")
                
            if snapshot_path and os.path.exists(snapshot_path):
                print(f"    ✅ 截图文件存在: {snapshot_path}")
            else:
                print(f"    ❌ 截图文件不存在: {snapshot_path}")
            
            print("-" * 50)
    else:
        print("❌ 没有找到保存的视频片段")
    
    return clips

def test_video_playback(clips):
    """测试视频播放"""
    if not clips:
        print("❌ 没有视频片段可以播放")
        return
    
    clip = clips[0]
    video_path = clip.get('video_path')
    
    if not video_path or not os.path.exists(video_path):
        print("❌ 视频文件不存在，无法播放")
        return
    
    print(f"🎥 播放视频: {video_path}")
    
    # 使用OpenCV播放视频
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("❌ 无法打开视频文件")
        return
    
    print("▶️ 开始播放视频（按 'q' 退出）...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        cv2.imshow('Video Playback Test', frame)
        
        # 按 'q' 退出
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("⏹️ 视频播放结束")

def cleanup_test_files():
    """清理测试文件"""
    print("🧹 清理测试文件...")
    clip_manager = get_video_clip_manager()
    
    clips = clip_manager.list_clips()
    deleted_count = 0
    
    for clip in clips:
        if clip.get('alert_info', {}).get('type') == 'test_alert':
            if clip_manager.delete_clip(clip['clip_id']):
                deleted_count += 1
    
    print(f"✅ 清理了 {deleted_count} 个测试文件")

if __name__ == "__main__":
    try:
        # 测试视频片段功能
        clips = test_video_clip_functionality()
        
        # 询问是否播放视频
        if clips:
            play_video = input("\n🎬 是否播放测试视频？(y/n): ").lower().strip()
            if play_video == 'y':
                test_video_playback(clips)
        
        # 询问是否清理测试文件
        cleanup = input("\n🧹 是否清理测试文件？(y/n): ").lower().strip()
        if cleanup == 'y':
            cleanup_test_files()
        
        print("\n✅ 测试完成！")
        
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
