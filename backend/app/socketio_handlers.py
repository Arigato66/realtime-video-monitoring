from app import socketio
from flask_socketio import emit, join_room, leave_room
from flask import request

@socketio.on('connect', namespace='/video')
def handle_connect():
    print(f'客户端连接: {request.sid}')
    emit('connected', {'status': 'success'})

@socketio.on('disconnect', namespace='/video')
def handle_disconnect():
    print(f'客户端断开: {request.sid}')

@socketio.on('join_stream', namespace='/video')
def handle_join_stream(data):
    """客户端加入特定视频流房间"""
    stream_id = data.get('stream_id')
    if stream_id:
        join_room(f'stream_{stream_id}')
        emit('joined_stream', {'stream_id': stream_id})

@socketio.on('leave_stream', namespace='/video')
def handle_leave_stream(data):
    """客户端离开特定视频流房间"""
    stream_id = data.get('stream_id')
    if stream_id:
        leave_room(f'stream_{stream_id}')
        emit('left_stream', {'stream_id': stream_id})