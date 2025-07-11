from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
import os

def create_app():
    # 解决 "OMP: Error #15" 警告
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})  # 启用跨域支持，允许所有来源
    swagger = Swagger(app) # 初始化 Flasgger
    
    # 定义上传目录路径
    UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    print(f"上传目录: {UPLOADS_DIR}")
    
    # 注册蓝图
    from app.routes.api import api_bp
    from app.routes.video import video_bp
    from app.routes.config import config_bp
    from app.routes.face import face_bp
    from app.routes.rtmp import rtmp_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(face_bp)
    app.register_blueprint(rtmp_bp)
    
    return app