from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from app.services.register_service import RegisterService
from app.services.login_service import LoginService
from flasgger import swag_from

# ===================== 用户认证相关接口 =====================
auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1.0')

@auth_bp.route('/register', methods=['POST'])
@swag_from({
    'tags': ['用户认证'],
    'summary': '用户注册',
    'description': '注册新用户，需提供唯一用户名、邮箱和密码。',
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'password', 'email'],
                'properties': {
                    'username': {'type': 'string', 'example': 'test_user', 'description': '唯一的用户名'},
                    'password': {'type': 'string', 'example': 'secure_password123', 'format': 'password', 'description': '用户密码'},
                    'email': {'type': 'string', 'example': 'test@example.com', 'format': 'email', 'description': '唯一的电子邮箱'}
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': '注册成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': '注册成功'},
                    'user_id': {'type': 'string', 'format': 'uuid', 'example': 'a1b2c3d4-e5f6-7890-1234-567890abcdef'}
                }
            }
        },
        '400': {
            'description': '请求参数错误或用户已存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': '用户名已存在或缺少必要参数'}
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
def register():
    """用户注册端点
    ---
    tags:
      - 用户认证
    summary: 用户注册
    description: 注册新用户，需提供唯一用户名、邮箱和密码。
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, password, email]
          properties:
            username:
              type: string
              example: test_user
              description: 唯一的用户名
            password:
              type: string
              example: secure_password123
              format: password
              description: 用户密码
            email:
              type: string
              example: test@example.com
              format: email
              description: 唯一的电子邮箱
    responses:
      201:
        description: 注册成功
        schema:
          type: object
          properties:
            message:
              type: string
              example: '注册成功'
            user_id:
              type: string
              example: a1b2c3d4-e5f6-7890-1234-567890abcdef
      400:
        description: 请求参数错误或用户已存在
        schema:
          type: object
          properties:
            error:
              type: string
              example: '用户名已存在或缺少必要参数'
      500:
        description: 服务器内部错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: '服务器内部错误'
    """
    data = request.get_json()
    # 验证必要参数
    if not all(key in data for key in ['username', 'email', 'password']):
        return jsonify({'error': '缺少必要参数（username/email/password）'}), 400
    service = RegisterService()
    success, result = service.create_user(
        username=data['username'],
        email=data['email'],
        password=data['password']
    )
    if success:
        return jsonify({
            'message': '注册成功',
            'user_id': result
        }), 201
    else:
        return jsonify({'error': result}), 400

@auth_bp.route('/login', methods=['POST'])
@swag_from({
    'tags': ['用户认证'],
    'summary': '用户登录',
    'description': '用户通过用户名和密码登录，成功后返回 JWT 访问令牌。',
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'password'],
                'properties': {
                    'username': {'type': 'string', 'example': 'test_user', 'description': '用户名'},
                    'password': {'type': 'string', 'example': 'secure_password123', 'format': 'password', 'description': '用户密码'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '登录成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'access_token': {'type': 'string', 'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'},
                    'user_id': {'type': 'string', 'format': 'uuid', 'example': 'a1b2c3d4-e5f6-7890-1234-567890abcdef'}
                }
            }
        },
        '400': {
            'description': '缺少请求参数',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': '缺少必填字段: username, password'}
                }
            }
        },
        '401': {
            'description': '无效凭证或账户未激活',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': '用户名或密码错误'}
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
def login():
    """用户登录端点
    ---
    tags:
      - 用户认证
    summary: 用户登录
    description: 用户通过用户名和密码登录，成功后返回 JWT 访问令牌。
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, password]
          properties:
            username:
              type: string
              example: test_user
              description: 用户名
            password:
              type: string
              example: secure_password123
              format: password
              description: 用户密码
    responses:
      200:
        description: 登录成功
        schema:
          type: object
          properties:
            access_token:
              type: string
              example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
            user_id:
              type: string
              example: a1b2c3d4-e5f6-7890-1234-567890abcdef
      400:
        description: 缺少请求参数
        schema:
          type: object
          properties:
            error:
              type: string
              example: '缺少必填字段: username, password'
      401:
        description: 无效凭证或账户未激活
        schema:
          type: object
          properties:
            error:
              type: string
              example: '用户名或密码错误'
      500:
        description: 服务器内部错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: '服务器内部错误'
    """
    data = request.get_json()
    required_fields = ['username', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "缺少必填字段: username, password"}), 400
    login_service = LoginService()
    is_valid, result = login_service.verify_user(
        username=data['username'],
        password=data['password']
    )
    if not is_valid:
        return jsonify({"error": result}), 401
    user = result
    login_service.update_login_time(user['user_id'])
    access_token = create_access_token(identity=user['user_id'])
    return jsonify({
        "access_token": access_token,
        "user_id": user['user_id']
    }), 200