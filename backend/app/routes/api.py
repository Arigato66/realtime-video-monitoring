from flask import Blueprint, jsonify

# 创建API蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route("/status", methods=["GET"])
def api_status():
    """API状态检查端点
    ---
    tags:
      - 通用API
    responses:
      200:
        description: API 运行状态.
        schema:
          type: object
          properties:
            status:
              type: string
              example: running
            version:
              type: string
              example: 1.0.0
            message:
              type: string
              example: Video monitoring API is operational
    """
    return jsonify({
        "status": "running",
        "version": "1.0.0",
        "message": "Video monitoring API is operational"
    })

@api_bp.route("/alerts")
def get_alerts():
    """获取告警信息端点
    ---
    tags:
      - 通用API
    responses:
      200:
        description: 当前的警报列表.
        schema:
          type: object
          properties:
            alerts:
              type: array
              items:
                type: string
              description: 警报信息列表.
    """
    from app.services.alerts import get_alerts
    return jsonify({"alerts": get_alerts()}) 