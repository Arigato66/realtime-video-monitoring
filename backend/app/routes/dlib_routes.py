from flask import Blueprint, jsonify, request
from app.services.dlib_service import dlib_face_service
from app import socketio
from flask_socketio import emit
import logging

dlib_bp = Blueprint('dlib', __name__, url_prefix='/api/dlib')

@dlib_bp.route('/faces', methods=['GET'])
def get_registered_faces():
    """
    获取所有已注册人脸姓名的列表 (Dlib)。
    ---
    tags:
      - Dlib人脸管理
    responses:
      200:
        description: 成功返回已注册的人脸姓名列表。
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            names:
              type: array
              items:
                type: string
              example: ["person1", "person2"]
    """
    names = dlib_face_service.get_all_registered_names()
    return jsonify({"status": "success", "names": names})

@dlib_bp.route('/faces/<name>', methods=['DELETE'])
def delete_registered_face(name):
    """
    按姓名删除已注册的人脸 (Dlib)。
    ---
    tags:
      - Dlib人脸管理
    parameters:
      - name: name
        in: path
        type: string
        required: true
        description: 要删除的已注册姓名。
    responses:
      200:
        description: 删除成功。
      404:
        description: 未找到指定姓名的人脸。
    """
    success = dlib_face_service.delete_face_by_name(name)
    if success:
        return jsonify({"status": "success", "message": f"'{name}' 已被成功删除。"})
    else:
        return jsonify({"status": "error", "message": f"'{name}' 未找到或无法删除。"}), 404

# --- WebSocket 交互式注册 ---

# 用于存储每个客户端的注册状态
registration_sessions = {}

@socketio.on('connect', namespace='/dlib/register')
def handle_connect():
    """客户端连接到注册命名空间"""
    sid = request.sid
    registration_sessions[sid] = {'name': None, 'capturing': False}
    logging.info(f"客户端 {sid} 已连接到 Dlib 注册。")
    emit('status', {'message': '已连接，请开始注册。'})

@socketio.on('start_registration', namespace='/dlib/register')
def handle_start_registration(data):
    """开始一个注册会话"""
    sid = request.sid
    name = data.get('name')
    if name:
        registration_sessions[sid]['name'] = name
        registration_sessions[sid]['capturing'] = True
        logging.info(f"客户端 {sid} 开始为 '{name}' 注册。")
        emit('status', {'message': f"已开始为 {name} 注册，请发送视频帧进行捕获。", "name": name})
    else:
        emit('error', {'message': '需要提供姓名。'})

@socketio.on('frame_for_capture', namespace='/dlib/register')
def handle_frame_capture(data):
    """处理用于捕获的视频帧"""
    sid = request.sid
    session = registration_sessions.get(sid)
    
    if not session or not session['capturing']:
        emit('error', {'message': '无效的会话或未开始注册。'})
        return

    name = session['name']
    image_data = data.get('image') # 接收 Base64 编码的图像数据

    if image_data:
        try:
            import base64
            import numpy as np
            import cv2

            # 解码 Base64 图像
            img_bytes = base64.b64decode(image_data.split(',')[1])
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            # 调用服务进行捕获
            result = dlib_face_service.register_face_capture(name, frame)
            
            # 将结果发回给客户端
            emit('capture_result', result)

        except Exception as e:
            logging.error(f"处理帧时出错: {e}")
            emit('error', {'message': f'处理帧时出错: {e}'})

@socketio.on('disconnect', namespace='/dlib/register')
def handle_disconnect():
    """客户端断开连接"""
    sid = request.sid
    if sid in registration_sessions:
        del registration_sessions[sid]
    logging.info(f"客户端 {sid} 已断开 Dlib 注册连接。") 