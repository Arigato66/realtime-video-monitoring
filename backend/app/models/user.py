from app import db
import uuid
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(
        db.String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment='用户唯一标识符(UUID)'
    )
    username = db.Column(
        db.String(50), 
        unique=True, 
        nullable=False,
        comment='用户名'
    )
    password = db.Column(
        db.String(100), 
        nullable=False,
        comment='密码哈希'
    )
    email = db.Column(
        db.String(100), 
        unique=True, 
        nullable=False,
        comment='邮箱'
    )
    created_at = db.Column(
        db.TIMESTAMP, 
        server_default=db.func.current_timestamp(),
        comment='创建时间'
    )
    last_login = db.Column(
        db.TIMESTAMP, 
        nullable=True,
        comment='最后登录时间'
    )
    is_active = db.Column(
        db.Boolean, 
        default=True,
        nullable=False,
        comment='账户是否激活'
    )

    def __repr__(self):
        return f'<User {self.username}>'