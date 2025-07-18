import cv2
import threading
import queue
import time
import uuid
import numpy as np  # 添加numpy导入
from typing import List, Dict, Optional
from threading import Event
from datetime import datetime
from app import socketio
from app.services.danger_zone import DANGER_ZONE
from ultralytics import YOLO
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
        
        # 添加姿态历史追踪
        self.pose_history = {}  # 用于存储每个人的姿态历史
        
        # 初始化AI模型
        print("正在初始化AI模型...")
        try:
            from app.services.detection import get_object_model, get_face_model, get_pose_model
            from app.services.dlib_service import dlib_face_service
            
            self.models = {
                'object': get_object_model(),
                'face': get_face_model(),
                'pose': get_pose_model()  # 添加姿态模型
            }
            self.dlib_service = dlib_face_service
            print("✅ AI模型初始化成功")
        except Exception as e:
            print(f"❌ AI模型初始化失败: {e}")
            # 设置为None以避免后续错误
            self.models = {
                'object': None,
                'face': None,
                'pose': None  # 添加姿态模型
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
        results = {'detections': [], 'alerts': []}
        
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
                            
                            if conf > 0.5:
                                class_name = self.models['object'].names[cls]
                                results['detections'].append({
                                    'type': 'object',
                                    'class': class_name,
                                    'confidence': float(conf),
                                    'bbox': [int(x1), int(y1), int(x2), int(y2)]
                                })
                                
                                if self._is_in_danger_zone(x1, y1, x2, y2):
                                    results['alerts'].append(f'检测到{class_name}进入危险区域！')
            
            # 人脸检测和识别
            if 'face_only' in detection_modes and self.models.get('face') is not None:
                face_results = self.models['face'](frame)
                for result in face_results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            
                            if conf > 0.5:
                                results['detections'].append({
                                    'type': 'face',
                                    'confidence': float(conf),
                                    'bbox': [int(x1), int(y1), int(x2), int(y2)]
                                })
                                
                                if 'face_only' in detection_modes:
                                    if self.dlib_service:
                                        face_crop = frame[int(y1):int(y2), int(x1):int(x2)]
                                        # 修复：使用正确的方法名和参数格式
                                        face_boxes = [[int(x1), int(y1), int(x2), int(y2)]]
                                        recognition_results = self.dlib_service.identify_faces(frame, face_boxes)
                                        if recognition_results and len(recognition_results) > 0:
                                            name, bbox = recognition_results[0]
                                            if name != "Unknown":
                                                results['detections'][-1]['name'] = name
                                            else:
                                                results['detections'][-1]['name'] = "stranger"
            
            # 跌倒检测部分修复
            if 'fall_detection' in detection_modes and self.models.get('pose') is not None:
                try:
                    # 进行姿态估计
                    pose_results = self.models['pose'](frame)
                    
                    if pose_results and len(pose_results) > 0:
                        # 绘制姿态关键点和骨架
                        annotated_frame = pose_results[0].plot()  # 添加这行来绘制可视化
                        
                        for result in pose_results:
                            if result.keypoints is not None:
                                keypoints = result.keypoints.data.cpu().numpy()
                                
                                for person_keypoints in keypoints:
                                    # 计算边界框
                                    bbox = self._get_pose_bbox(person_keypoints)
                                    
                                    # 跌倒检测逻辑
                                    fall_detected, confidence = self._detect_fall(person_keypoints)
                                    
                                    if fall_detected:
                                        results['detections'].append({
                                            'type': 'fall',
                                            'confidence': confidence,
                                            'bbox': bbox,
                                            'keypoints': person_keypoints.tolist(),  # 添加关键点数据
                                            'message': '检测到跌倒！'
                                        })
                                        results['alerts'].append('检测到跌倒行为！')
                                    else:
                                        # 即使没有跌倒也返回姿态数据用于可视化
                                        results['detections'].append({
                                            'type': 'pose',
                                            'confidence': 0.8,
                                            'bbox': bbox,
                                            'keypoints': person_keypoints.tolist(),
                                            'message': '正常姿态'
                                        })
                
                except Exception as e:
                    print(f"跌倒检测错误: {e}")
                
                return results
            results['detections'].extend(fall_results['detections'])
            results['alerts'].extend(fall_results['alerts'])
            
        except Exception as e:
            print(f"AI检测错误: {e}")
        
        return results
    
    def _process_smoking_detection(self, frame):
        """处理抽烟检测 - 增强版"""
        results = {'detections': [], 'alerts': []}
        
        try:
            # 方法1：使用专用抽烟检测模型
            if hasattr(self, 'smoking_model') and self.smoking_model is not None:
                smoking_results = self.smoking_model(frame)
                
                for result in smoking_results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            cls = int(box.cls[0].cpu().numpy())
                            
                            if conf > 0.5:  # 置信度阈值
                                results['detections'].append({
                                    'type': 'smoking',
                                    'confidence': float(conf),
                                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                    'message': '检测到吸烟行为'
                                })
                                results['alerts'].append('检测到吸烟行为！')
                            
            # 方法2：备用检测 - 使用目标检测模型检测香烟相关物体
            elif self.models.get('object') is not None:
                object_results = self.models['object'](frame)
                
                # 定义与吸烟相关的类别（根据COCO数据集）
                smoking_related_classes = ['person']  # 可以扩展为包含香烟、打火机等
                
                for result in object_results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            cls = int(box.cls[0].cpu().numpy())
                            class_name = self.models['object'].names[cls]
                            
                            if conf > 0.6 and class_name in smoking_related_classes:
                                # 提取人物区域进行进一步分析
                                person_crop = frame[int(y1):int(y2), int(x1):int(x2)]
                                
                                # 简单的启发式检测（可以用更复杂的算法替换）
                                if self._detect_smoking_heuristic(person_crop):
                                    results['detections'].append({
                                        'type': 'smoking_suspected',
                                        'confidence': float(conf * 0.7),  # 降低置信度
                                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                        'message': '疑似吸烟行为'
                                    })
                                    results['alerts'].append('疑似检测到吸烟行为！')
        
        except:
            pass
        
        return results
    
    def _detect_smoking_heuristic(self, person_crop):
        """简单的启发式吸烟检测"""
        try:
            # 这里可以实现简单的图像处理逻辑
            # 例如：检测手部区域的亮点、烟雾模糊等
            # 目前返回随机结果作为示例
            import random
            return random.random() > 0.8  # 20%的概率检测为吸烟
        except:
            return False
    
    def _process_violence_detection(self, frame):
        """处理暴力检测"""
        results = {'detections': [], 'alerts': []}
        
        try:
            # 这里可以实现暴力检测逻辑
            # 目前返回空结果作为示例
            return results
        except Exception as e:
            print(f"暴力检测错误: {e}")
            return results
    
    def _predict_violence(self, frame_sequence):
        """预测暴力行为"""
        try:
            if not hasattr(self, 'violence_model') or self.violence_model is None or not hasattr(self, 'image_model_transfer') or self.image_model_transfer is None:
                return 0.0
                
            import tensorflow as tf
            import numpy as np
            
            # 将帧序列转换为模型输入格式
            frames = np.array(frame_sequence)
            
            # 使用VGG16提取特征
            features = []
            for frame in frames:
                # 调整帧大小为VGG16输入要求
                resized_frame = tf.image.resize(frame, [224, 224])
                resized_frame = tf.expand_dims(resized_frame, 0)
                feature = self.image_model_transfer.predict(resized_frame, verbose=0)
                features.append(feature[0])
            
            # 转换为模型输入格式
            features = np.array(features)
            features = np.expand_dims(features, 0)
            
            # 预测暴力概率
            prediction = self.violence_model.predict(features, verbose=0)
            violence_prob = prediction[0][1] if len(prediction[0]) > 1 else prediction[0][0]
            
            return float(violence_prob)
            
        except Exception as e:
            print(f"暴力预测错误: {e}")
            return 0.0
    
    def _get_pose_bbox(self, keypoints):
        """从关键点计算边界框"""
        try:
            # 过滤有效关键点（坐标大于0）
            valid_points = keypoints[keypoints[:, 0] > 0]
            
            if len(valid_points) == 0:
                return [0, 0, 100, 100]  # 默认边界框
            
            # 计算边界框
            x_min = int(np.min(valid_points[:, 0]))
            y_min = int(np.min(valid_points[:, 1]))
            x_max = int(np.max(valid_points[:, 0]))
            y_max = int(np.max(valid_points[:, 1]))
            
            # 添加一些边距
            margin = 10
            x_min = max(0, x_min - margin)
            y_min = max(0, y_min - margin)
            x_max += margin
            y_max += margin
            
            return [x_min, y_min, x_max, y_max]
            
        except Exception as e:
            print(f"计算姿态边界框错误: {e}")
            return [0, 0, 100, 100]
    
    def _is_in_danger_zone(self, x1, y1, x2, y2):
        """检查是否在危险区域内"""
        try:
            # 这里可以实现危险区域检测逻辑
            # 目前返回False作为示例
            return False
        except Exception as e:
            print(f"危险区域检测错误: {e}")
            return False
    
    def _detect_fall(self, keypoints):
        """检测跌倒行为"""
        try:
            import numpy as np
            
            # 过滤有效关键点（置信度 > 0.5）
            valid_keypoints = []
            for i, kp in enumerate(keypoints):
                if len(kp) >= 3 and kp[2] > 0.5:  # 置信度阈值
                    valid_keypoints.append([kp[0], kp[1], i])  # [x, y, keypoint_index]
            
            if len(valid_keypoints) < 5:  # 需要足够的关键点
                return False, 0.0
            
            # 转换为numpy数组便于计算
            points = np.array([[kp[0], kp[1]] for kp in valid_keypoints])
            
            # 计算人体边界框
            x_min, y_min = np.min(points, axis=0)
            x_max, y_max = np.max(points, axis=0)
            
            # 计算宽高比
            width = x_max - x_min
            height = y_max - y_min
            
            if height == 0:
                return False, 0.0
                
            aspect_ratio = width / height
            
            # 跌倒判断逻辑
            fall_confidence = 0.0
            
            # 1. 宽高比检测（跌倒时人体更宽）
            if aspect_ratio > 1.2:  # 宽度大于高度
                fall_confidence += 0.4
            
            # 2. 头部位置检测（如果能检测到头部和躯干）
            head_points = [kp for kp in valid_keypoints if kp[2] in [0, 1, 2, 3, 4]]  # 头部关键点
            body_points = [kp for kp in valid_keypoints if kp[2] in [5, 6, 11, 12]]  # 躯干关键点
            
            if head_points and body_points:
                head_y = np.mean([kp[1] for kp in head_points])
                body_y = np.mean([kp[1] for kp in body_points])
                
                # 头部应该在躯干上方，如果不是可能跌倒了
                if abs(head_y - body_y) < height * 0.3:  # 头部和躯干在同一水平线
                    fall_confidence += 0.3
            
            # 3. 整体姿态角度检测
            if len(points) >= 2:
                # 计算主轴角度
                center = np.mean(points, axis=0)
                centered_points = points - center
                
                # 使用PCA计算主方向
                cov_matrix = np.cov(centered_points.T)
                eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
                
                # 主方向向量
                main_direction = eigenvectors[:, -1]
                
                # 计算与垂直方向的角度
                vertical = np.array([0, 1])
                angle = np.arccos(np.abs(np.dot(main_direction, vertical)))
                angle_degrees = np.degrees(angle)
                
                # 如果角度大于45度，可能是跌倒
                if angle_degrees > 45:
                    fall_confidence += 0.3
            
            # 判断是否跌倒
            is_fall = fall_confidence > 0.6
            
            return is_fall, min(fall_confidence, 1.0)
            
        except Exception as e:
            print(f"跌倒检测错误: {e}")
            return False, 0.0

    def stop_stream(self, stream_id: str):
        """停止RTMP流处理"""
        if stream_id not in self.streams:
            raise Exception("流不存在")
        
        print(f"正在停止流: {stream_id}")
        
        # 设置停止事件
        if stream_id in self.stop_events:
            self.stop_events[stream_id].set()
        
        # 等待线程结束
        if stream_id in self.reader_threads:
            self.reader_threads[stream_id].join(timeout=5)
            del self.reader_threads[stream_id]
        
        if stream_id in self.streaming_threads:
            self.streaming_threads[stream_id].join(timeout=5)
            del self.streaming_threads[stream_id]
        
        if stream_id in self.analysis_threads:
            self.analysis_threads[stream_id].join(timeout=5)
            del self.analysis_threads[stream_id]
        
        # 释放资源
        if stream_id in self.active_captures:
            self.active_captures[stream_id].release()
            del self.active_captures[stream_id]
        
        # 清理队列和事件
        if stream_id in self.streaming_queues:
            del self.streaming_queues[stream_id]
        
        if stream_id in self.analysis_queues:
            del self.analysis_queues[stream_id]
        
        if stream_id in self.stop_events:
            del self.stop_events[stream_id]
        
        # 更新状态
        self.streams[stream_id]['status'] = 'inactive'
        
        print(f"✅ 流 {stream_id} 已停止")
    
    def get_stream_status(self, stream_id: str) -> dict:
        """获取流状态"""
        if stream_id not in self.streams:
            raise Exception("流不存在")
        
        return self.streams[stream_id]
    
    def list_streams(self) -> List[dict]:
        """列出所有流"""
        return list(self.streams.values())
    
    def remove_stream(self, stream_id: str):
        """移除流"""
        if stream_id not in self.streams:
            raise Exception("流不存在")
        
        # 如果流正在运行，先停止它
        if self.streams[stream_id]['status'] == 'active':
            self.stop_stream(stream_id)
        
        # 删除流配置
        del self.streams[stream_id]
        
        print(f"✅ 流 {stream_id} 已移除")
    
    def get_all_streams(self) -> List[dict]:
        """获取所有流（兼容方法）"""
        return self.list_streams()
    
    def delete_stream(self, stream_id: str):
        """删除流（兼容方法）"""
        return self.remove_stream(stream_id)
    
    def get_stream_frames(self, stream_id: str):
        """获取流帧数据（用于HTTP流）"""
        # 这个方法用于HTTP视频流，RTMP流使用Socket.IO
        # 可以返回空生成器或抛出异常
        raise Exception("RTMP流使用Socket.IO传输，不支持HTTP流")
    
    # 创建全局实例（移到类定义外部）
rtmp_manager = RTMPStreamManager()