from flask import Blueprint, jsonify, request
from app.services.logger import get_logs
from datetime import datetime
from flasgger import swag_from

system_logs_bp = Blueprint('system_logs_bp', __name__, url_prefix='/api/system-logs')

@system_logs_bp.route('/', methods=['GET'])
@swag_from({
    'tags': ['系统日志'],
    'summary': '获取系统日志列表',
    'description': '支持分页和多种过滤条件查询系统日志',
    'parameters': [
        {
            'name': 'page',
            'in': 'query',
            'type': 'integer',
            'default': 1,
            'description': '页码'
        },
        {
            'name': 'per_page',
            'in': 'query',
            'type': 'integer',
            'default': 20,
            'description': '每页数量'
        },
        {
            'name': 'level',
            'in': 'query',
            'type': 'string',
            'description': '日志级别过滤 (INFO, WARNING, ERROR, CRITICAL)'
        },
        {
            'name': 'module',
            'in': 'query',
            'type': 'string',
            'description': '模块名称过滤'
        },
        {
            'name': 'start_date',
            'in': 'query',
            'type': 'string',
            'format': 'date-time',
            'description': '开始日期 (ISO格式: YYYY-MM-DDTHH:MM:SS)'
        },
        {
            'name': 'end_date',
            'in': 'query',
            'type': 'string',
            'format': 'date-time',
            'description': '结束日期 (ISO格式: YYYY-MM-DDTHH:MM:SS)'
        }
    ],
    'responses': {
        200: {
            'description': '系统日志列表',
            'schema': {
                'type': 'object',
                'properties': {
                    'logs': {'type': 'array', 'items': {'$ref': '#/definitions/SystemLog'}},
                    'total': {'type': 'integer'},
                    'pages': {'type': 'integer'},
                    'current_page': {'type': 'integer'}
                }
            }
        },
        500: {
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
def list_logs():
    """获取系统日志列表
    ---
    tags:
      - 系统日志
    summary: 获取系统日志列表
    description: 支持分页和多种过滤条件查询系统日志
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: 页码
      - name: per_page
        in: query
        type: integer
        default: 20
        description: 每页数量
      - name: level
        in: query
        type: string
        description: '日志级别过滤 (INFO, WARNING, ERROR, CRITICAL)'
      - name: module
        in: query
        type: string
        description: 模块名称过滤
      - name: start_date
        in: query
        type: string
        format: date-time
        description: 开始日期 (ISO格式: YYYY-MM-DDTHH:MM:SS)
      - name: end_date
        in: query
        type: string
        format: date-time
        description: 结束日期 (ISO格式: YYYY-MM-DDTHH:MM:SS)
    responses:
      200:
        description: 系统日志列表
        schema:
          type: object
          properties:
            logs:
              type: array
              items:
                $ref: '#/definitions/SystemLog'
            total:
              type: integer
            pages:
              type: integer
            current_page:
              type: integer
      500:
        description: 服务器内部错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: '服务器内部错误'
    """
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        level = request.args.get('level', None, type=str)
        module = request.args.get('module', None, type=str)
        
        # 解析日期参数
        start_date = None
        end_date = None
        
        if request.args.get('start_date'):
            try:
                start_date = datetime.fromisoformat(request.args.get('start_date').replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': '无效的开始日期格式'}), 400
                
        if request.args.get('end_date'):
            try:
                end_date = datetime.fromisoformat(request.args.get('end_date').replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': '无效的结束日期格式'}), 400
        
        # 获取日志
        paginated_logs = get_logs(
            page=page, 
            per_page=per_page, 
            level=level, 
            module=module, 
            start_date=start_date, 
            end_date=end_date
        )
        
        # 返回结果
        return jsonify({
            'logs': [log.to_dict() for log in paginated_logs.items],
            'total': paginated_logs.total,
            'pages': paginated_logs.pages,
            'current_page': paginated_logs.page
        })
        
    except Exception as e:
        return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500

# 在 flasgger 中定义 SystemLog 模型，以便于 API 文档生成
def register_swag_definitions(swagger):
    if swagger.template is None:
        swagger.template = {'definitions': {}}
    if 'definitions' not in swagger.template:
        swagger.template['definitions'] = {}

    system_log_definition = {
        "type": "object",
        "properties": {
            "log_id": {"type": "string", "format": "uuid"},
            "log_time": {"type": "string", "format": "date-time"},
            "log_level": {"type": "string", "enum": ["INFO", "WARNING", "ERROR", "CRITICAL"]},
            "module": {"type": "string"},
            "message": {"type": "string"},
            "details": {"type": "string"},
            "user_id": {"type": "string", "format": "uuid"}
        }
    }
    swagger.template['definitions']['SystemLog'] = system_log_definition 