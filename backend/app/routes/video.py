import os
import uuid
import threading
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename

from app.services.detection import process_image, process_video
from app.services.video import video_feed, stop_video_feed_service
from app.services.alerts import reset_alerts

# 创建视频蓝图
video_bp = Blueprint('video', __name__, url_prefix='/api')

# 用于管理异步任务的字典
tasks = {}

def run_video_processing(task_id, filepath, output_dir, app):
    """一个包装函数，在后台线程中运行process_video并存储结果"""
    try:
        # 使用传入的app对象创建上下文
        with app.app_context():
            result = process_video(filepath, output_dir)
            tasks[task_id] = {'status': 'completed', 'result': result}
    except Exception as e:
        print(f"视频处理任务 {task_id} 失败: {e}")
        tasks[task_id] = {'status': 'error', 'result': {'status': 'error', 'message': str(e)}}

# 定义上传目录路径
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

@video_bp.route('/video_feed')
def get_video_feed():
    """
    视频流端点
    ---
    tags:
      - 视频处理
    summary: 获取实时视频流
    description: '提供实时视频流。此端点返回一个 multipart/x-mixed-replace 响应，用于视频流。浏览器中的 <img> 标签可以直接使用此端点的URL作为 src。'
    produces:
      - multipart/x-mixed-replace; boundary=frame
    responses:
      200:
        description: 视频流正在传输.
    """
    return video_feed()

@video_bp.route('/stop_video_feed', methods=['POST'])
def stop_video_feed():
    """
    停止摄像头视频流端点
    ---
    tags:
      - 视频处理
    summary: 停止摄像头视频流
    description: 停止摄像头实时视频流。
    responses:
      200:
        description: 视频流已成功停止
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: 'Video feed stopped.'
      500:
        description: 停止失败
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: 'Failed to stop video feed.'
    """
    if stop_video_feed_service():
        return jsonify({"status": "success", "message": "Video feed stopped."})
    else:
        return jsonify({"status": "error", "message": "Failed to stop video feed."}), 500

@video_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    文件上传处理端点
    ---
    tags:
      - 视频处理
    summary: 上传视频或图片文件
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: 要上传的视频 (mp4) 或图片 (jpg) 文件.
    responses:
      200:
        description: 文件处理成功.
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            media_type:
              type: string
              example: video
            file_url:
              type: string
              description: 处理后可供访问的文件URL.
              example: /api/files/processed_video.mp4
            alerts:
              type: array
              items:
                type: string
              description: 处理过程中生成的警报列表.
      202:
        description: 视频处理已开始（异步任务）
        schema:
          type: object
          properties:
            status:
              type: string
              example: processing
            message:
              type: string
              example: '视频处理已开始.'
            task_id:
              type: string
      400:
        description: 请求错误，例如没有文件、文件类型不支持等.
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: 'No file part'
    """
    reset_alerts()
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOADS_DIR, filename)
        file.save(filepath)
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if file_extension == 'jpg':
            return jsonify(process_image(filepath, UPLOADS_DIR))
        elif file_extension == 'mp4':
            task_id = str(uuid.uuid4())
            tasks[task_id] = {'status': 'processing', 'result': None}
            app = current_app._get_current_object()
            thread = threading.Thread(target=run_video_processing, args=(task_id, filepath, UPLOADS_DIR, app))
            thread.start()
            return jsonify({
                "status": "processing",
                "message": "视频处理已开始.",
                "task_id": task_id,
            }), 202
        else:
            return jsonify({
                "status": "error", 
                "message": "Unsupported file type. Please upload JPG or MP4."
            }), 400

@video_bp.route('/video/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    获取视频处理任务的状态
    ---
    tags:
      - 视频处理
    summary: 获取视频处理任务状态
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: 视频处理任务的ID.
    responses:
      202:
        description: 任务仍在处理中.
        schema:
          type: object
          properties:
            status:
              type: string
              example: processing
      200:
        description: 任务成功完成.
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
      404:
        description: 任务未找到.
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: 'Task not found'
      500:
        description: 任务处理失败.
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: '任务处理失败'
    """
    task = tasks.get(task_id)
    if not task:
        return jsonify({"status": "error", "message": "Task not found"}), 404
    if task['status'] == 'completed':
        return jsonify(task['result'])
    elif task['status'] == 'error':
        return jsonify(task['result']), 500
    else:  # processing
        return jsonify({"status": "processing"}), 202

@video_bp.route('/files/<filename>')
def serve_file(filename):
    """
    文件访问端点
    ---
    tags:
      - 视频处理
    summary: 访问处理后的视频或图片文件
    parameters:
      - name: filename
        in: path
        type: string
        required: true
        description: 要访问的文件名 (通常是处理后的视频或图片).
    responses:
      200:
        description: 成功返回文件.
      404:
        description: 文件未找到.
    """
    print(f"请求访问文件: {filename}, 目录: {UPLOADS_DIR}")
    filename = secure_filename(filename)
    return send_from_directory(UPLOADS_DIR, filename) 