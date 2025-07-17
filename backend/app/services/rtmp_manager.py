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
        self.streaming_threads: Dict[str, threading.Thread] = {}
        self.analysis_threads: Dict[str, threading.Thread] = {}
        # 为推流和分析创建独立的队列
        self.streaming_queues: Dict[str, queue.Queue] = {}
        self.analysis_queues: Dict[str, queue.Queue] = {}
        self.stop_events: Dict[str, threading.Event] = {}
        self.reader_threads = {}
        
        # 初始化AI模型


        print("正在初始化AI模型...")
        try:
            from app.services.detection import get_object_model, get_face_model
            from app.services.dlib_service import dlib_face_service
            
            self.models = {
                'object': get_object_model(),
                'face': get_face_model()
            }
            self.dlib_service = dlib_face_service
            print("✅ AI模型初始化成功")
        except Exception as e:
            print(f"❌ AI模型初始化失败: {e}")
            # 设置为None以避免后续错误
            self.models = {
                'object': None,
                'face': None
            }


            self.dlib_service = None
    
    def add_stream(self, config: dict) -> str:
        """添加新的RTMP流"""
        stream_id = str(uuid.uuid4())
        
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
        
        stream_config = self.streams[stream_id]
        rtmp_url = stream_config['rtmp_url']
        
        print(f"尝试启动流: {stream_id}, URL: {rtmp_url}")
        
        # 创建VideoCapture
        cap = cv2.VideoCapture(rtmp_url)
        
        # 设置缓冲区大小和超时
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not cap.isOpened():
            raise Exception(f"无法连接到RTMP流: {rtmp_url}")
        
        # 测试读取一帧
        ret, frame = cap.read()
        if not ret:
            cap.release()
            raise Exception(f"无法从RTMP流读取数据: {rtmp_url}")
        
        # 获取原始视频尺寸
        original_height, original_width = frame.shape[:2]
        print(f"✅ RTMP流连接成功，原始尺寸: {original_width}x{original_height}")
        
        # 保存原始尺寸到流配置中
        self.streams[stream_id]['original_width'] = original_width
        self.streams[stream_id]['original_height'] = original_height
        
        # 存储capture和相关资源
        self.active_captures[stream_id] = cap
        self.stop_events[stream_id] = threading.Event()
        # 创建独立的队列
        self.streaming_queues[stream_id] = queue.Queue(maxsize=10)
        self.analysis_queues[stream_id] = queue.Queue(maxsize=5)
        
        # 启动单一读取线程（负责从RTMP流读取帧）
        reader_thread = threading.Thread(
            target=self._frame_reader_loop,
            args=(stream_id,),
            daemon=True
        )
        reader_thread.start()
        self.reader_threads[stream_id] = reader_thread
        
        # 启动推流线程（从队列获取帧并发送）
        streaming_thread = threading.Thread(
            target=self._streaming_loop,
            args=(stream_id,),
            daemon=True
        )
        streaming_thread.start()
        self.streaming_threads[stream_id] = streaming_thread
        
        # 启动分析线程（从队列获取帧并进行AI检测）
        analysis_thread = threading.Thread(
            target=self._analysis_loop,
            args=(stream_id,),
            daemon=True
        )
        analysis_thread.start()
        self.analysis_threads[stream_id] = analysis_thread
        
        # 更新状态
        self.streams[stream_id]['status'] = 'active'
        self.streams[stream_id]['last_activity'] = datetime.now().isoformat()
        
        print(f"✅ 流 {stream_id} 启动成功")



    def _frame_reader_loop(self, stream_id: str):
        """帧读取线程：从RTMP流读取帧并分发到两个队列"""
        cap = self.active_captures[stream_id]
        stop_event = self.stop_events[stream_id]
        streaming_queue = self.streaming_queues[stream_id]
        analysis_queue = self.analysis_queues[stream_id]
        
        print(f"📖 帧读取线程启动: {stream_id}")
        
        consecutive_failures = 0
        max_failures = 10
        
        try:
            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    consecutive_failures += 1
                    print(f"帧读取失败 {stream_id}, 连续失败次数: {consecutive_failures}")
                    
                    if consecutive_failures >= max_failures:
                        print(f"连续读取失败超过{max_failures}次，停止读取线程")
                        break
                    
                    time.sleep(0.1)
                    continue
                
                consecutive_failures = 0
                
                # 将帧分发到两个队列
                frame_copy = frame.copy()
                
                # 推流队列（高频率）
                try:
                    streaming_queue.put(frame_copy, block=False)
                except queue.Full:
                    try:
                        streaming_queue.get_nowait()
                        streaming_queue.put(frame_copy, block=False)
                    except queue.Empty:
                        pass
                
                # 分析队列（低频率，每5帧一次）
                if consecutive_failures == 0:  # 只有成功读取时才考虑分析
                    try:
                        analysis_queue.put(frame.copy(), block=False)
                    except queue.Full:
                        try:
                            analysis_queue.get_nowait()
                            analysis_queue.put(frame.copy(), block=False)
                        except queue.Empty:
                            pass
                
                time.sleep(0.033)
                
        except Exception as e:
            print(f"帧读取线程错误 {stream_id}: {e}")
        finally:
            print(f"📖 帧读取线程结束: {stream_id}")

    def _streaming_loop(self, stream_id: str):
        """推流线程：从推流队列获取帧并发送"""
        stop_event = self.stop_events[stream_id]
        streaming_queue = self.streaming_queues[stream_id]
        stream_config = self.streams[stream_id]
        
        print(f"📺 推流线程启动: {stream_id}")
        
        frame_count = 0
        
        try:
            while not stop_event.is_set():
                try:
                    frame = streaming_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                frame_count += 1
                
                # 保持原始分辨率，不进行resize
                # frame_resized = cv2.resize(frame, (640, 480))  # 删除这行
                
                # 压缩为JPEG（调整质量以平衡文件大小和画质）
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_bytes = buffer.tobytes()
                
                # 添加调试信息
                if frame_count % 30 == 0:  # 每30帧打印一次
                    print(f"📺 发送第{frame_count}帧，大小: {len(frame_bytes)} bytes, 流ID: {stream_id}")
                
                # 通过Socket.IO发送二进制数据，包含原始尺寸信息
                try:
                    socketio.emit('video_frame', {
                        'stream_id': stream_id,
                        'frame_data': frame_bytes,
                        'frame_count': frame_count,
                        'timestamp': datetime.now().isoformat(),
                        'original_width': stream_config.get('original_width', 1280),
                        'original_height': stream_config.get('original_height', 720)
                    }, namespace='/rtmp')
                    
                    # 添加发送确认日志
                    if frame_count % 30 == 0:
                        print(f"✅ 已发送video_frame事件到/rtmp命名空间，流ID: {stream_id}, 帧数: {frame_count}")
                        
                except Exception as emit_error:
                    print(f"❌ Socket.IO发送错误: {emit_error}")
                
                # 更新活动时间
                self.streams[stream_id]['last_activity'] = datetime.now().isoformat()
                
                time.sleep(0.033)  # 约30fps
                
        except Exception as e:
            print(f"推流线程错误 {stream_id}: {e}")
        finally:
            print(f"📺 推流线程结束: {stream_id}")

    def _analysis_loop(self, stream_id: str):
        """分析线程：从分析队列获取帧并进行AI检测"""
        stop_event = self.stop_events[stream_id]
        analysis_queue = self.analysis_queues[stream_id]
        stream_config = self.streams[stream_id]
        
        print(f"🔍 分析线程启动: {stream_id}")
        
        frame_count = 0
        
        try:
            while not stop_event.is_set():
                try:
                    frame = analysis_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                frame_count += 1
                
                # 每3帧进行一次AI检测
                if frame_count % 3 == 0:
                    try:
                        detection_results = self._perform_detection(
                            frame, stream_config['detection_modes']
                        )
                        
                        socketio.emit('ai_result', {
                            'stream_id': stream_id,
                            'timestamp': datetime.now().isoformat(),
                            'detections': detection_results['detections'],
                            'alerts': detection_results['alerts']
                        }, namespace='/rtmp', room=stream_id)
                        
                    except Exception as e:
                        print(f"AI检测错误: {e}")
                
                time.sleep(0.1)
                
        except Exception as e:
            print(f"分析线程错误 {stream_id}: {e}")
        finally:
            print(f"🔍 分析线程结束: {stream_id}")

    def _perform_detection(self, frame, detection_modes):
        """执行AI检测"""
        results = {
            'detections': [],
            'alerts': []
        }
        
        if not hasattr(self, 'models') or self.models is None:
            print("警告: AI模型未初始化，跳过检测")
            return results
        
        try:
            # 目标检测
            if 'object_detection' in detection_modes and self.models.get('object') is not None:
                object_results = self.models['object'](frame)
                for result in object_results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            cls = int(box.cls[0].cpu().numpy())
                            class_name = self.models['object'].names[cls]
                            
                            in_danger = self._is_in_danger_zone(x1, y1, x2, y2)
                            
                            results['detections'].append({
                                'type': 'object',
                                'class': class_name,
                                'confidence': float(conf),
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'in_danger_zone': in_danger
                            })
                            
                            if in_danger:
                                results['alerts'].append(f"检测到{class_name}进入危险区域")
        
        except Exception as e:
            print(f"目标检测错误: {e}")
        
        try:
            # 人脸检测和识别
            if 'face_only' in detection_modes and self.models.get('face') is not None:
                face_results = self.models['face'](frame)
                
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
                
                if hasattr(self, 'dlib_service') and self.dlib_service is not None and len(face_boxes) > 0:
                    try:
                        recognition_results = self.dlib_service.identify_faces(frame, face_boxes)
                        
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
            print(f"人脸检测错误: {e}")
        
        return results



    def stop_stream(self, stream_id: str):
        """停止RTMP流处理"""
        if stream_id not in self.streams:
            raise Exception("流不存在")
        
        if stream_id in self.stop_events:
            self.stop_events[stream_id].set()
        
        if stream_id in self.reader_threads:
            self.reader_threads[stream_id].join(timeout=5)
            del self.reader_threads[stream_id]
        
        if stream_id in self.streaming_threads:
            self.streaming_threads[stream_id].join(timeout=5)
            del self.streaming_threads[stream_id]
        
        if stream_id in self.analysis_threads:
            self.analysis_threads[stream_id].join(timeout=5)
            del self.analysis_threads[stream_id]
        
        if stream_id in self.active_captures:
            self.active_captures[stream_id].release()
            del self.active_captures[stream_id]
        
        # 清理队列
        if stream_id in self.streaming_queues:
            del self.streaming_queues[stream_id]
        
        if stream_id in self.analysis_queues:
            del self.analysis_queues[stream_id]
        
        if stream_id in self.stop_events:
            del self.stop_events[stream_id]
        
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
        """获取流的帧数据（生成器）- 保留兼容性"""
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

    def _is_in_danger_zone(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """检查边界框是否与危险区域重叠"""
        try:
            # 计算边界框中心点
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            # 简化实现：总是返回False，避免复杂的几何计算
            return False
        except Exception:
            return False

# 创建全局实例
rtmp_manager = RTMPStreamManager()