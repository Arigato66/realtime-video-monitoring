import cv2
import numpy as np
import os
import time
from flask import Response
from ultralytics import YOLO

from app.services import detection as detection_service
from app.services.danger_zone import DANGER_ZONE
from app.services.alerts import update_detection_time, reset_alerts
from app.services import system_state

# 全局变量，用于控制摄像头视频流的循环
CAMERA_ACTIVE = False
# 全局变量来持有YOLO模型，避免重复加载
model = None
# 用于人脸识别模式的状态缓存
face_recognition_cache = {}

def video_feed():
    """实时视频流处理，包括目标检测和人脸识别"""
    global CAMERA_ACTIVE
    CAMERA_ACTIVE = True

    # 重置警报，以便为新的实时会话提供干净的状态
    reset_alerts()

    # 初始化YOLO模型
    global model
    model = detection_service.get_model()

    # 打开默认摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("错误：无法打开摄像头。")
        return Response("无法打开摄像头。", mimetype='text/plain')

    frame_count = 0

    def generate():
        nonlocal frame_count
        while CAMERA_ACTIVE:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1

            # 诊断日志: 打印当前检测模式
            if frame_count % 30 == 0: # 每30帧打印一次，避免刷屏
                print(f"[Diagnostics] Current detection mode: {system_state.DETECTION_MODE}")
            
            # 计算帧之间的时间差以进行徘徊检测
            time_diff = update_detection_time()

            processed_frame = frame.copy()

            # 根据当前模式决定处理方式
            if system_state.DETECTION_MODE == 'object_detection':
                # 使用YOLOv8进行目标追踪
                outputs = model.track(processed_frame, persist=True)
                
                # 在绘制的帧上应用我们的自定义检测逻辑
                detection_service.process_detection_results(outputs, processed_frame, time_diff, frame_count)
            
            elif system_state.DETECTION_MODE == 'fall_detection':
                # 新增：处理跌倒检测模式
                pose_model = detection_service.get_pose_model() # 获取姿态估计模型
                pose_results = pose_model.track(processed_frame, persist=True)
                detection_service.process_pose_estimation_results(pose_results, processed_frame, time_diff, frame_count)

            elif system_state.DETECTION_MODE == 'face_only':
                # 确保已初始化人脸模式的状态字典和模型
                if 'face_model' not in face_recognition_cache:
                    face_recognition_cache['face_model'] = detection_service.get_face_model()
                
                # 传递当前时间戳给处理函数，用于计算识别间隔
                face_recognition_cache['current_time'] = time.time()
                
                # 直接在原始帧上进行处理
                detection_service.process_faces_only(frame, frame_count, face_recognition_cache)
                
                # 将处理结果复制到要编码的帧上
                processed_frame = frame
            
            elif system_state.DETECTION_MODE == 'smoking_detection':
                # 获取抽烟检测模型
                smoking_model = detection_service.get_smoking_model()
                # 执行检测
                results = smoking_model.predict(processed_frame)
                # 处理并绘制结果
                detection_service.process_smoking_detection_results(results, processed_frame, smoking_model)

            # 将处理后的帧编码为JPEG格式
            (flag, encodedImage) = cv2.imencode(".jpg", processed_frame)
            if not flag:
                continue
                
            # 以multipart格式产生输出帧
            yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                  bytearray(encodedImage) + b'\r\n')
            
    # 返回一个包含视频流的HTTP响应
    return Response(generate(),
                    mimetype = "multipart/x-mixed-replace; boundary=frame")

def stop_video_feed_service():
    """停止摄像头视频流的服务函数"""
    global CAMERA_ACTIVE
    CAMERA_ACTIVE = False
    print("摄像头视频流已请求停止。")
    return True 