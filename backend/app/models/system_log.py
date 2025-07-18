from app import db
from datetime import datetime
import uuid

class SystemLog(db.Model):
    __tablename__ = 'system_logs'

    log_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    log_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    log_level = db.Column(db.String(20), nullable=False)  # INFO/WARNING/ERROR/CRITICAL
    module = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.String(36), nullable=True)

    def __repr__(self):
        return f'<SystemLog {self.log_id} [{self.log_level}] {self.module}: {self.message[:30]}...>'

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'log_time': self.log_time.isoformat() + 'Z',
            'log_level': self.log_level,
            'module': self.module,
            'message': self.message,
            'details': self.details,
            'user_id': self.user_id
        } 