import os
import cv2
import uuid
import json
from flask import Blueprint, request, jsonify, Response, send_from_directory, current_app
from werkzeug.utils import secure_filename
from app.services.video import video_feed, stop_video_feed_service
from app.services.detection import process_image, process_video
from app.services.logger import log_info, log_error

video_bp = Blueprint('video_bp', __name__, url_prefix='/api')

# 确保上传目录存在
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

# 确保快照目录存在
SNAPSHOTS_DIR = os.path.join(UPLOADS_DIR, 'snapshots')
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@video_bp.route('/video_feed')
def get_video_feed():
    """提供实时视频流"""
    log_info('video', '开始视频流')
    return video_feed()

@video_bp.route('/stop_video_feed', methods=['POST'])
def stop_video_feed():
    """停止视频流"""
    result = stop_video_feed_service()
    log_info('video', '停止视频流')
    return jsonify({"success": result})

@video_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    处理文件上传
    ---
    tags:
      - 视频处理
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: 要上传的图片或视频文件
    responses:
      200:
        description: 文件处理成功
      400:
        description: 无效的请求或文件类型
      500:
        description: 服务器内部错误
    """
    # 检查请求中是否有文件
    if 'file' not in request.files:
        log_error('video', '上传失败: 请求中没有文件')
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['file']
    
    # 检查文件名是否为空
    if file.filename == '':
        log_error('video', '上传失败: 未选择文件')
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    # 检查文件类型是否允许
    if not allowed_file(file.filename):
        log_error('video', f'上传失败: 不支持的文件类型 ({file.filename})')
        return jsonify({"status": "error", "message": "File type not allowed"}), 400
    
    # 安全地获取文件名并保存文件
    filename = secure_filename(file.filename)
    
    # 添加随机前缀以避免文件名冲突
    unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join(UPLOADS_DIR, unique_filename)
    
    try:
        file.save(filepath)
        log_info('video', f'文件上传成功: {unique_filename}')
        
        # 根据文件类型进行不同处理
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        if file_ext in {'png', 'jpg', 'jpeg'}:
            # 处理图片
            result = process_image(filepath, UPLOADS_DIR)
            return jsonify(result)
        elif file_ext in {'mp4', 'avi', 'mov'}:
            # 处理视频
            result = process_video(filepath, UPLOADS_DIR)
            return jsonify(result)
        else:
            # 不应该到达这里，因为已经检查了文件类型
            log_error('video', f'未知的文件类型: {file_ext}')
            return jsonify({"status": "error", "message": "Unknown file type"}), 400
            
    except Exception as e:
        log_error('video', f'处理上传文件时出错: {str(e)}')
        return jsonify({"status": "error", "message": str(e)}), 500

@video_bp.route('/files/<path:filename>')
def serve_file(filename):
    """
    提供上传的文件
    ---
    tags:
      - 文件服务
    parameters:
      - name: filename
        in: path
        type: string
        required: true
        description: 要提供的文件名
    responses:
      200:
        description: 文件内容
      404:
        description: 文件未找到
    """
    try:
        # 处理快照路径
        if filename.startswith('snapshots/'):
            # 从snapshots子目录提供文件
            snapshot_filename = filename.replace('snapshots/', '')
            return send_from_directory(SNAPSHOTS_DIR, snapshot_filename)
        else:
            # 从主上传目录提供文件
            return send_from_directory(UPLOADS_DIR, filename)
    except Exception as e:
        log_error('video', f'提供文件时出错: {str(e)}')
        return jsonify({"status": "error", "message": str(e)}), 404 