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

def video_feed():
    """实时视频流处理，为每个会话创建独立的模型实例。"""
    global CAMERA_ACTIVE
    CAMERA_ACTIVE = True

    # 重置警报，以便为新的实时会话提供干净的状态
    reset_alerts()
    
    # --- 性能优化：添加视频源缓冲区大小的配置 ---
    # 减小缓冲区大小可降低延迟，但可能造成一定程度的画面不平滑
    # 增大可提高平滑度，但会增加延迟
    BUFFER_SIZE = 1

    # --- FIX: Create session-local model instances ---
    # These instances live only for the duration of this camera session.
    print("Initializing new model instances for real-time stream...")
    object_model_stream = YOLO(detection_service.OBJECT_MODEL_PATH)
    face_model_stream = YOLO(detection_service.FACE_MODEL_PATH)
    pose_model_stream = YOLO(detection_service.POSE_MODEL_PATH)
    smoking_model_service = detection_service.get_smoking_model() # This is a stateless service wrapper
    face_recognition_cache = {
        'face_model': face_model_stream,  # 模型实例
        'skip_frames': 0,                # 跳帧计数器
        'last_processed_frame': None,    # 上一次处理的帧
    } # Create a fresh cache for this session

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
        
    # 优化1: 减小缓冲区大小，降低延迟
    cap.set(cv2.CAP_PROP_BUFFERSIZE, BUFFER_SIZE)
        
    # 优化2: 针对不同检测模式设置不同的分辨率
    if system_state.DETECTION_MODE == 'face_only':
        # 人脸识别模式下，可以使用中等分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    else:
        # 其他模式下，根据需要设置分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

    frame_count = 0
    # --- 新增：FPS计算相关的变量 ---
    prev_frame_time = 0
    new_frame_time = 0
    
    # --- 性能优化：添加跳帧计数器 ---
    skip_frame_count = 0
    
    # --- 性能优化：设置跳帧参数 ---
    # 不同模式可以使用不同的跳帧率
    if system_state.DETECTION_MODE == 'face_only':
        PROCESS_EVERY_N_FRAMES = 1  # 人脸识别模式下，可以适当跳帧
    elif system_state.DETECTION_MODE == 'violence_detection':
        PROCESS_EVERY_N_FRAMES = 2  # 暴力检测模式需要连续帧
    else:
        PROCESS_EVERY_N_FRAMES = 1  # 其他模式默认设置

    def generate():
        nonlocal object_model_stream, face_model_stream, pose_model_stream
        nonlocal frame_count, prev_frame_time, new_frame_time, violence_model, vgg_model
        nonlocal image_model_transfer, violence_buffer, violence_status, violence_prob
        nonlocal violence_last_infer_frame, skip_frame_count
        
        try:
            while CAMERA_ACTIVE:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                frame_count += 1
                skip_frame_count += 1
                
                # --- 新增：FPS 计算 ---
                new_frame_time = time.time()
                # 避免除以零错误
                time_diff_fps = new_frame_time - prev_frame_time
                if time_diff_fps > 0:
                    fps = 1 / time_diff_fps
                    fps_text = f"FPS: {int(fps)}"
                    # --- 修改：将FPS显示移动到右上角 ---
                    # 获取文本大小以便精确放置
                    (text_width, _), _ = cv2.getTextSize(fps_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
                    # 从帧宽度中减去文本宽度和一些边距（10px）
                    top_right_x = frame.shape[1] - text_width - 10
                    cv2.putText(frame, fps_text, (top_right_x, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                prev_frame_time = new_frame_time

                # 诊断日志
                if frame_count % 30 == 0:
                    print(f"[Diagnostics] Current detection mode: {system_state.DETECTION_MODE}")
                
                time_diff = update_detection_time()
                
                # 性能优化：将原始帧保存到处理后的帧中
                processed_frame = frame.copy() # 使用复制操作确保原始帧不被修改
                
                # 性能优化：只处理每N帧，其他帧直接传递
                if skip_frame_count >= PROCESS_EVERY_N_FRAMES:
                    skip_frame_count = 0  # 重置计数器

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
                        violence_buffer.append(violence_process_frame(processed_frame))
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
                        # 优化: 创建专门的人脸识别处理逻辑
                        # 保存上一帧的结果，在需要的时候重用
                        if face_recognition_cache.get('last_processed_frame') is not None:
                            # 如果有上次处理的结果，我们直接显示它
                            if face_recognition_cache.get('skip_frames', 0) > 0:
                                face_recognition_cache['skip_frames'] -= 1
                                # 重用上次的处理结果，只添加FPS等文本信息
                                detection_service.process_faces_only(processed_frame, frame_count, face_recognition_cache)
                            else:
                                # 重置跳帧计数
                                face_recognition_cache['skip_frames'] = 2  # 每3帧做一次完整处理
                                detection_service.process_faces_only(processed_frame, frame_count, face_recognition_cache)
                                # 保存处理后的结果
                                face_recognition_cache['last_processed_frame'] = processed_frame.copy()
                        else:
                            # 第一次处理
                            detection_service.process_faces_only(processed_frame, frame_count, face_recognition_cache)
                            face_recognition_cache['last_processed_frame'] = processed_frame.copy()
                            face_recognition_cache['skip_frames'] = 2  # 设置跳帧
                    
                    elif system_state.DETECTION_MODE == 'smoking_detection':
                        face_results = face_model_stream.predict(processed_frame, verbose=False)
                        person_results = object_model_stream.track(processed_frame, persist=True, classes=[0], verbose=False)
                        detection_service.process_smoking_detection_hybrid(
                            processed_frame, person_results, face_results, smoking_model_service
                        )

                # 将处理后的帧编码为JPEG格式 - 使用较小的JPEG质量参数，减少带宽需求
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]  # 质量设为80%，平衡质量和大小
                (flag, encodedImage) = cv2.imencode(".jpg", processed_frame, encode_param)
                if not flag:
                    continue
                    
                # 以multipart格式产生输出帧
                yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                      bytearray(encodedImage) + b'\r\n')
        
        except (GeneratorExit, ConnectionAbortedError):
            print("客户端断开连接，正在清理视频流资源...")
        finally:
            print("释放摄像头和模型资源...")
            cap.release()

            # 显式删除模型实例以释放内存
            del object_model_stream
            del face_model_stream
            del pose_model_stream
            
            if violence_model:
                del violence_model
            if vgg_model:
                del vgg_model
            if image_model_transfer:
                del image_model_transfer
            
            # 对于TensorFlow模型，清理会话至关重要
            tf.keras.backend.clear_session()
            
            print("所有模型和摄像头资源已成功释放。")

    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def stop_video_feed_service():
    """停止摄像头视频流的服务函数"""
    global CAMERA_ACTIVE
    CAMERA_ACTIVE = False
    print("摄像头视频流已请求停止。")
    return True 