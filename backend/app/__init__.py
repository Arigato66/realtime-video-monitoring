import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flasgger import Swagger
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import traceback

# 初始化核心组件
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()  # 注意：这里统一使用一个jwt实例
socketio = SocketIO()

def create_app():
    # 解决 "OMP: Error #15" 警告
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    app = Flask(__name__)
    
    # 优化CORS配置（解决跨域问题核心）
    CORS(app,
        origins=["http://localhost:5173"],  # 明确前端域名
        supports_credentials=True,         # 允许携带认证信息
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 允许所有必要方法
        allow_headers=["Content-Type", "Authorization"],  # 允许认证头和内容类型
        max_age=3600  # 预检请求缓存1小时，减少重复验证
    )
    
    # 处理OPTIONS预检请求（关键：避免跨域预检失败）
    @app.before_request
    def handle_options_request():
        if request.method == 'OPTIONS':
            return jsonify({"status": "preflight OK"}), 200, {
                'Access-Control-Allow-Origin': "http://localhost:5173",
                'Access-Control-Allow-Methods': "GET, POST, PUT, DELETE, OPTIONS",
                'Access-Control-Allow-Headers': "Content-Type, Authorization",
                'Access-Control-Max-Age': "3600"
            }
    
    # 初始化扩展
    Swagger(app)
    socketio.init_app(app, cors_allowed_origins="http://localhost:5173")  # 细化SocketIO跨域
    
    # 加载配置
    app.config.from_object('app.config.Config')
    
    # 绑定扩展到应用
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)  # 使用全局jwt实例
    
    # 定义上传目录路径
    UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    print(f"上传目录: {UPLOADS_DIR}")
    
    # 注册蓝图（按功能分组，保持顺序一致）
    from app.routes.api import api_bp
    from app.routes.video import video_bp
    from app.routes.config import config_bp
    from app.routes.face import face_bp
    from app.routes.auth import auth_bp 
    from app.routes.dlib_routes import dlib_bp
    from app.routes.rtmp_routes import rtmp_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(main_bp)        # 主路由优先
    app.register_blueprint(auth_bp)        # 认证相关路由
    app.register_blueprint(api_bp)         # 核心API路由
    app.register_blueprint(video_bp)       # 视频相关路由
    app.register_blueprint(config_bp)      # 配置相关路由
    app.register_blueprint(dlib_bp)        # 人脸识别路由
    app.register_blueprint(rtmp_bp)        # 流媒体路由
    
    # 配置JWT错误处理
    add_jwt_handlers(jwt)
    
    # 添加全局错误处理
    add_error_handlers(app)
    
    # 验证数据库连接
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1"))
                print("✅ MySQL数据库连接成功")
        except Exception as e:
            print(f"❌ MySQL数据库连接失败: {e}")
            print(traceback.format_exc())
    
    return app 

def add_jwt_handlers(jwt):
    """添加JWT错误处理"""
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            "error": "无效的令牌",
            "message": str(error)
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            "error": "缺少授权令牌",
            "message": "请求需要有效的JWT令牌"
        }), 401
        
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "error": "令牌已过期",
            "message": "请重新登录获取新令牌"
        }), 401

def add_error_handlers(app):
    """添加全局错误处理"""
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "error": "资源未找到",
            "message": str(error)
        }), 404
        
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "服务器内部错误",
            "message": "请稍后再试或联系管理员"
        }), 500
   
    @app.errorhandler(401)
    def unauthorized_error(error):
        return jsonify({
            "error": "未授权",
            "message": "请先登录"
        }), 401

    # 新增：处理OPTIONS请求的错误（确保预检请求不返回错误状态）
    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.method == 'OPTIONS':
            return jsonify({"status": "preflight allowed"}), 200
        return jsonify({
            "error": "方法不允许",
            "message": str(error)
        }), 405