from flask import Blueprint, request, jsonify, Response
import cv2
import threading
import time
import numpy as np
from typing import Dict, List, Optional
from ultralytics import YOLO

# 导入检测相关模块
from app.services.detection import process_detection_results, get_model, process_faces_only
from app.services.alerts import update_detection_time
from app.services import system_state
from app.services.danger_zone import DANGER_ZONE

# 创建RTMP蓝图
rtmp_bp = Blueprint('rtmp', __name__, url_prefix='/api/rtmp')

# 全局变量存储RTMP流状态
rtmp_streams: Dict[int, dict] = {}
rtmp_active = False
stream_threads: Dict[int, threading.Thread] = {}
stream_frames: Dict[int, Optional[bytes]] = {}
stream_locks: Dict[int, threading.Lock] = {}

import subprocess
import queue

class RTMPStreamManager:
    """RTMP流管理器（OpenCV实现）"""
    
    def __init__(self):
        self.streams: Dict[int, dict] = {}
        self.threads: Dict[int, threading.Thread] = {}
        self.frames: Dict[int, Optional[bytes]] = {}
        self.locks: Dict[int, threading.Lock] = {}
        self.active = False
        # 检测相关状态
        self.face_recognition_caches: Dict[int, dict] = {}
        self.frame_counts: Dict[int, int] = {}
        # 初始化检测模型
        self.model = None
        self._init_detection_model()
    
    def _init_detection_model(self):
        """初始化YOLO检测模型"""
        try:
            self.model = get_model()
            print("YOLO模型初始化成功")
        except Exception as e:
            print(f"YOLO模型初始化失败: {e}")
            self.model = None
    
    def connect_streams(self, stream_urls: List[str]) -> List[dict]:
        """连接多个RTMP流（OpenCV实现）"""
        results = []
        self.disconnect_all()
        
        for i, url in enumerate(stream_urls):
            # 基本URL验证
            if not url or not isinstance(url, str):
                results.append({'index': i, 'connected': False, 'error': 'Invalid URL format'})
                continue
                
            # 检查URL格式（支持rtmp, rtsp, http等协议）
            url = url.strip()
            if not any(url.lower().startswith(proto) for proto in ['rtmp://', 'rtsp://', 'http://', 'https://']):
                results.append({'index': i, 'connected': False, 'error': f'Unsupported protocol. URL: {url}'})  
                continue
                
            try:
                print(f"尝试连接流 {i}: {url}")
                
                # 使用OpenCV连接RTMP流
                cap = cv2.VideoCapture(url)
                
                # 设置缓冲区大小，减少延迟
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # 尝试读取一帧来验证连接
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    cap.release()
                    results.append({'index': i, 'connected': False, 'error': 'Failed to read frame from stream'})
                    print(f"流 {i} 连接失败: 无法读取帧")
                    continue
                
                # 连接成功
                self.streams[i] = {
                    'url': url,
                    'capture': cap,
                    'connected': True,
                    'error': None
                }
                self.frames[i] = None
                self.locks[i] = threading.Lock()
                
                # 初始化检测相关状态
                self.face_recognition_caches[i] = {}
                self.frame_counts[i] = 0
                
                # 启动帧读取线程
                thread = threading.Thread(target=self._opencv_worker, args=(i,))
                thread.daemon = True
                thread.start()
                self.threads[i] = thread
                
                results.append({'index': i, 'connected': True, 'error': None})
                print(f"流 {i} 连接成功: {url}")
                
            except Exception as e:
                error_msg = str(e)
                results.append({'index': i, 'connected': False, 'error': error_msg})
                print(f"流 {i} 连接异常: {url}, 错误: {error_msg}")
        
        self.active = any(r['connected'] for r in results)
        connected_count = sum(1 for r in results if r['connected'])
        print(f"RTMP连接完成: {connected_count}/{len(stream_urls)} 个流连接成功")
        
        return results

    def _opencv_worker(self, stream_index: int):
        """OpenCV帧读取线程"""
        stream = self.streams.get(stream_index)
        if not stream:
            print(f"流 {stream_index} 不存在，工作线程退出")
            return
            
        cap = stream['capture']
        consecutive_failures = 0
        max_failures = 10  # 连续失败次数阈值
        
        print(f"流 {stream_index} 开始读取帧数据")
        
        while self.active and stream_index in self.streams:
            try:
                # 读取帧
                ret, frame = cap.read()
                
                if not ret or frame is None:
                    consecutive_failures += 1
                    print(f"流 {stream_index} 读取帧失败，连续失败次数: {consecutive_failures}")
                    if consecutive_failures >= max_failures:
                        print(f"流 {stream_index} 连续失败次数过多，断开连接")
                        break
                    time.sleep(0.1)
                    continue
                
                # 重置失败计数
                consecutive_failures = 0
                
                # 更新帧计数
                self.frame_counts[stream_index] += 1
                
                # 处理帧（包含检测逻辑）
                processed_frame = self._process_frame(frame, stream_index)
                _, buffer = cv2.imencode('.jpg', processed_frame)
                
                # 线程安全地更新帧数据
                if stream_index in self.locks:
                    with self.locks[stream_index]:
                        self.frames[stream_index] = buffer.tobytes()
                        
            except Exception as e:
                consecutive_failures += 1
                print(f"流 {stream_index} OpenCV工作线程错误: {e}, 连续失败次数: {consecutive_failures}")
                if consecutive_failures >= max_failures:
                    print(f"流 {stream_index} 连续失败次数过多，断开连接")
                    break
                time.sleep(0.1)
        
        # 清理工作
        print(f"流 {stream_index} 工作线程结束，开始清理")
        
        # 更新连接状态
        if stream_index in self.streams:
            self.streams[stream_index]['connected'] = False
            self.streams[stream_index]['error'] = 'Stream disconnected'
        
        # 释放OpenCV资源
        try:
            cap.release()
        except Exception as e:
            print(f"流 {stream_index} 释放OpenCV资源时出错: {e}")
        
        print(f"流 {stream_index} 清理完成")
    
    def _process_frame(self, frame, stream_index: int):
        """处理单个流的帧，包含完整的检测逻辑"""
        try:
            # 获取当前帧计数
            frame_count = self.frame_counts.get(stream_index, 0)
            
            # 计算时间差（用于徘徊检测）
            time_diff = update_detection_time()
            
            # 创建处理后的帧副本
            processed_frame = frame.copy()
            
            # 根据检测模式进行处理
            if system_state.DETECTION_MODE == 'object_detection':
                # YOLO目标检测模式
                if self.model is not None:
                    try:
                        # 执行目标追踪
                        results = self.model.track(frame, persist=True)
                        
                        # 绘制危险区域
                        if len(DANGER_ZONE) > 0:
                            overlay = processed_frame.copy()
                            danger_zone_pts = DANGER_ZONE.reshape((-1, 1, 2))
                            cv2.fillPoly(overlay, [danger_zone_pts], (0, 0, 255))
                            cv2.addWeighted(overlay, 0.4, processed_frame, 0.6, 0, processed_frame)
                            cv2.polylines(processed_frame, [danger_zone_pts], True, (0, 0, 255), 3)
                            
                            # 在危险区域中添加文字
                            danger_zone_center = np.mean(DANGER_ZONE, axis=0, dtype=np.int32)
                            cv2.putText(processed_frame, "Danger Zone", 
                                        (danger_zone_center[0] - 60, danger_zone_center[1]),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
                        
                        # 处理检测结果
                        process_detection_results(results, processed_frame, time_diff, frame_count)
                        
                    except Exception as e:
                        print(f"YOLO检测错误 (流 {stream_index}): {e}")
                        
            elif system_state.DETECTION_MODE == 'face_only':
                # 纯人脸识别模式
                try:
                    face_cache = self.face_recognition_caches.get(stream_index, {})
                    process_faces_only(processed_frame, frame_count, face_cache)
                    self.face_recognition_caches[stream_index] = face_cache
                except Exception as e:
                    print(f"人脸识别错误 (流 {stream_index}): {e}")
            
            # 添加流标识和检测模式信息
            cv2.putText(processed_frame, f'Stream {stream_index + 1}', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            mode_text = "Object Detection" if system_state.DETECTION_MODE == 'object_detection' else "Face Recognition"
            cv2.putText(processed_frame, mode_text, 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # 添加帧计数信息
            cv2.putText(processed_frame, f'Frame: {frame_count}', 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            return processed_frame
            
        except Exception as e:
            print(f"帧处理错误 (流 {stream_index}): {e}")
            # 发生错误时返回原始帧
            cv2.putText(frame, f'Stream {stream_index + 1} (Error)', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return frame
    
    def get_stream_frame(self, stream_index: int) -> Optional[bytes]:
        """获取指定流的当前帧"""
        if stream_index in self.frames and stream_index in self.locks:
            with self.locks[stream_index]:
                return self.frames[stream_index]
        return None
    
    def disconnect_all(self):
        self.active = False
        for thread in self.threads.values():
            if thread.is_alive():
                thread.join(timeout=2)
        for stream in self.streams.values():
            if 'capture' in stream and stream['capture']:
                try:
                    stream['capture'].release()
                except:
                    pass
        self.streams.clear()
        self.threads.clear()
        self.frames.clear()
        self.locks.clear()
        # 清理检测相关缓存
        self.face_recognition_caches.clear()
        self.frame_counts.clear()
        print("所有RTMP流已断开，检测缓存已清理")

# 全局流管理器实例
stream_manager = RTMPStreamManager()

@rtmp_bp.route('/connect', methods=['POST'])
def connect_rtmp_streams():
    """连接RTMP流端点
    ---
    tags:
      - RTMP流管理
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            streams:
              type: array
              items:
                type: string
              description: RTMP流URL列表
    responses:
      200:
        description: 连接结果
        schema:
          type: object
          properties:
            status:
              type: string
            results:
              type: array
              items:
                type: object
                properties:
                  index:
                    type: integer
                  connected:
                    type: boolean
                  error:
                    type: string
    """
    try:
        data = request.get_json()
        stream_urls = data.get('streams', [])
        
        if not stream_urls:
            return jsonify({
                'status': 'error',
                'message': '未提供RTMP流URL'
            }), 400
        
        results = stream_manager.connect_streams(stream_urls)
        
        return jsonify({
            'status': 'success',
            'message': f'处理了 {len(stream_urls)} 个流',
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'连接RTMP流失败: {str(e)}'
        }), 500

@rtmp_bp.route('/disconnect', methods=['POST'])
def disconnect_rtmp_streams():
    """断开所有RTMP流连接端点
    ---
    tags:
      - RTMP流管理
    responses:
      200:
        description: 断开连接成功
    """
    try:
        stream_manager.disconnect_all()
        return jsonify({
            'status': 'success',
            'message': '所有RTMP流已断开连接'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'断开连接失败: {str(e)}'
        }), 500

@rtmp_bp.route('/stream/<int:stream_index>')
def get_rtmp_stream(stream_index):
    """获取指定RTMP流的视频流端点
    ---
    tags:
      - RTMP流管理
    parameters:
      - name: stream_index
        in: path
        type: integer
        required: true
        description: 流索引
    responses:
      200:
        description: 视频流数据
        content:
          multipart/x-mixed-replace:
            schema:
              type: string
              format: binary
    """
    def generate():
        while stream_manager.active and stream_index in stream_manager.streams:
            frame_data = stream_manager.get_stream_frame(stream_index)
            if frame_data:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
            else:
                time.sleep(0.1)  # 避免过度占用CPU
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@rtmp_bp.route('/status')
def get_rtmp_status():
    """获取RTMP流状态端点
    ---
    tags:
      - RTMP流管理
    responses:
      200:
        description: RTMP流状态信息
        schema:
          type: object
          properties:
            active:
              type: boolean
            stream_count:
              type: integer
            streams:
              type: object
    """
    return jsonify({
        'active': stream_manager.active,
        'stream_count': len(stream_manager.streams),
        'streams': {
            str(k): {
                'url': v['url'],
                'connected': v['connected']
            } for k, v in stream_manager.streams.items()
        }
    })

# 全局连接缓存，避免重复连接
active_connections = {}
connection_locks = {}

@rtmp_bp.route('/video/<rtmp_url>')
def get_video_stream(rtmp_url):
    """直接通过RTMP URL获取视频流
    ---
    tags:
      - RTMP流管理
    parameters:
      - name: rtmp_url
        in: path
        type: string
        required: true
        description: Base64编码的RTMP URL
    responses:
      200:
        description: 视频流数据
        content:
          multipart/x-mixed-replace:
            schema:
              type: string
              format: binary
    """
    import base64
    
    try:
        # 解码RTMP URL
        decoded_url = base64.b64decode(rtmp_url).decode('utf-8')
        
        # 只在首次连接时打印日志
        if decoded_url not in active_connections:
            print(f"接收到视频流请求: {decoded_url}")
        
        def generate():
            cap = None
            try:
                # 检查是否已有活跃连接
                if decoded_url in active_connections:
                    cap = active_connections[decoded_url]
                    if cap and cap.isOpened():
                        # 复用现有连接
                        pass
                    else:
                        # 清理无效连接
                        if decoded_url in active_connections:
                            del active_connections[decoded_url]
                        cap = None
                
                # 创建新连接
                if cap is None:
                    cap = cv2.VideoCapture(decoded_url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    if not cap.isOpened():
                        print(f"无法打开视频流: {decoded_url}")
                        return
                    
                    # 缓存连接
                    active_connections[decoded_url] = cap
                    print(f"视频流连接成功: {decoded_url}")
                
                frame_count = 0
                consecutive_failures = 0
                max_failures = 5  # 减少失败阈值
                
                while True:
                    # 检查连接状态
                    if not cap.isOpened():
                        print(f"连接已断开: {decoded_url}")
                        break
                    
                    ret, frame = cap.read()
                    
                    if not ret or frame is None:
                        consecutive_failures += 1
                        
                        if consecutive_failures >= max_failures:
                            print(f"连续读取失败，断开连接: {decoded_url}")
                            break
                        
                        time.sleep(0.1)
                        continue
                    
                    # 重置失败计数
                    consecutive_failures = 0
                    frame_count += 1
                    
                    try:
                        # 简化的帧处理 - 只添加基本信息
                        processed_frame = frame.copy()
                        
                        # 添加流信息（减少文本渲染）
                        if frame_count % 30 == 1:  # 每秒更新一次文本
                            cv2.putText(processed_frame, f'Frame: {frame_count}', 
                                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        
                        # 编码为JPEG（提高质量）
                        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                        _, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
                        frame_data = buffer.tobytes()
                        
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                        
                        # 控制帧率（提高到25fps）
                        time.sleep(0.04)
                        
                    except Exception as e:
                        # 静默处理帧错误，避免日志过多
                        try:
                            _, buffer = cv2.imencode('.jpg', frame)
                            frame_data = buffer.tobytes()
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                        except:
                            break
                            
            except Exception as e:
                print(f"视频流生成器错误: {e}")
            finally:
                # 不立即释放连接，保持复用
                # 连接将在服务器重启或手动清理时释放
                if decoded_url in active_connections and not cap.isOpened():
                    del active_connections[decoded_url]
                print(f"视频流客户端断开: {decoded_url}")
        
        return Response(generate(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
                       
    except Exception as e:
        print(f"视频流处理错误: {e}")
        return jsonify({'error': str(e)}), 500

# 添加清理连接的端点
@rtmp_bp.route('/cleanup_connections', methods=['POST'])
def cleanup_connections():
    """清理所有活跃连接"""
    global active_connections
    try:
        for url, cap in active_connections.items():
            if cap:
                cap.release()
        active_connections.clear()
        return jsonify({'status': 'success', 'message': '所有连接已清理'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500