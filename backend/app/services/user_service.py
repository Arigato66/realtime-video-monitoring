from app import db  # 移除 bcrypt 导入
from app.models.user import User
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime

def create_user(username, password, email):
    # 检查用户名和邮箱是否已存在
    if User.query.filter_by(username=username).first():
        return {"error": "用户名已存在"}, 409
    if User.query.filter_by(email=email).first():
        return {"error": "邮箱已被注册"}, 409
    
    try:
        # 直接存储明文密码（不哈希，仅用于测试）
        new_user = User(
            username=username,
            password=password,  # 明文存储
            email=email,
            is_active=True
        )
        
        db.session.add(new_user)
        db.session.commit()
        return {"message": "用户注册成功", "user_id": new_user.user_id}, 201
    except IntegrityError as e:
        db.session.rollback()
        return {"error": f"数据库错误: {str(e)}"}, 500

def verify_user(username, password):
    user = User.query.filter_by(username=username).first()
    if not user:
        return None
    
    # 检查账户是否激活
    if not user.is_active:
        return None
    
    # 直接比较明文密码（不加密验证）
    if user.password == password:
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()
        return user
    return None