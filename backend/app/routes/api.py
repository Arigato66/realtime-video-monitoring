from flask import Blueprint, jsonify, request
from app import socketio
from flask_socketio import emit
from app.services import real_time_detection

# 创建API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route("/status", methods=["GET"])
def api_status():
    """API状态检查端点
    ---
    tags:
      - 通用API
    responses:
      200:
        description: API 运行状态.
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
    """获取告警信息端点
    ---
    tags:
      - 通用API
    responses:
      200:
        description: 当前的警报列表.
        schema:
          type: object
          properties:
            alerts:
              type: array
              items:
                type: string
              description: 警报信息列表.
    """
    from app.services.alerts import get_alerts
# 新增：尖叫声检测 WebSocket 路由
@socketio.on('scream_detect', namespace='/api/scream_ws')
def handle_scream_detect(message):
    sid = request.sid  # 获取当前客户端 session id
    action = message.get('action')
    if action == 'start':
        def ws_callback(result):
            # 用 socketio.emit 并指定 to=sid
            socketio.emit('scream_status', result, namespace='/api/scream_ws', to=sid)
            if result['status'] == 'scream':
                socketio.emit('scream_alert', {'alert': '检测到尖叫声！'}, namespace='/api/scream_ws', to=sid)
        real_time_detection.start_scream_detection(ws_callback)
        socketio.emit('scream_status', {'status': 'listening'}, namespace='/api/scream_ws', to=sid)
    elif action == 'stop':
        real_time_detection.stop_scream_detection()
        socketio.emit('scream_status', {'status': 'stopped'}, namespace='/api/scream_ws', to=sid) 