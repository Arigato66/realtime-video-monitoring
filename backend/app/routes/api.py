from flask import Blueprint, jsonify, request
from app import socketio
from flask_socketio import emit
from app.services import real_time_detection
import subprocess
import os
import time
import threading
from app.services import system_state

# 初始化系统状态
system_state.FACE_RECOGNITION_ENABLED = False

# 创建一个互斥锁和全局变量，用于防止多个活体检测实例同时运行
face_anti_spoofing_lock = threading.Lock()
face_anti_spoofing_running = False

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')
from flasgger import swag_from

# 创建API蓝图
api_bp = Blueprint('api_bp', __name__, url_prefix='/api')

@api_bp.route("/status", methods=["GET"])
@swag_from({
    'tags': ['通用及测试API'],
    'summary': '检查API服务状态',
    'description': '返回API的当前运行状态、版本等信息，可用于健康检查。',
    'responses': {
        '200': {
            'description': 'API 运行正常',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'running'},
                    'version': {'type': 'string', 'example': '1.0.0'},
                    'message': {'type': 'string', 'example': 'Video monitoring API is operational'}
                }
            }
        }
    }
})
def api_status():
    """API status check endpoint
    ---
    tags:
      - General API
    responses:
      200:
        description: API running status.
      - 通用及测试API
    summary: 检查API服务状态
    description: 返回API的当前运行状态、版本等信息，可用于健康检查。
    responses:
      200:
        description: API 运行正常
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
              example: 'Video monitoring API is operational'
    """
    return jsonify({
        "status": "running",
        "version": "1.0.0",
        "message": "Video monitoring API is operational"
    })

@api_bp.route("/test-alert", methods=["POST"])
@swag_from({
    'tags': ['通用及测试API'],
    'summary': '添加一条测试告警（到内存）',
    'description': '这是一个用于测试的接口，它会向系统的 **内存** 中添加一条告警信息，用于在监控视图中即时显示。',
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': '告警的主要信息', 'example': '这是一个测试告警'},
                    'event_type': {'type': 'string', 'description': '告警的事件类型', 'example': 'TestEvent'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '测试告警添加成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'success'},
                    'message': {'type': 'string', 'example': '已添加告警: 这是一个测试告警'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': '请求体缺失或格式错误'}
                }
            }
        }
    }
})
def add_test_alert():
    """添加测试告警到内存
    ---
    tags:
      - 通用及测试API
    summary: 添加一条测试告警（到内存）
    description: 这是一个用于测试的接口，它会向系统的内存中添加一条告警信息，用于在监控视图中即时显示。
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            message:
              type: string
              description: 告警的主要信息
              example: '这是一个测试告警'
            event_type:
              type: string
              description: 告警的事件类型
              example: TestEvent
    responses:
      200:
        description: 测试告警添加成功
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: '已添加告警: 这是一个测试告警'
      400:
        description: 请求参数错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: '请求体缺失或格式错误'
    """
    from app.services.alerts import add_alert_memory
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体缺失或格式错误'}), 400
    message = data.get('message', '这是一个测试告警')
    event_type = data.get('event_type', '测试告警')
    add_alert_memory(message, event_type=event_type)
    return jsonify({"status": "success", "message": f"已添加告警: {message}"})

@api_bp.route("/alerts", methods=["GET"])
@swag_from({
    'tags': ['通用及测试API'],
    'summary': '获取内存中的告警列表',
    'description': '获取当前存储在 **内存** 中的临时告警信息列表。这些告警是即时的，服务重启后会丢失。要获取持久化的历史告警，请使用 `/api/alerts/` 接口。',
    'responses': {
        '200': {
            'description': '成功获取内存告警列表',
            'schema': {
                'type': 'object',
                'properties': {
                    'alerts': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'event_type': {'type': 'string'},
                                'details': {'type': 'string'},
                                'message': {'type': 'string'},
                                'snapshot_path': {'type': 'string', 'nullable': True},
                                'timestamp': {'type': 'string', 'format': 'date-time'},
                                'status': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': '服务器内部错误'}
                }
            }
        }
    }
})
def get_alerts():
    """Get alerts endpoint
    ---
    tags:
      - General API
    responses:
      200:
        description: Current list of alerts.
    """获取内存中的告警信息端点
    ---
    tags:
      - 通用及测试API
    summary: 获取内存中的告警列表
    description: 获取当前存储在内存中的临时告警信息列表。这些告警是即时的，服务重启后会丢失。要获取持久化的历史告警，请使用 '/api/alerts/' 接口。
    responses:
      200:
        description: 成功获取内存告警列表
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

# 启动活体检测的API端点
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
    global face_anti_spoofing_running
    
    # 检查活体检测是否已经在运行
    with face_anti_spoofing_lock:
        if face_anti_spoofing_running:
            return jsonify({
                "status": "warning",
                "message": "Face anti-spoofing is already running"
            })
        face_anti_spoofing_running = True
    
    try:
        # 导入活体检测函数和模型下载函数
        from app.services.face_anti_spoofing import run_face_anti_spoofing
        from app.services.download_models import download_required_models
        
        # 先下载所需的模型文件
        def download_and_run():
            global face_anti_spoofing_running
            try:
                # 下载所需模型
                download_required_models()
                
                # 启动活体检测（在单独窗口中运行，不推流到前端）
                run_face_anti_spoofing()
            except Exception as e:
                print(f"活体检测过程中出现错误: {str(e)}")
            finally:
                # 无论如何，运行结束后重置标志
                with face_anti_spoofing_lock:
                    face_anti_spoofing_running = False
        
        # 启动活体检测线程
        thread = threading.Thread(target=download_and_run)
        thread.daemon = True  # 设置为守护线程，主程序退出时自动结束
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Face anti-spoofing started in a separate window"
        })
    except Exception as e:
        # 发生异常时，重置运行标志
        with face_anti_spoofing_lock:
            face_anti_spoofing_running = False
        
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
                type: object
                properties:
                  id:
                    type: integer
                  event_type:
                    type: string
                  details:
                    type: string
                  message:
                    type: string
                  snapshot_path:
                    type: string
                    nullable: true
                  timestamp:
                    type: string
                    format: date-time
                  status:
                    type: string
      500:
        description: 服务器内部错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: '服务器内部错误'
    """
    from app.services.alerts import get_alerts as get_memory_alerts
    try:
        memory_alerts = get_memory_alerts()
        return jsonify({"alerts": memory_alerts})
    except Exception as e:
        print(f"获取内存告警失败: {e}")
        return jsonify({"error": "服务器内部错误"}), 500
