from app import db
from datetime import datetime

class BehaviorDetectionLog(db.Model):
    __tablename__ = 'behavior_detection_logs'
    
    detection_id = db.Column(db.String(36), primary_key=True)
    passenger_id = db.Column(db.String(36))  # 可选，如果可关联乘客
    camera_id = db.Column(db.String(36), nullable=False)
    detection_time = db.Column(db.DateTime, nullable=False)
    behavior_type = db.Column(db.String(50), nullable=False)
    confidence_score = db.Column(db.Float)
    risk_level = db.Column(db.String(20))
    location_id = db.Column(db.String(36), nullable=False)
    detection_area = db.Column(db.String(50))  # 新增字段，检测区域

    def __repr__(self):
        return f'<BehaviorDetection {self.detection_id} - {self.behavior_type}>'

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    alert_id = db.Column(db.String(36), primary_key=True)
    detection_id = db.Column(db.String(36), db.ForeignKey('behavior_detection_logs.detection_id'))
    alert_time = db.Column(db.DateTime, nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20))
    status = db.Column(db.String(20), default='unprocessed')
    camera_id = db.Column(db.String(36))
    location_id = db.Column(db.String(36))
    message = db.Column(db.Text)

    # 关系定义
    behavior_log = db.relationship('BehaviorDetectionLog', backref=db.backref('alerts', lazy=True))

    def __repr__(self):
        return f'<Alert {self.alert_id} - {self.alert_type}>'