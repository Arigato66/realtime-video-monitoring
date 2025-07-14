import cv2
import numpy as np
import os
import time
from flask import Response
from ultralytics import YOLO

from app.services import detection as detection_service
from app.services.alerts import update_detection_time, reset_alerts, add_alert
from app.services import system_state
from app.services.violenceDetect import load_model_safely, process_frame as violence_process_frame, CUSTOM_OBJECTS
import tensorflow as tf
from collections import deque

# 全局变量，用于控制摄像头视频流的循环
CAMERA_ACTIVE = False
# -- REMOVED --: Global model instances are removed to prevent state conflicts.
# model = None
# face_recognition_cache = {}

def video_feed():
    """实时视频流处理，为每个会话创建独立的模型实例。"""
    global CAMERA_ACTIVE
    CAMERA_ACTIVE = True

    # 重置警报，以便为新的实时会话提供干净的状态
    reset_alerts()

    # --- FIX: Create session-local model instances ---
    # These instances live only for the duration of this camera session.
    print("Initializing new model instances for real-time stream...")
    object_model_stream = YOLO(detection_service.OBJECT_MODEL_PATH)
    face_model_stream = YOLO(detection_service.FACE_MODEL_PATH)
    pose_model_stream = YOLO(detection_service.POSE_MODEL_PATH)
    smoking_model_service = detection_service.get_smoking_model() # This is a stateless service wrapper
    face_recognition_cache = {} # Create a fresh cache for this session

    # 暴力检测模型和特征提取器（仅在首次用到时加载）
    violence_model = None
    vgg_model = None
    image_model_transfer = None
    violence_buffer = deque(maxlen=20)
    violence_status = "unknown"
    violence_prob = 0.0
    violence_last_infer_frame = -100
    violence_infer_interval = 10  # 每10帧推理一次

    # 打开默认摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("错误：无法打开摄像头。")
        return Response("无法打开摄像头。", mimetype='text/plain')

    frame_count = 0

    def generate():
        nonlocal frame_count, violence_model, vgg_model, image_model_transfer, violence_status, violence_prob, violence_last_infer_frame
        try:
            while CAMERA_ACTIVE:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_count += 1

                # 诊断日志
                if frame_count % 30 == 0:
                    print(f"[Diagnostics] Current detection mode: {system_state.DETECTION_MODE}")
                
                time_diff = update_detection_time()
                processed_frame = frame.copy()

                # 根据当前模式决定处理方式 (All modes now use session-local models)
                if system_state.DETECTION_MODE == 'violence_detection':
                    # 初始化模型和特征提取器
                    if violence_model is None:
                        import os
                        model_path = os.path.join(os.path.dirname(__file__), 'vd.hdf5')
                        violence_model = load_model_safely(model_path)
                        try:
                            vgg_model = tf.keras.applications.VGG16(include_top=True, weights='imagenet')
                        except Exception:
                            vgg_model = tf.keras.applications.VGG16(include_top=True, weights=None)
                        transfer_layer = vgg_model.get_layer('fc2')
                        image_model_transfer = tf.keras.models.Model(inputs=vgg_model.input, outputs=transfer_layer.output)
                    # 处理帧并加入缓冲区
                    violence_buffer.append(violence_process_frame(frame))
                    # 每N帧推理一次
                    if len(violence_buffer) == 20 and (frame_count - violence_last_infer_frame >= violence_infer_interval):
                        violence_last_infer_frame = frame_count
                        try:
                            transfer_values = image_model_transfer.predict(np.array(violence_buffer), verbose=0)
                            prediction = violence_model.predict(np.array([transfer_values]), verbose=0)
                            violence_prob = float(prediction[0][0])
                            # 状态判断
                            if violence_prob <= 0.5:
                                violence_status = "safe"
                            elif violence_prob <= 0.7:
                                violence_status = "caution"
                                add_alert("caution: 检测到可能的暴力行为")
                            else:
                                violence_status = "warning"
                                add_alert("warning: 检测到高概率暴力行为!")
                        except Exception as e:
                            violence_status = "error"
                            violence_prob = 0.0
                            print(f"暴力检测推理异常: {e}")
                    # 叠加状态到画面
                    color = (0, 255, 0) if violence_status == "safe" else (0, 255, 255) if violence_status == "caution" else (0, 0, 255)
                    cv2.putText(processed_frame, f"state: {violence_status}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    cv2.putText(processed_frame, f"violenceProbability: {violence_prob:.4f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                elif system_state.DETECTION_MODE == 'object_detection':
                    outputs = object_model_stream.track(processed_frame, persist=True)
                    detection_service.process_object_detection_results(outputs, processed_frame, time_diff, frame_count)
                
                elif system_state.DETECTION_MODE == 'fall_detection':
                    pose_results = pose_model_stream.track(processed_frame, persist=True)
                    detection_service.process_pose_estimation_results(pose_results, processed_frame, time_diff, frame_count)

                elif system_state.DETECTION_MODE == 'face_only':
                    # 修复：恢复 state 参数的传递，这是必须的
                    if 'face_model' not in face_recognition_cache:
                        face_recognition_cache['face_model'] = face_model_stream
                    detection_service.process_faces_only(processed_frame, frame_count, face_recognition_cache)
                
                elif system_state.DETECTION_MODE == 'smoking_detection':
                    face_results = face_model_stream.predict(processed_frame, verbose=False)
                    person_results = object_model_stream.track(processed_frame, persist=True, classes=[0], verbose=False)
                    detection_service.process_smoking_detection_hybrid(
                        processed_frame, person_results, face_results, smoking_model_service
                    )

                # 将处理后的帧编码为JPEG格式
                (flag, encodedImage) = cv2.imencode(".jpg", processed_frame)
                if not flag:
                    continue
                    
                # 以multipart格式产生输出帧
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                      bytearray(encodedImage) + b'\r\n')
        finally:
            # 确保无论如何都能释放摄像头
            print("释放摄像头资源...")
            cap.release()
            cv2.destroyAllWindows()
            
    # 返回一个包含视频流的HTTP响应
    return Response(generate(),
                    mimetype = "multipart/x-mixed-replace; boundary=frame")

def stop_video_feed_service():
    """停止摄像头视频流的服务函数"""
    global CAMERA_ACTIVE
    CAMERA_ACTIVE = False
    print("摄像头视频流已请求停止。")
    return True 