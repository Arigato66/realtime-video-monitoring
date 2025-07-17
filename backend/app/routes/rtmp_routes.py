from flask import Blueprint, request, jsonify, Response
from flask_socketio import emit, join_room, leave_room
from app import socketio
from app.services.rtmp_manager import rtmp_manager
import cv2
import json
from datetime import datetime

# 创建RTMP蓝图
rtmp_bp = Blueprint('rtmp', __name__, url_prefix='/api')

@rtmp_bp.route('/streams', methods=['POST'])
def create_stream():
    """
    创建新的RTMP视频流
    ---
    tags:
      - RTMP流管理
    summary: 创建新的RTMP视频流
    description: 创建一个新的RTMP视频流。
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name, rtmp_url]
          properties:
            name:
              type: string
              description: 流名称
            rtmp_url:
              type: string
              description: RTMP推流地址
    responses:
      201:
        description: 流创建成功
        schema:
          type: object
          properties:
            stream_id:
              type: string
            status:
              type: string
              example: created
            message:
              type: string
              example: '流创建成功'
      400:
        description: 请求参数错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: '缺少必需字段: name 和 rtmp_url'
    """
    try:
        data = request.get_json()
        if not data.get('name') or not data.get('rtmp_url'):
            return jsonify({'error': '缺少必需字段: name 和 rtmp_url'}), 400
        stream_id = rtmp_manager.add_stream(data)
        return jsonify({
            'stream_id': stream_id,
            'status': 'created',
            'message': '流创建成功'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@rtmp_bp.route('/streams', methods=['GET'])
def list_streams():
    """
    获取所有视频流列表
    ---
    tags:
      - RTMP流管理
    summary: 获取所有视频流列表
    description: 获取所有已注册的RTMP视频流信息。
    responses:
      200:
        description: 成功返回所有流信息
        schema:
          type: array
          items:
            type: object
            properties:
              stream_id:
                type: string
              name:
                type: string
              rtmp_url:
                type: string
              status:
                type: string
      500:
        description: 服务器内部错误
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        streams = rtmp_manager.get_all_streams()
        return jsonify(streams), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rtmp_bp.route('/streams/<stream_id>/start', methods=['POST'])
def start_stream(stream_id):
    """
    启动视频流处理
    ---
    tags:
      - RTMP流管理
    summary: 启动视频流处理
    description: 启动指定ID的视频流。
    parameters:
      - name: stream_id
        in: path
        type: string
        required: true
        description: 流ID
    responses:
      200:
        description: 流启动成功
        schema:
          type: object
          properties:
            status:
              type: string
              example: started
            message:
              type: string
              example: '流启动成功'
      400:
        description: 启动失败
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        rtmp_manager.start_stream(stream_id)
        return jsonify({
            'status': 'started',
            'message': '流启动成功'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@rtmp_bp.route('/streams/<stream_id>/stop', methods=['POST'])
def stop_stream(stream_id):
    """
    停止视频流处理
    ---
    tags:
      - RTMP流管理
    summary: 停止视频流处理
    description: 停止指定ID的视频流。
    parameters:
      - name: stream_id
        in: path
        type: string
        required: true
        description: 流ID
    responses:
      200:
        description: 流停止成功
        schema:
          type: object
          properties:
            status:
              type: string
              example: stopped
            message:
              type: string
              example: '流停止成功'
      400:
        description: 停止失败
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        rtmp_manager.stop_stream(stream_id)
        return jsonify({
            'status': 'stopped',
            'message': '流停止成功'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@rtmp_bp.route('/streams/<stream_id>', methods=['DELETE'])
def delete_stream(stream_id):
    """
    删除视频流
    ---
    tags:
      - RTMP流管理
    summary: 删除视频流
    description: 删除指定ID的视频流。
    parameters:
      - name: stream_id
        in: path
        type: string
        required: true
        description: 流ID
    responses:
      200:
        description: 流删除成功
        schema:
          type: object
          properties:
            status:
              type: string
              example: deleted
            message:
              type: string
              example: '流删除成功'
      400:
        description: 删除失败
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        rtmp_manager.delete_stream(stream_id)
        return jsonify({
            'status': 'deleted',
            'message': '流删除成功'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@rtmp_bp.route('/streams/<stream_id>/feed')
def stream_feed(stream_id):
    """
    获取指定流的视频feed
    ---
    tags:
      - RTMP流管理
    summary: 获取指定流的视频feed
    description: 获取指定ID的视频流的实时视频帧。
    parameters:
      - name: stream_id
        in: path
        type: string
        required: true
        description: 流ID
    produces:
      - multipart/x-mixed-replace; boundary=frame
    responses:
      200:
        description: 视频流正在传输
      400:
        description: 获取失败
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        def generate():
            for frame_data in rtmp_manager.get_stream_frames(stream_id):
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
        return Response(generate(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# SocketIO事件处理
@socketio.on('connect', namespace='/rtmp')
def handle_rtmp_connect():
    print('客户端连接到RTMP命名空间')
    emit('status', {'message': '已连接到RTMP服务'})

@socketio.on('disconnect', namespace='/rtmp')
def handle_rtmp_disconnect():
    print('客户端从RTMP命名空间断开')

@socketio.on('join_stream', namespace='/rtmp')
def handle_join_stream(data):
    stream_id = data.get('stream_id')
    if stream_id:
        join_room(stream_id)
        emit('status', {'message': f'已加入流 {stream_id}'})

@socketio.on('leave_stream', namespace='/rtmp')
def handle_leave_stream(data):
    stream_id = data.get('stream_id')
    if stream_id:
        leave_room(stream_id)
        emit('status', {'message': f'已离开流 {stream_id}'})