from app import db
from datetime import datetime

class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='unprocessed', nullable=False) # e.g., 'unprocessed', 'viewed', 'resolved'
    video_path = db.Column(db.String(255), nullable=True)
    frame_snapshot_path = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Alert {self.id} [{self.event_type}] at {self.timestamp}>'

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'event_type': self.event_type,
            'details': self.details,
            'status': self.status,
            'video_path': self.video_path,
            'frame_snapshot_path': self.frame_snapshot_path
        } 