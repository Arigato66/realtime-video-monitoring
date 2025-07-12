from flask import Blueprint

# 创建主蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return "视频监控系统后端服务已运行"