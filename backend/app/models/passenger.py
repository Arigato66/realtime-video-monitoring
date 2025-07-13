from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Date, Boolean, Text, LargeBinary, TIMESTAMP, func
import uuid
from datetime import datetime

# 从当前包的父级导入db
from .. import db

class Passenger(db.Model):
    __tablename__ = 'passengers'
    
    passenger_id = db.Column(
        db.String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment='乘客唯一标识符(UUID)'
    )
    id_card_number = db.Column(
        db.String(18),
        nullable=True,
        comment='身份证号码'
    )
    name = db.Column(
        db.String(50), 
        nullable=False,
        comment='乘客姓名'
    )
    gender = db.Column(
        db.String(1),
        nullable=True,
        comment='性别(M-男, F-女)'
    )
    birth_date = db.Column(
        db.Date,
        nullable=True,
        comment='出生日期'
    )
    phone_number = db.Column(
        db.String(20),
        nullable=True,
        comment='联系电话'
    )
    registered_face_feature = db.Column(
        db.LargeBinary,
        nullable=True,
        comment='注册的人脸特征向量'
    )
    registration_time = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        comment='注册时间'
    )
    blacklist_flag = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment='是否在黑名单中'
    )
    blacklist_reason = db.Column(
        db.Text,
        nullable=True,
        comment='加入黑名单的原因'
    )
    image_path = db.Column(
        db.String(255),
        nullable=True,
        comment='注册人脸的图像文件路径'
    )
    last_updated = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
        comment='最后更新时间'
    )

    def __repr__(self):
        return f'<Passenger {self.name}>'