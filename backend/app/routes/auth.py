from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.services.user_service import create_user, verify_user

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1.0')

@auth_bp.route('/signin', methods=['POST'])
def register():
    """用户注册端点
    ---
    tags:
      - 用户认证
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
            password:
              type: string
              example: secure_password123
            email:
              type: string
              example: test@example.com
    responses:
      201:
        description: 注册成功
        schema:
          type: object
          properties:
            message:
              type: string
              example: 用户注册成功
            user_id:
              type: string
              example: 123e4567-e89b-12d3-a456-426614174000
      409:
        description: 用户名或邮箱已存在
        schema:
          type: object
          properties:
            error:
              type: string
              example: 用户名已存在
      500:
        description: 服务器内部错误
    """
    data = request.get_json()
    # 验证必填字段
    required_fields = ['username', 'password', 'email']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "缺少必填字段: username, password, email"}), 400
    
    result, status_code = create_user(
        data['username'],
        data['password'],
        data['email']
    )
    return jsonify(result), status_code

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录端点
    ---
    tags:
      - 用户认证
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
            password:
              type: string
              example: secure_password123
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
              example: 123e4567-e89b-12d3-a456-426614174000
      401:
        description: 无效凭证或账户未激活
        schema:
          type: object
          properties:
            error:
              type: string
              example: 用户名或密码错误
    """
    data = request.get_json()
    # 验证必填字段
    required_fields = ['username', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "缺少必填字段: username, password"}), 400
    
    user = verify_user(data['username'], data['password'])
    if user:
        # 在JWT令牌中包含用户ID
        access_token = create_access_token(identity=user.user_id)
        return jsonify({
            "access_token": access_token,
            "user_id": user.user_id
        }), 200
    return jsonify({"error": "用户名或密码错误"}), 401