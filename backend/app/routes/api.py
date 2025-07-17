from flask import Blueprint, jsonify, request
from flasgger import swag_from

# 创建API蓝图
api_bp = Blueprint('api_bp', __name__, url_prefix='/api')

@api_bp.route("/status", methods=["GET"])
@swag_from({
    'tags': ['通用及测试API'],
    'summary': '检查API服务状态',
    'description': '返回API的当前运行状态、版本等信息，可用于健康检查。',
    'responses': {
        '200': {
            'description': 'API 运行正常',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'running'},
                    'version': {'type': 'string', 'example': '1.0.0'},
                    'message': {'type': 'string', 'example': 'Video monitoring API is operational'}
                }
            }
        }
    }
})
def api_status():
    """API状态检查端点
    ---
    tags:
      - 通用及测试API
    summary: 检查API服务状态
    description: 返回API的当前运行状态、版本等信息，可用于健康检查。
    responses:
      200:
        description: API 运行正常
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
              example: 'Video monitoring API is operational'
    """
    return jsonify({
        "status": "running",
        "version": "1.0.0",
        "message": "Video monitoring API is operational"
    })

@api_bp.route("/test-alert", methods=["POST"])
@swag_from({
    'tags': ['通用及测试API'],
    'summary': '添加一条测试告警（到内存）',
    'description': '这是一个用于测试的接口，它会向系统的 **内存** 中添加一条告警信息，用于在监控视图中即时显示。',
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'description': '告警的主要信息', 'example': '这是一个测试告警'},
                    'event_type': {'type': 'string', 'description': '告警的事件类型', 'example': 'TestEvent'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '测试告警添加成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'success'},
                    'message': {'type': 'string', 'example': '已添加告警: 这是一个测试告警'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': '请求体缺失或格式错误'}
                }
            }
        }
    }
})
def add_test_alert():
    """添加测试告警到内存
    ---
    tags:
      - 通用及测试API
    summary: 添加一条测试告警（到内存）
    description: 这是一个用于测试的接口，它会向系统的内存中添加一条告警信息，用于在监控视图中即时显示。
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            message:
              type: string
              description: 告警的主要信息
              example: '这是一个测试告警'
            event_type:
              type: string
              description: 告警的事件类型
              example: TestEvent
    responses:
      200:
        description: 测试告警添加成功
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: '已添加告警: 这是一个测试告警'
      400:
        description: 请求参数错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: '请求体缺失或格式错误'
    """
    from app.services.alerts import add_alert_memory
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体缺失或格式错误'}), 400
    message = data.get('message', '这是一个测试告警')
    event_type = data.get('event_type', '测试告警')
    add_alert_memory(message, event_type=event_type)
    return jsonify({"status": "success", "message": f"已添加告警: {message}"})

@api_bp.route("/alerts", methods=["GET"])
@swag_from({
    'tags': ['通用及测试API'],
    'summary': '获取内存中的告警列表',
    'description': '获取当前存储在 **内存** 中的临时告警信息列表。这些告警是即时的，服务重启后会丢失。要获取持久化的历史告警，请使用 `/api/alerts/` 接口。',
    'responses': {
        '200': {
            'description': '成功获取内存告警列表',
            'schema': {
                'type': 'object',
                'properties': {
                    'alerts': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'event_type': {'type': 'string'},
                                'details': {'type': 'string'},
                                'message': {'type': 'string'},
                                'snapshot_path': {'type': 'string', 'nullable': True},
                                'timestamp': {'type': 'string', 'format': 'date-time'},
                                'status': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': '服务器内部错误'}
                }
            }
        }
    }
})
def get_alerts():
    """获取内存中的告警信息端点
    ---
    tags:
      - 通用及测试API
    summary: 获取内存中的告警列表
    description: 获取当前存储在内存中的临时告警信息列表。这些告警是即时的，服务重启后会丢失。要获取持久化的历史告警，请使用 /api/alerts/ 接口。
    responses:
      200:
        description: 成功获取内存告警列表
        schema:
          type: object
          properties:
            alerts:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  event_type:
                    type: string
                  details:
                    type: string
                  message:
                    type: string
                  snapshot_path:
                    type: string
                    nullable: true
                  timestamp:
                    type: string
                    format: date-time
                  status:
                    type: string
      500:
        description: 服务器内部错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: '服务器内部错误'
    """
    from app.services.alerts import get_alerts as get_memory_alerts
    try:
        memory_alerts = get_memory_alerts()
        return jsonify({"alerts": memory_alerts})
    except Exception as e:
        print(f"获取内存告警失败: {e}")
        return jsonify({"error": "服务器内部错误"}), 500