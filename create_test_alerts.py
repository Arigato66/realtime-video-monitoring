#!/usr/bin/env python3
import requests
import json

API_BASE_URL = "http://127.0.0.1:5000/api"

def create_test_alert(event_type, details, video_path=None, frame_snapshot_path=None):
    """创建测试告警"""
    data = {
        "event_type": event_type,
        "details": details
    }
    if video_path:
        data["video_path"] = video_path
    if frame_snapshot_path:
        data["frame_snapshot_path"] = frame_snapshot_path
    
    try:
        response = requests.post(f"{API_BASE_URL}/alerts/", 
                               headers={"Content-Type": "application/json"},
                               json=data)
        if response.status_code == 201:
            print(f"✅ 成功创建告警: {event_type}")
            return response.json()
        else:
            print(f"❌ 创建告警失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def main():
    print("开始创建测试告警数据...")
    
    # 创建多个测试告警
    test_alerts = [
        {
            "event_type": "smoking_detection",
            "details": "在办公区域检测到吸烟行为",
            "video_path": "/static/videos/smoking_detection_001.mp4",
            "frame_snapshot_path": "/static/snapshots/smoking_001.jpg"
        },
        {
            "event_type": "fire_detection", 
            "details": "在仓库区域检测到火焰",
            "video_path": "/static/videos/fire_detection_001.mp4",
            "frame_snapshot_path": "/static/snapshots/fire_001.jpg"
        },
        {
            "event_type": "intrusion_detection",
            "details": "在禁区检测到人员入侵",
            "video_path": "/static/videos/intrusion_001.mp4",
            "frame_snapshot_path": "/static/snapshots/intrusion_001.jpg"
        },
        {
            "event_type": "violence_detection",
            "details": "在公共区域检测到暴力行为",
            "video_path": "/static/videos/violence_001.mp4", 
            "frame_snapshot_path": "/static/snapshots/violence_001.jpg"
        },
        {
            "event_type": "smoking_detection",
            "details": "在会议室检测到吸烟行为",
            "video_path": "/static/videos/smoking_detection_002.mp4",
            "frame_snapshot_path": "/static/snapshots/smoking_002.jpg"
        }
    ]
    
    created_count = 0
    for alert_data in test_alerts:
        result = create_test_alert(**alert_data)
        if result:
            created_count += 1
    
    print(f"\n✅ 总共创建了 {created_count} 个测试告警")
    
    # 获取告警列表验证
    try:
        response = requests.get(f"{API_BASE_URL}/alerts/")
        if response.status_code == 200:
            data = response.json()
            print(f"📊 当前数据库中共有 {data.get('total', 0)} 个告警")
        else:
            print(f"❌ 获取告警列表失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 获取告警列表失败: {e}")

if __name__ == "__main__":
    main()