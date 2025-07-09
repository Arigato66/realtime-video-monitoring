from flask import Blueprint, request, jsonify
import os
from werkzeug.utils import secure_filename

from app.services import face_service

# 创建人脸管理蓝图
face_bp = Blueprint('face', __name__, url_prefix='/api/faces')

# 在'uploads'文件夹内为临时上传定义一个目录
# 这应该由应用的配置来处理，但目前这样可以
TEMP_UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads', 'temp_faces')
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)


@face_bp.route('/', methods=['GET'])
def get_registered_faces():
    """获取所有已注册人脸姓名的列表"""
    names = face_service.get_all_registered_names()
    return jsonify({"status": "success", "names": names})

@face_bp.route('/register', methods=['POST'])
def register_face():
    """从上传的图像中注册新的人脸"""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "未提供图像文件。"}), 400
    
    file = request.files['file']
    name = request.form.get('name')

    if not name:
        return jsonify({"status": "error", "message": "未提供姓名。"}), 400
        
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择文件。"}), 400
        
    if file:
        filename = secure_filename(file.filename)
        temp_filepath = os.path.join(TEMP_UPLOADS_DIR, filename)
        file.save(temp_filepath)
        
        # 调用服务注册人脸
        result = face_service.register_new_face(temp_filepath, name)
        
        # 清理临时文件
        os.remove(temp_filepath)
        
        if result['status'] == 'success':
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    return jsonify({"status": "error", "message": "文件上传失败。"}), 500

@face_bp.route('/<name>', methods=['DELETE'])
def delete_registered_face(name):
    """按姓名删除已注册的人脸"""
    success = face_service.delete_face(name)
    if success:
        return jsonify({"status": "success", "message": f"'{name}' 已被删除。"})
    else:
        return jsonify({"status": "error", "message": f"'{name}' 未找到或无法删除。"}), 404 