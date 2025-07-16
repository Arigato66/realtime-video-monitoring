from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.services.register_service import RegisterService
from app.services.login_service import LoginService

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
    
    # 验证必要参数
    if not all(key in data for key in ['username', 'email', 'password']):
        return jsonify({'error': '缺少必要参数（username/email/password）'}), 400
    
    # 正确实例化服务并调用方法
    service = RegisterService()
    success, result = service.create_user(  # <-- 修正此处
        username=data['username'],
        email=data['email'],
        password=data['password']
    )
    
    # 返回响应
    if success:
        return jsonify({
            'message': '注册成功',
            'user_id': result
        }), 201
    else:
        return jsonify({'error': result}), 400

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
    
    # 1. 验证必填字段
    required_fields = ['username', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "缺少必填字段: username, password"}), 400
    
    # 2. 实例化LoginService并验证用户
    login_service = LoginService()  # 实例化登录服务
    is_valid, result = login_service.verify_user(  # 调用验证方法
        username=data['username'],
        password=data['password']
    )
    
    # 3. 处理验证结果
    if not is_valid:
        return jsonify({"error": result}), 401  # 验证失败（用户名/密码错误或未激活）
    
    # 4. 验证通过：更新登录时间
    user = result  # result为用户信息字典
    login_service.update_login_time(user['user_id'])
    
    # 5. 生成JWT令牌并返回
    access_token = create_access_token(identity=user['user_id'])
    return jsonify({
        "access_token": access_token,
        "user_id": user['user_id']
    }), 200