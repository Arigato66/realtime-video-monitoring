from flask import Blueprint

# 创建主蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """
    系统运行状态检查
    ---
    tags:
      - 系统健康检查
    summary: 系统运行状态检查
    description: 检查后端服务是否正常运行。
    responses:
      200:
        description: 服务运行正常
        schema:
          type: string
          example: '视频监控系统后端服务已运行'
    """
    return "视频监控系统后端服务已运行"