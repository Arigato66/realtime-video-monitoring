from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask import jsonify  
from flask_sqlalchemy import SQLAlchemy 
from flask_socketio import SocketIO
from .config import config  # 修改这里：导入config字典
import os

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
socketio = SocketIO()

def create_app(config_name=None):
    # 解决 "OMP: Error #15" 警告
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    app = Flask(__name__)
    
    # 根据环境变量FLASK_CONFIG来选择加载哪个配置
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')
        
    # 加载对应环境的配置
    config_class = config[config_name]
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    print(f"🔧 当前运行环境: {config_name}")
    
    # 获取数据库URI（处理@property装饰器）
    db_uri = getattr(config_class(), 'SQLALCHEMY_DATABASE_URI', 'Not configured')
    print(f"🔧 数据库URI: {db_uri[:50]}...")
    
    # 🔥 动态CORS配置 - 根据环境自动调整
    cors_origins = getattr(config_class, 'CORS_ORIGINS', [
        "http://localhost:5173", 
        "http://127.0.0.1:5173", 
        "http://120.46.199.152"
    ])
    
    print(f"🌐 允许的CORS来源: {len(cors_origins)} 个")
    
    CORS(app, 
         origins=cors_origins,
         allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         supports_credentials=True
    )
    
    swagger = Swagger(app)
    
    # 🔥 动态Socket.IO配置
    socketio.init_app(app, 
        cors_allowed_origins=cors_origins,
        logger=True,
        engineio_logger=True,
        async_mode='threading'
    )

    db.init_app(app)
    bcrypt.init_app(app)
    JWTManager(app)

    # 定义上传目录路径
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
    
    add_jwt_handlers(jwt)
    add_error_handlers(app)
    
    # 测试数据库连接
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1"))
                print("✅ 数据库连接成功")
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            import traceback
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