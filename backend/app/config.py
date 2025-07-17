import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 获取项目根目录的绝对路径
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class Config:
    """基础配置类，包含通用配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 从环境变量获取数据库配置
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '123456')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_DB = os.environ.get('MYSQL_DB', 'realtime_monitoring')
    MYSQL_CHARSET = os.environ.get('MYSQL_CHARSET', 'utf8mb4')

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """开发环境配置 - 连接服务器数据库"""
    DEBUG = True
    
    # 开发环境数据库配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST_DEV', '120.46.199.152')
    
    # 直接定义为类属性
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DEV_DATABASE_URL') or 
        f"mysql+pymysql://{os.environ.get('MYSQL_USER', 'root')}:"
        f"{os.environ.get('MYSQL_PASSWORD', '123456')}@"
        f"{os.environ.get('MYSQL_HOST_DEV', '120.46.199.152')}:"
        f"{os.environ.get('MYSQL_PORT', 3306)}/"
        f"{os.environ.get('MYSQL_DB', 'realtime_monitoring')}?"
        f"charset={os.environ.get('MYSQL_CHARSET', 'utf8mb4')}"
    )
    
    # 开发环境CORS配置
    CORS_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://120.46.199.152"
    ]

class ProductionConfig(Config):
    """生产环境配置 - 服务器本地数据库"""
    DEBUG = False
    
    # 生产环境数据库配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST_PROD', '127.0.0.1')
    
    # 直接定义为类属性
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('PROD_DATABASE_URL') or 
        f"mysql+pymysql://{os.environ.get('MYSQL_USER', 'root')}:"
        f"{os.environ.get('MYSQL_PASSWORD', '123456')}@"
        f"{os.environ.get('MYSQL_HOST_PROD', '127.0.0.1')}:"
        f"{os.environ.get('MYSQL_PORT', 3306)}/"
        f"{os.environ.get('MYSQL_DB', 'realtime_monitoring')}?"
        f"charset={os.environ.get('MYSQL_CHARSET', 'utf8mb4')}"
    )
    
    # 生产环境CORS配置
    CORS_ORIGINS = [
        "http://120.46.199.152",
        "https://120.46.199.152",
        "http://localhost:5173",  # 保留本地访问能力
        "http://127.0.0.1:5173"
    ]

class CloudConfig(Config):
    """云服务器专用配置"""
    DEBUG = False
    
    # 云端数据库配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST_PROD', '127.0.0.1')
    
    # 直接定义为类属性
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('PROD_DATABASE_URL') or 
        f"mysql+pymysql://{os.environ.get('MYSQL_USER', 'root')}:"
        f"{os.environ.get('MYSQL_PASSWORD', '123456')}@"
        f"{os.environ.get('MYSQL_HOST_PROD', '127.0.0.1')}:"
        f"{os.environ.get('MYSQL_PORT', 3306)}/"
        f"{os.environ.get('MYSQL_DB', 'realtime_monitoring')}?"
        f"charset={os.environ.get('MYSQL_CHARSET', 'utf8mb4')}"
    )
    
    # 云端配置只允许服务器访问
    CORS_ORIGINS = [
        "http://120.46.199.152",
        "https://120.46.199.152"
    ]

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    CORS_ORIGINS = ["*"]  # 测试环境允许所有来源

# 导出配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'cloud': CloudConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}