from app import db
from datetime import datetime
    
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
    

class DangerZoneConfig(db.Model):
    __tablename__ = 'danger_zone_config'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    location_id = db.Column(db.String(36), nullable=False, comment='位置ID')
    danger_zone = db.Column(db.JSON, nullable=False, comment='危险区域坐标')
    safety_distance = db.Column(db.Integer, default=100, comment='安全距离(像素)')
    loitering_threshold = db.Column(db.Float, default=2.0, comment='停留时间阈值(秒)')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    

from app import db

class Features(db.Model):
    """人脸特征表模型"""
    __tablename__ = 'features'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    person_name = db.Column(db.String(100), nullable=False, comment='人员姓名')
    
    # 128D特征向量字段
    feature_1 = db.Column(db.Float, nullable=False, comment='特征向量第1维')
    feature_2 = db.Column(db.Float, nullable=False, comment='特征向量第2维')
    feature_3 = db.Column(db.Float, nullable=False, comment='特征向量第3维')
    feature_4 = db.Column(db.Float, nullable=False, comment='特征向量第4维')
    feature_5 = db.Column(db.Float, nullable=False, comment='特征向量第5维')
    feature_6 = db.Column(db.Float, nullable=False, comment='特征向量第6维')
    feature_7 = db.Column(db.Float, nullable=False, comment='特征向量第7维')
    feature_8 = db.Column(db.Float, nullable=False, comment='特征向量第8维')
    feature_9 = db.Column(db.Float, nullable=False, comment='特征向量第9维')
    feature_10 = db.Column(db.Float, nullable=False, comment='特征向量第10维')
    feature_11 = db.Column(db.Float, nullable=False, comment='特征向量第11维')
    feature_12 = db.Column(db.Float, nullable=False, comment='特征向量第12维')
    feature_13 = db.Column(db.Float, nullable=False, comment='特征向量第13维')
    feature_14 = db.Column(db.Float, nullable=False, comment='特征向量第14维')
    feature_15 = db.Column(db.Float, nullable=False, comment='特征向量第15维')
    feature_16 = db.Column(db.Float, nullable=False, comment='特征向量第16维')
    feature_17 = db.Column(db.Float, nullable=False, comment='特征向量第17维')
    feature_18 = db.Column(db.Float, nullable=False, comment='特征向量第18维')
    feature_19 = db.Column(db.Float, nullable=False, comment='特征向量第19维')
    feature_20 = db.Column(db.Float, nullable=False, comment='特征向量第20维')
    feature_21 = db.Column(db.Float, nullable=False, comment='特征向量第21维')
    feature_22 = db.Column(db.Float, nullable=False, comment='特征向量第22维')
    feature_23 = db.Column(db.Float, nullable=False, comment='特征向量第23维')
    feature_24 = db.Column(db.Float, nullable=False, comment='特征向量第24维')
    feature_25 = db.Column(db.Float, nullable=False, comment='特征向量第25维')
    feature_26 = db.Column(db.Float, nullable=False, comment='特征向量第26维')
    feature_27 = db.Column(db.Float, nullable=False, comment='特征向量第27维')
    feature_28 = db.Column(db.Float, nullable=False, comment='特征向量第28维')
    feature_29 = db.Column(db.Float, nullable=False, comment='特征向量第29维')
    feature_30 = db.Column(db.Float, nullable=False, comment='特征向量第30维')
    feature_31 = db.Column(db.Float, nullable=False, comment='特征向量第31维')
    feature_32 = db.Column(db.Float, nullable=False, comment='特征向量第32维')
    feature_33 = db.Column(db.Float, nullable=False, comment='特征向量第33维')
    feature_34 = db.Column(db.Float, nullable=False, comment='特征向量第34维')
    feature_35 = db.Column(db.Float, nullable=False, comment='特征向量第35维')
    feature_36 = db.Column(db.Float, nullable=False, comment='特征向量第36维')
    feature_37 = db.Column(db.Float, nullable=False, comment='特征向量第37维')
    feature_38 = db.Column(db.Float, nullable=False, comment='特征向量第38维')
    feature_39 = db.Column(db.Float, nullable=False, comment='特征向量第39维')
    feature_40 = db.Column(db.Float, nullable=False, comment='特征向量第40维')
    feature_41 = db.Column(db.Float, nullable=False, comment='特征向量第41维')
    feature_42 = db.Column(db.Float, nullable=False, comment='特征向量第42维')
    feature_43 = db.Column(db.Float, nullable=False, comment='特征向量第43维')
    feature_44 = db.Column(db.Float, nullable=False, comment='特征向量第44维')
    feature_45 = db.Column(db.Float, nullable=False, comment='特征向量第45维')
    feature_46 = db.Column(db.Float, nullable=False, comment='特征向量第46维')
    feature_47 = db.Column(db.Float, nullable=False, comment='特征向量第47维')
    feature_48 = db.Column(db.Float, nullable=False, comment='特征向量第48维')
    feature_49 = db.Column(db.Float, nullable=False, comment='特征向量第49维')
    feature_50 = db.Column(db.Float, nullable=False, comment='特征向量第50维')
    feature_51 = db.Column(db.Float, nullable=False, comment='特征向量第51维')
    feature_52 = db.Column(db.Float, nullable=False, comment='特征向量第52维')
    feature_53 = db.Column(db.Float, nullable=False, comment='特征向量第53维')
    feature_54 = db.Column(db.Float, nullable=False, comment='特征向量第54维')
    feature_55 = db.Column(db.Float, nullable=False, comment='特征向量第55维')
    feature_56 = db.Column(db.Float, nullable=False, comment='特征向量第56维')
    feature_57 = db.Column(db.Float, nullable=False, comment='特征向量第57维')
    feature_58 = db.Column(db.Float, nullable=False, comment='特征向量第58维')
    feature_59 = db.Column(db.Float, nullable=False, comment='特征向量第59维')
    feature_60 = db.Column(db.Float, nullable=False, comment='特征向量第60维')
    feature_61 = db.Column(db.Float, nullable=False, comment='特征向量第61维')
    feature_62 = db.Column(db.Float, nullable=False, comment='特征向量第62维')
    feature_63 = db.Column(db.Float, nullable=False, comment='特征向量第63维')
    feature_64 = db.Column(db.Float, nullable=False, comment='特征向量第64维')
    feature_65 = db.Column(db.Float, nullable=False, comment='特征向量第65维')
    feature_66 = db.Column(db.Float, nullable=False, comment='特征向量第66维')
    feature_67 = db.Column(db.Float, nullable=False, comment='特征向量第67维')
    feature_68 = db.Column(db.Float, nullable=False, comment='特征向量第68维')
    feature_69 = db.Column(db.Float, nullable=False, comment='特征向量第69维')
    feature_70 = db.Column(db.Float, nullable=False, comment='特征向量第70维')
    feature_71 = db.Column(db.Float, nullable=False, comment='特征向量第71维')
    feature_72 = db.Column(db.Float, nullable=False, comment='特征向量第72维')
    feature_73 = db.Column(db.Float, nullable=False, comment='特征向量第73维')
    feature_74 = db.Column(db.Float, nullable=False, comment='特征向量第74维')
    feature_75 = db.Column(db.Float, nullable=False, comment='特征向量第75维')
    feature_76 = db.Column(db.Float, nullable=False, comment='特征向量第76维')
    feature_77 = db.Column(db.Float, nullable=False, comment='特征向量第77维')
    feature_78 = db.Column(db.Float, nullable=False, comment='特征向量第78维')
    feature_79 = db.Column(db.Float, nullable=False, comment='特征向量第79维')
    feature_80 = db.Column(db.Float, nullable=False, comment='特征向量第80维')
    feature_81 = db.Column(db.Float, nullable=False, comment='特征向量第81维')
    feature_82 = db.Column(db.Float, nullable=False, comment='特征向量第82维')
    feature_83 = db.Column(db.Float, nullable=False, comment='特征向量第83维')
    feature_84 = db.Column(db.Float, nullable=False, comment='特征向量第84维')
    feature_85 = db.Column(db.Float, nullable=False, comment='特征向量第85维')
    feature_86 = db.Column(db.Float, nullable=False, comment='特征向量第86维')
    feature_87 = db.Column(db.Float, nullable=False, comment='特征向量第87维')
    feature_88 = db.Column(db.Float, nullable=False, comment='特征向量第88维')
    feature_89 = db.Column(db.Float, nullable=False, comment='特征向量第89维')
    feature_90 = db.Column(db.Float, nullable=False, comment='特征向量第90维')
    feature_91 = db.Column(db.Float, nullable=False, comment='特征向量第91维')
    feature_92 = db.Column(db.Float, nullable=False, comment='特征向量第92维')
    feature_93 = db.Column(db.Float, nullable=False, comment='特征向量第93维')
    feature_94 = db.Column(db.Float, nullable=False, comment='特征向量第94维')
    feature_95 = db.Column(db.Float, nullable=False, comment='特征向量第95维')
    feature_96 = db.Column(db.Float, nullable=False, comment='特征向量第96维')
    feature_97 = db.Column(db.Float, nullable=False, comment='特征向量第97维')
    feature_98 = db.Column(db.Float, nullable=False, comment='特征向量第98维')
    feature_99 = db.Column(db.Float, nullable=False, comment='特征向量第99维')
    feature_100 = db.Column(db.Float, nullable=False, comment='特征向量第100维')
    feature_101 = db.Column(db.Float, nullable=False, comment='特征向量第101维')
    feature_102 = db.Column(db.Float, nullable=False, comment='特征向量第102维')
    feature_103 = db.Column(db.Float, nullable=False, comment='特征向量第103维')
    feature_104 = db.Column(db.Float, nullable=False, comment='特征向量第104维')
    feature_105 = db.Column(db.Float, nullable=False, comment='特征向量第105维')
    feature_106 = db.Column(db.Float, nullable=False, comment='特征向量第106维')
    feature_107 = db.Column(db.Float, nullable=False, comment='特征向量第107维')
    feature_108 = db.Column(db.Float, nullable=False, comment='特征向量第108维')
    feature_109 = db.Column(db.Float, nullable=False, comment='特征向量第109维')
    feature_110 = db.Column(db.Float, nullable=False, comment='特征向量第110维')
    feature_111 = db.Column(db.Float, nullable=False, comment='特征向量第111维')
    feature_112 = db.Column(db.Float, nullable=False, comment='特征向量第112维')
    feature_113 = db.Column(db.Float, nullable=False, comment='特征向量第113维')
    feature_114 = db.Column(db.Float, nullable=False, comment='特征向量第114维')
    feature_115 = db.Column(db.Float, nullable=False, comment='特征向量第115维')
    feature_116 = db.Column(db.Float, nullable=False, comment='特征向量第116维')
    feature_117 = db.Column(db.Float, nullable=False, comment='特征向量第117维')
    feature_118 = db.Column(db.Float, nullable=False, comment='特征向量第118维')
    feature_119 = db.Column(db.Float, nullable=False, comment='特征向量第119维')
    feature_120 = db.Column(db.Float, nullable=False, comment='特征向量第120维')
    feature_121 = db.Column(db.Float, nullable=False, comment='特征向量第121维')
    feature_122 = db.Column(db.Float, nullable=False, comment='特征向量第122维')
    feature_123 = db.Column(db.Float, nullable=False, comment='特征向量第123维')
    feature_124 = db.Column(db.Float, nullable=False, comment='特征向量第124维')
    feature_125 = db.Column(db.Float, nullable=False, comment='特征向量第125维')
    feature_126 = db.Column(db.Float, nullable=False, comment='特征向量第126维')
    feature_127 = db.Column(db.Float, nullable=False, comment='特征向量第127维')
    feature_128 = db.Column(db.Float, nullable=False, comment='特征向量第128维')
    
    # 索引定义
    __table_args__ = (
        db.Index('idx_person_name', 'person_name'),
        db.Index('idx_features_first_5', 'feature_1', 'feature_2', 'feature_3', 'feature_4', 'feature_5'),
    )