import cv2
import uuid
import threading
import time
import queue
import os
from datetime import datetime
from typing import Dict, List, Optional
from app import socketio
from app.services.danger_zone import DANGER_ZONE
from ultralytics import YOLO
import numpy as np
import base64

class RTMPStreamManager:
    def __init__(self):
        self.streams: Dict[str, dict] = {}
        self.active_captures: Dict[str, cv2.VideoCapture] = {}
        self.processing_threads: Dict[str, threading.Thread] = {}
        self.frame_queues: Dict[str, queue.Queue] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        
        # 初始化AI模型
        try:
            from ultralytics import YOLO
            from app.services.dlib_service import dlib_face_service
            
            # 模型路径
            BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            MODEL_DIR = os.path.join(BASE_PATH, 'yolo-Weights')
            
            print(f"模型目录: {MODEL_DIR}")
            
            # 加载模型
            self.models = {
                'object': None,
                'face': None,
                'pose': None
            }
            
            # 尝试加载目标检测模型
            object_model_path = os.path.join(MODEL_DIR, "yolov8n.pt")
            if os.path.exists(object_model_path):
                self.models['object'] = YOLO(object_model_path)
                print("✅ 目标检测模型加载成功")
            else:
                print(f"❌ 目标检测模型文件不存在: {object_model_path}")
            
            # 尝试加载人脸检测模型
            face_model_path = os.path.join(MODEL_DIR, "yolov8n-face-lindevs.pt")
            if os.path.exists(face_model_path):
                self.models['face'] = YOLO(face_model_path)
                print("✅ 人脸检测模型加载成功")
            else:
                print(f"❌ 人脸检测模型文件不存在: {face_model_path}")
            
            # 初始化Dlib服务
            self.dlib_service = dlib_face_service
            print("✅ RTMP AI模型加载成功")
            
        except Exception as e:
            print(f"❌ RTMP AI模型加载失败: {e}")
            self.models = {'object': None, 'face': None, 'pose': None}
            self.dlib_service = None
    
    def add_stream(self, config: dict) -> str:
        """添加新的RTMP流"""
        stream_id = str(uuid.uuid4())
        
        # 移除RTMP URL验证，因为RTMP流可能需要时间建立连接
        # 直接保存流配置，在启动时再验证
        
        # 保存流配置
        self.streams[stream_id] = {
            'stream_id': stream_id,
            'name': config['name'],
            'rtmp_url': config['rtmp_url'],
            'description': config.get('description', ''),
            'detection_modes': config.get('detection_modes', ['object_detection']),
            'status': 'inactive',
            'created_at': datetime.now().isoformat(),
            'last_activity': None
        }
        
        return stream_id

    def start_stream(self, stream_id: str):
        """启动RTMP流处理"""
        if stream_id not in self.streams:
            raise Exception("流不存在")
        
        if stream_id in self.active_captures:
            raise Exception("流已经在运行")
        
        stream_config = self.streams[stream_id]
        print(f"尝试启动流: {stream_id}, URL: {stream_config['rtmp_url']}")
        
        # 创建视频捕获对象，添加RTMP优化配置
        try:
            cap = cv2.VideoCapture(stream_config['rtmp_url'])
            
            # 设置RTMP流的优化参数
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲区大小，降低延迟
            cap.set(cv2.CAP_PROP_FPS, 30)  # 设置帧率
            
            # 尝试多次连接
            max_retries = 3
            for attempt in range(max_retries):
                if cap.isOpened():
                    # 测试读取一帧
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        print(f"✅ RTMP流连接成功，帧大小: {frame.shape}")
                        break
                    else:
                        print(f"⚠️ 连接尝试 {attempt + 1}/{max_retries}: 无法读取数据")
                else:
                    print(f"⚠️ 连接尝试 {attempt + 1}/{max_retries}: 无法打开流")
                
                if attempt < max_retries - 1:
                    cap.release()
                    time.sleep(2)  # 等待2秒后重试
                    cap = cv2.VideoCapture(stream_config['rtmp_url'])
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FPS, 30)
            else:
                # 所有重试都失败
                cap.release()
                raise Exception(f"经过{max_retries}次尝试，仍无法连接到RTMP流: {stream_config['rtmp_url']}")
                
        except Exception as e:
            print(f"❌ RTMP流连接失败: {e}")
            raise Exception(f"RTMP流连接失败: {str(e)}")
        
        # 设置VideoCapture的属性以减少延迟
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        
        self.active_captures[stream_id] = cap
        self.frame_queues[stream_id] = queue.Queue(maxsize=10)
        self.stop_events[stream_id] = threading.Event()
        
        # 启动处理线程
        thread = threading.Thread(
            target=self._process_stream,
            args=(stream_id,),
            daemon=True
        )
        thread.start()
        self.processing_threads[stream_id] = thread
        
        # 更新状态
        self.streams[stream_id]['status'] = 'active'
        self.streams[stream_id]['last_activity'] = datetime.now().isoformat()
        
        print(f"✅ 流 {stream_id} 启动成功")

    def stop_stream(self, stream_id: str):
        """停止RTMP流处理"""
        if stream_id not in self.streams:
            raise Exception("流不存在")
        
        # 设置停止事件
        if stream_id in self.stop_events:
            self.stop_events[stream_id].set()
        
        # 等待线程结束
        if stream_id in self.processing_threads:
            self.processing_threads[stream_id].join(timeout=5)
            del self.processing_threads[stream_id]
        
        # 释放资源
        if stream_id in self.active_captures:
            self.active_captures[stream_id].release()
            del self.active_captures[stream_id]
        
        if stream_id in self.frame_queues:
            del self.frame_queues[stream_id]
        
        if stream_id in self.stop_events:
            del self.stop_events[stream_id]
        
        # 更新状态
        self.streams[stream_id]['status'] = 'inactive'
    
    def delete_stream(self, stream_id: str):
        """删除RTMP流"""
        if stream_id not in self.streams:
            raise Exception("流不存在")
        
        # 先停止流
        if self.streams[stream_id]['status'] == 'active':
            self.stop_stream(stream_id)
        
        # 删除流配置
        del self.streams[stream_id]
    
    def get_all_streams(self) -> List[dict]:
        """获取所有流的信息"""
        return list(self.streams.values())
    
    def get_stream_frames(self, stream_id: str):
        """获取流的帧数据（生成器）"""
        if stream_id not in self.frame_queues:
            raise Exception("流未激活")
        
        frame_queue = self.frame_queues[stream_id]
        
        while stream_id in self.active_captures:
            try:
                # 从队列获取帧数据
                frame_data = frame_queue.get(timeout=1)
                yield frame_data
            except queue.Empty:
                continue
            except Exception as e:
                print(f"获取帧数据错误: {e}")
                break
    
    def _validate_rtmp_url(self, rtmp_url: str) -> bool:
        """验证RTMP URL的有效性"""
        try:
            cap = cv2.VideoCapture(rtmp_url)
            is_valid = cap.isOpened()
            cap.release()
            return is_valid
        except Exception:
            return False
    
    def _process_stream(self, stream_id: str):
        """处理单个RTMP流的主循环"""
        cap = self.active_captures[stream_id]
        frame_queue = self.frame_queues[stream_id]
        stop_event = self.stop_events[stream_id]
        stream_config = self.streams[stream_id]
        
        frame_count = 0
        last_detection_time = time.time()
        
        try:
            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    print(f"流 {stream_id} 读取帧失败")
                    break
                
                frame_count += 1
                current_time = time.time()
                
                # 创建用于显示的帧副本
                display_frame = frame.copy()
                
                # 每隔几帧进行一次AI检测
                if frame_count % 5 == 0:  # 每5帧检测一次
                    try:
                        # 执行AI检测
                        detection_results = self._perform_detection(
                            frame, stream_config['detection_modes']
                        )
                        
                        # 在显示帧上绘制检测结果
                        self._draw_detection_results(display_frame, detection_results, stream_config['detection_modes'])
                        
                        # 通过WebSocket发送检测结果
                        socketio.emit('detection_result', {
                            'stream_id': stream_id,
                            'timestamp': datetime.now().isoformat(),
                            'detections': detection_results['detections'],
                            'alerts': detection_results['alerts']
                        }, namespace='/rtmp', room=stream_id)
                        
                        last_detection_time = current_time
                        
                    except Exception as e:
                        print(f"检测处理错误: {e}")
                
                # 编码帧为JPEG（使用带检测结果的显示帧）
                try:
                    _, buffer = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    frame_data = buffer.tobytes()
                    
                    # 将帧数据放入队列
                    if not frame_queue.full():
                        frame_queue.put(frame_data)
                    else:
                        # 队列满时，移除旧帧
                        try:
                            frame_queue.get_nowait()
                            frame_queue.put(frame_data)
                        except queue.Empty:
                            pass
                            
                except Exception as e:
                    print(f"帧编码错误: {e}")
                
                # 更新活动时间
                self.streams[stream_id]['last_activity'] = datetime.now().isoformat()
                
                # 控制帧率
                time.sleep(0.033)  # 约30fps
                
        except Exception as e:
            print(f"流处理错误 {stream_id}: {e}")
        finally:
            # 更新流状态
            if stream_id in self.streams:
                self.streams[stream_id]['status'] = 'error'
    
    def _perform_detection(self, frame, detection_modes):
        """执行AI检测"""
        results = {
            'detections': [],
            'alerts': []
        }
        
        try:
            # 目标检测
            if 'object_detection' in detection_modes and self.models['object'] is not None:
                object_results = self.models['object'].track(frame, persist=True)  # 使用track而不是predict
                for result in object_results:
                    boxes = result.boxes
                    if boxes is not None and hasattr(boxes, 'id') and boxes.id is not None:
                        # 处理有追踪ID的检测结果
                        for i, box in enumerate(boxes):
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            cls = int(box.cls[0].cpu().numpy())
                            track_id = int(boxes.id[i].cpu().numpy())
                            class_name = self.models['object'].names[cls]
                            
                            # 只处理人员检测（class 0）
                            if cls == 0:  # person class
                                # 计算目标的底部中心点
                                foot_point = (int((x1 + x2) / 2), int(y2))
                                
                                # 检查是否在危险区域内
                                in_danger_zone = self._is_in_danger_zone_advanced(foot_point)
                                
                                # 计算到危险区域的距离
                                distance = self._calculate_distance_to_danger_zone(foot_point)
                                
                                # 确定告警状态
                                alert_status = None
                                color_status = 'green'  # 默认绿色
                                
                                if in_danger_zone:
                                    # 更新停留时间
                                    loitering_time = update_loitering_time(track_id, 0.2)  # 假设每次检测间隔0.2秒
                                    
                                    if loitering_time >= danger_zone_service.LOITERING_THRESHOLD:
                                        color_status = 'red'
                                        alert_status = f"人员 ID:{track_id} 在危险区域停留 {loitering_time:.1f} 秒"
                                        results['alerts'].append(alert_status)
                                        
                                        # 添加告警
                                        add_alert(alert_status,
                                                 event_type="danger_zone_intrusion",
                                                 details=f"人员在危险区域停留 {loitering_time:.1f} 秒")
                                    else:
                                        color_status = 'orange'
                                else:
                                    # 重置停留时间
                                    reset_loitering_time(track_id)
                                    
                                    # 检查是否接近危险区域
                                    if distance < danger_zone_service.SAFETY_DISTANCE:
                                        color_status = 'yellow'
                                        alert_status = f"人员 ID:{track_id} 过于接近危险区域，距离 {distance:.1f} 像素"
                                        results['alerts'].append(alert_status)
                                        
                                        # 添加告警
                                        add_alert(alert_status,
                                                 event_type="proximity_warning",
                                                 details=f"人员过于接近危险区域，距离 {distance:.1f} 像素")
                                
                                results['detections'].append({
                                    'type': 'object',
                                    'class': class_name,
                                    'confidence': float(conf),
                                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                    'track_id': track_id,
                                    'in_danger_zone': in_danger_zone,
                                    'distance_to_danger': distance,
                                    'color_status': color_status,
                                    'loitering_time': get_loitering_time(track_id) if in_danger_zone else 0
                                })
            
            # 人脸检测和识别（保持原有逻辑）
            if 'face_only' in detection_modes and self.models['face'] is not None:
                face_results = self.models['face'](frame)
                
                # 收集所有检测到的人脸边界框
                face_boxes = []
                face_confidences = []
                
                for result in face_results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            face_boxes.append([int(x1), int(y1), int(x2), int(y2)])
                            face_confidences.append(float(conf))
                
                # 使用Dlib服务进行人脸识别
                if self.dlib_service is not None and len(face_boxes) > 0:
                    try:
                        # 调用正确的方法名和参数格式
                        recognition_results = self.dlib_service.identify_faces(frame, face_boxes)
                        
                        # 处理识别结果
                        for i, (name, box) in enumerate(recognition_results):
                            x1, y1, x2, y2 = box
                            conf = face_confidences[i] if i < len(face_confidences) else 0.0
                            
                            results['detections'].append({
                                'type': 'face',
                                'name': name,
                                'confidence': conf,
                                'bbox': [int(x1), int(y1), int(x2), int(y2)]
                            })
                            
                            if name == "Unknown":
                                results['alerts'].append("检测到未知人脸")
                                
                    except Exception as e:
                        print(f"人脸识别错误: {e}")
                        # 如果识别失败，至少返回检测到的人脸框
                        for i, box in enumerate(face_boxes):
                            x1, y1, x2, y2 = box
                            conf = face_confidences[i] if i < len(face_confidences) else 0.0
                            
                            results['detections'].append({
                                'type': 'face',
                                'name': 'Unknown',
                                'confidence': conf,
                                'bbox': [int(x1), int(y1), int(x2), int(y2)]
                            })
                            
                            results['alerts'].append("人脸识别服务异常")
                                
        except Exception as e:
            print(f"检测执行错误: {e}")
        
        return results

    def _draw_detection_results(self, frame, detection_results, detection_modes):
        """在帧上绘制检测结果"""
        try:
            # 首先绘制危险区域
            self._draw_danger_zone(frame)
            
            for detection in detection_results['detections']:
                bbox = detection['bbox']
                x1, y1, x2, y2 = bbox
                
                if detection['type'] == 'object' and 'color_status' in detection:
                    # 根据状态设置颜色
                    color_map = {
                        'green': (0, 255, 0),
                        'yellow': (0, 255, 255),
                        'orange': (0, 165, 255),
                        'red': (0, 0, 255)
                    }
                    color = color_map.get(detection['color_status'], (0, 255, 0))
                    
                    # 根据危险程度调整边框粗细
                    thickness = 2
                    if detection['color_status'] == 'red':
                        thickness = 4
                    elif detection['color_status'] == 'orange':
                        thickness = 3
                    
                    # 绘制边框
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                    
                    # 准备标签文本
                    label = f"ID:{detection.get('track_id', 'N/A')} {detection['class']}"
                    if detection['in_danger_zone']:
                        label += f" 停留:{detection['loitering_time']:.1f}s"
                    elif detection['distance_to_danger'] < danger_zone_service.SAFETY_DISTANCE:
                        label += f" 距离:{detection['distance_to_danger']:.1f}px"
                    
                    # 绘制标签
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (x1, y1 - h - 10), (x1 + w, y1 - 5), color, -1)
                    cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    # 绘制底部中心点
                    foot_point = (int((x1 + x2) / 2), int(y2))
                    cv2.circle(frame, foot_point, 5, color, -1)
                    
                    # 如果接近但不在危险区域内，绘制连接线
                    if not detection['in_danger_zone'] and detection['distance_to_danger'] < danger_zone_service.SAFETY_DISTANCE * 2:
                        self._draw_distance_line(frame, foot_point, detection['distance_to_danger'])
                    
                    # 如果在危险区域且停留时间超过阈值，绘制警告标记
                    if detection['in_danger_zone'] and detection['loitering_time'] >= danger_zone_service.LOITERING_THRESHOLD:
                        self._draw_warning_triangle(frame, x1, y1, x2, y2)
                
                elif detection['type'] == 'face':
                    # 绘制人脸识别结果（保持原有逻辑）
                    name = detection['name']
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # 绘制姓名标签
                    label = name
                    (label_width, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    label_bg_height = 20
                    
                    if y1 - label_bg_height < 5:
                        cv2.rectangle(frame, (x1, y1), (x1 + label_width + 4, y1 + label_bg_height), color, -1)
                        cv2.putText(frame, label, (x1 + 2, y1 + label_bg_height - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    else:
                        cv2.rectangle(frame, (x1, y1 - label_bg_height), (x1 + label_width + 4, y1), color, -1)
                        cv2.putText(frame, label, (x1 + 2, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
        except Exception as e:
            print(f"绘制检测结果错误: {e}")
    
    def _draw_danger_zone(self, frame):
        """绘制危险区域"""
        try:
            if len(danger_zone_service.DANGER_ZONE) > 0:
                # 绘制危险区域多边形
                danger_zone_pts = np.array(danger_zone_service.DANGER_ZONE, dtype=np.int32).reshape((-1, 1, 2))
                
                # 绘制半透明填充
                overlay = frame.copy()
                cv2.fillPoly(overlay, [danger_zone_pts], (0, 0, 255))  # 红色填充
                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                
                # 绘制边界线
                cv2.polylines(frame, [danger_zone_pts], True, (0, 0, 255), 3)
                
                # 添加危险区域标签
                if len(danger_zone_service.DANGER_ZONE) > 0:
                    label_pos = tuple(danger_zone_service.DANGER_ZONE[0].astype(int))
                    cv2.putText(frame, "DANGER ZONE", label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        except Exception as e:
            print(f"绘制危险区域错误: {e}")
    
    def _draw_warning_triangle(self, frame, x1, y1, x2, y2):
        """绘制警告三角形"""
        try:
            triangle_height = 20
            triangle_base = 20
            triangle_center_x = int((x1 + x2) / 2)
            triangle_top_y = int(y1) - 25
            
            triangle_pts = np.array([
                [triangle_center_x - triangle_base//2, triangle_top_y + triangle_height],
                [triangle_center_x + triangle_base//2, triangle_top_y + triangle_height],
                [triangle_center_x, triangle_top_y]
            ], np.int32)
            
            cv2.fillPoly(frame, [triangle_pts], (0, 0, 255))  # 红色填充
            cv2.polylines(frame, [triangle_pts], True, (0, 0, 0), 1)  # 黑色边框
            
            # 在三角形中绘制感叹号
            cv2.putText(frame, "!", 
                        (triangle_center_x - 3, triangle_top_y + triangle_height - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        except Exception as e:
            print(f"绘制警告三角形错误: {e}")
    
    def _draw_distance_line(self, frame, foot_point, distance):
        """绘制到危险区域的距离线"""
        try:
            # 找到危险区域上最近的点
            min_dist = float('inf')
            closest_point = None
            
            for i in range(len(danger_zone_service.DANGER_ZONE)):
                p1 = danger_zone_service.DANGER_ZONE[i]
                p2 = danger_zone_service.DANGER_ZONE[(i + 1) % len(danger_zone_service.DANGER_ZONE)]
                
                # 计算点到线段的最近点
                line_vec = p2 - p1
                line_len = np.linalg.norm(line_vec)
                if line_len > 0:
                    line_unitvec = line_vec / line_len
                    
                    proj_length = np.dot(np.array(foot_point) - p1, line_unitvec)
                    proj_length = max(0, min(line_len, proj_length))
                    
                    closest_on_line = p1 + proj_length * line_unitvec
                    dist = np.linalg.norm(np.array(foot_point) - closest_on_line)
                    
                    if dist < min_dist:
                        min_dist = dist
                        closest_point = closest_on_line.astype(int)
            
            if closest_point is not None:
                # 绘制虚线
                cv2.line(frame, foot_point, tuple(closest_point), (255, 255, 0), 2)
                
                # 在线的中点显示距离
                mid_point = ((foot_point[0] + closest_point[0]) // 2, 
                           (foot_point[1] + closest_point[1]) // 2)
                cv2.putText(frame, f"{distance:.0f}px", mid_point, 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        except Exception as e:
            print(f"绘制距离线错误: {e}")
    
    def _is_in_danger_zone_advanced(self, point):
        """检查点是否在危险区域内（使用高级几何算法）"""
        try:
            if len(danger_zone_service.DANGER_ZONE) < 3:
                return False
            return point_in_polygon(point, danger_zone_service.DANGER_ZONE)
        except Exception as e:
            print(f"危险区域检测错误: {e}")
            return False
    
    def _calculate_distance_to_danger_zone(self, point):
        """计算点到危险区域的最小距离"""
        try:
            if len(danger_zone_service.DANGER_ZONE) < 3:
                return float('inf')
            return distance_to_polygon(point, danger_zone_service.DANGER_ZONE)
        except Exception as e:
            print(f"距离计算错误: {e}")
            return float('inf')
    
    def _is_in_danger_zone(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """检查边界框是否与危险区域重叠（保持向后兼容）"""
        try:
            # 计算边界框底部中心点
            foot_point = ((x1 + x2) / 2, y2)
            return self._is_in_danger_zone_advanced(foot_point)
        except Exception:
            return False

# 创建全局实例
rtmp_manager = RTMPStreamManager()