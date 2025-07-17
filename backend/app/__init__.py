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
jwt = JWTManager()
socketio = SocketIO()

def create_app(config_name=None):
    # 解决 "OMP: Error #15" 警告
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    app = Flask(__name__)
    
    # 根据环境变量选择配置
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')
    
    # 动态加载配置
    from app.config import config  # 导入配置字典
    config_class = config[config_name]
    app.config.from_object(config_class)
    
    # 如果配置类有初始化方法则调用
    if hasattr(config_class, 'init_app') and callable(config_class.init_app):
        config_class.init_app(app)
    
    print(f"🔧 当前运行环境: {config_name}")
    print(f"🔧 数据库URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
    
    # 动态CORS配置 - 解决多源头问题
    cors_origins = app.config.get('CORS_ORIGINS', [
        "http://localhost:5173", 
        "http://127.0.0.1:5173", 
        "http://120.46.199.152"
    ])
    
    print(f"🌐 允许的CORS来源: {cors_origins}")
    
    # 使用Flask-CORS统一处理CORS - 删除自定义OPTIONS处理器
    CORS(app,
        origins=cors_origins,
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
        max_age=3600
    )
    
    # 初始化扩展
    Swagger(app)
    socketio.init_app(app, 
        cors_allowed_origins=cors_origins,
        logger=True,
        engineio_logger=True
    )
    
    # 绑定扩展到应用
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    
    # 创建上传目录
    UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    print(f"📁 上传目录: {UPLOADS_DIR}")
    
    # 注册蓝图
    from app.routes.api import api_bp
    from app.routes.video import video_bp
    from app.routes.config import config_bp
    from app.routes.auth import auth_bp 
    from app.routes.dlib_routes import dlib_bp
    from app.routes.rtmp_routes import rtmp_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(rtmp_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dlib_bp)
    
    # 配置JWT和错误处理
    add_jwt_handlers(jwt)
    add_error_handlers(app)
    
    # 验证数据库连接
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1"))
                print("✅ 数据库连接成功")
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
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

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "error": "方法不允许",
            "message": str(error)
        }), 405