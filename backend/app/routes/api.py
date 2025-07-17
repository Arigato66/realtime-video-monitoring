from flask import Blueprint, jsonify, request
from app import socketio
from flask_socketio import emit
from app.services import real_time_detection
import subprocess
import os
import time
import threading

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route("/status", methods=["GET"])
def api_status():
    """API status check endpoint
    ---
    tags:
      - General API
    responses:
      200:
        description: API running status.
        schema:
          type: object
          properties:
            status:
              type: string
              example: running
            version:
              type: string
              example: 1.0.0
            message:
              type: string
              example: Video monitoring API is operational
    """
    return jsonify({
        "status": "running",
        "version": "1.0.0",
        "message": "Video monitoring API is operational"
    })

@api_bp.route("/alerts")
def get_alerts():
    """Get alerts endpoint
    ---
    tags:
      - General API
    responses:
      200:
        description: Current list of alerts.
        schema:
          type: object
          properties:
            alerts:
              type: array
              items:
                type: string
              description: List of alert messages.
    """
    from app.services.alerts import get_alerts as get_alerts_service
    return jsonify({"alerts": get_alerts_service()})

# 新增：启动活体检测的API端点
@api_bp.route("/start_face_anti_spoofing", methods=["POST"])
def start_face_anti_spoofing():
    """启动活体检测
    ---
    tags:
      - Face Anti-Spoofing
    responses:
      200:
        description: 活体检测启动状态
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Face anti-spoofing started
    """
    try:
        # 导入活体检测函数和模型下载函数
        from app.services.face_anti_spoofing import run_face_anti_spoofing
        from app.services.download_models import download_required_models
        
        # 确保之前的视频流已停止
        from app.services.video import stop_video_feed_service
        stop_video_feed_service()
        
        # 等待资源释放
        time.sleep(1)
        
        # 先下载所需的模型文件
        def download_and_run():
            try:
                # 下载所需模型
                download_required_models()
                
                # 启动活体检测
                run_face_anti_spoofing()
            except Exception as e:
                print(f"活体检测过程中出现错误: {str(e)}")
        
        # 启动活体检测线程
        thread = threading.Thread(target=download_and_run)
        thread.daemon = True  # 设置为守护线程，主程序退出时自动结束
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Face anti-spoofing started"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to start face anti-spoofing: {str(e)}"
        }), 500

# Scream detection WebSocket route
@socketio.on('scream_detect', namespace='/api/scream_ws')
def handle_scream_detect(message):
    # 在Flask-SocketIO中，我们可以通过连接ID发送消息
    # 但不使用request.sid，而是直接使用None让socketio广播给所有客户端
    sid = None
    action = message.get('action')
    if action == 'start':
        def ws_callback(result):
            # Use socketio.emit with to=sid
            socketio.emit('scream_status', result, namespace='/api/scream_ws', to=sid)
            if result['status'] == 'scream':
                socketio.emit('scream_alert', {'alert': 'Scream detected!'}, namespace='/api/scream_ws', to=sid)
        real_time_detection.start_scream_detection(ws_callback)
        socketio.emit('scream_status', {'status': 'listening'}, namespace='/api/scream_ws', to=sid)
    elif action == 'stop':
        real_time_detection.stop_scream_detection()
        socketio.emit('scream_status', {'status': 'stopped'}, namespace='/api/scream_ws', to=sid) 