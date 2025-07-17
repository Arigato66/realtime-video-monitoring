import cv2
import base64
import time
import numpy as np
from celery import current_task
from app.celery_app import celery_app
# 移除这行循环导入
# from app.services.detection import process_frame_with_ai
from app import socketio
import json

@celery_app.task(bind=True)
def process_rtmp_stream(self, stream_id: str, stream_config: dict):
    """处理单路RTMP视频流的Celery任务"""
    
    rtmp_url = stream_config['rtmp_url']
    detection_modes = stream_config['detection_modes']
    
    # 初始化AI模型（每个任务独立的模型实例）
    from ultralytics import YOLO
    models = {
        'object': YOLO('yolo-Weights/yolov8n.pt'),
        'face': YOLO('yolo-Weights/yolov8n-face.pt'),
        'pose': YOLO('yolo-Weights/yolov8n-pose.pt')
    }
    
    # 打开RTMP流
    cap = cv2.VideoCapture(rtmp_url)
    if not cap.isOpened():
        raise Exception(f"无法打开RTMP流: {rtmp_url}")
    
    frame_count = 0
    fps_counter = 0
    start_time = time.time()
    
    try:
        while True:
            # 检查任务是否被撤销
            if self.is_aborted():
                break
                
            ret, frame = cap.read()
            if not ret:
                # 尝试重连
                cap.release()
                time.sleep(5)
                cap = cv2.VideoCapture(rtmp_url)
                continue
            
            frame_count += 1
            fps_counter += 1
            
            # 每秒处理一次AI分析（降低CPU负载）
            if frame_count % 30 == 0:
                # AI处理
                ai_results = process_frame_with_ai(
                    frame, models, detection_modes, stream_config.get('danger_zones', [])
                )
                
                # 转换帧为Base64
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # 计算FPS
                current_time = time.time()
                if current_time - start_time >= 1.0:
                    fps = fps_counter / (current_time - start_time)
                    fps_counter = 0
                    start_time = current_time
                else:
                    fps = 0
                
                # 通过WebSocket发送数据
                socketio.emit('stream_data', {
                    'stream_id': stream_id,
                    'frame': frame_base64,
                    'ai_results': ai_results,
                    'fps': fps,
                    'timestamp': time.time()
                }, namespace='/video')
            
            # 更新任务状态
            if frame_count % 300 == 0:  # 每10秒更新一次
                self.update_state(
                    state='PROGRESS',
                    meta={'frames_processed': frame_count, 'stream_id': stream_id}
                )
    
    except Exception as e:
        # 发送错误信息
        socketio.emit('stream_error', {
            'stream_id': stream_id,
            'error': str(e)
        }, namespace='/video')
        raise
    
    finally:
        cap.release()
        # 通知流已停止
        socketio.emit('stream_stopped', {
            'stream_id': stream_id
        }, namespace='/video')

def process_frame_with_ai(frame, models, detection_modes, danger_zones):
    """使用AI模型处理单帧图像"""
    results = {
        'detections': [],
        'alerts': [],
        'statistics': {}
    }
    
    for mode in detection_modes:
        if mode == 'object_detection':
            # 目标检测
            object_results = models['object'].predict(frame, verbose=False)
            for result in object_results:
                for box in result.boxes:
                    if box.conf > 0.5:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        
                        detection = {
                            'type': 'object',
                            'class': models['object'].names[cls],
                            'confidence': conf,
                            'bbox': [int(x1), int(y1), int(x2), int(y2)]
                        }
                        results['detections'].append(detection)
                        
                        # 检查危险区域
                        if check_danger_zone(detection['bbox'], danger_zones):
                            results['alerts'].append({
                                'type': 'danger_zone',
                                'message': f'{detection["class"]}进入危险区域',
                                'severity': 'high'
                            })
        
        elif mode == 'face_detection':
            # 人脸检测
            face_results = models['face'].predict(frame, verbose=False)
            face_count = 0
            for result in face_results:
                face_count += len(result.boxes) if result.boxes else 0
            
            results['statistics']['face_count'] = face_count
    
    return results

def check_danger_zone(bbox, danger_zones):
    """检查目标是否在危险区域内"""
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    
    for zone in danger_zones:
        if (zone['x1'] <= center_x <= zone['x2'] and 
            zone['y1'] <= center_y <= zone['y2']):
            return True
    return False