from collections import defaultdict
import time
# --- 新增: 数据库集成与应用上下文 ---
from app import db, create_app
from app.models.alert import Alert
from datetime import datetime
# --- 结束新增 ---


# === 旧的基于内存的告警系统 (保留以兼容) ===

# 用于跟踪目标在危险区域内的停留时间
target_loitering_time = defaultdict(float)

# 上次检测的时间戳
last_detection_time = time.time()

# 用于存储告警信息 - 改为存储字典对象以包含完整信息
_memory_alerts = [] # 重命名以避免混淆

def reset_alerts():
    """重置所有内存中的警报信息"""
    global _memory_alerts, target_loitering_time, last_detection_time
    _memory_alerts = []
    target_loitering_time = defaultdict(float)
    last_detection_time = time.time()

def add_alert_memory(alert_message, event_type=None, details=None, snapshot_path=None):
    """添加新的警报信息到内存，支持完整的告警信息"""
    global _memory_alerts
    
    # 创建完整的告警对象
    alert_obj = {
        'id': len(_memory_alerts) + 1,  # 简单的ID生成
        'event_type': event_type or 'Memory Alert',
        'details': details or alert_message,
        'message': alert_message,
        'snapshot_path': snapshot_path,
        'timestamp': datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
        'status': 'unprocessed'
    }
    
    # 添加到内存列表（保持最近的50条告警）
    _memory_alerts.append(alert_obj)
    if len(_memory_alerts) > 50:
        _memory_alerts.pop(0)  # 移除最旧的告警
        
    print(f"内存告警已添加: {event_type} - {alert_message}")
    return alert_obj

def get_alerts():
    """获取当前内存中的所有警报信息"""
    global _memory_alerts
    print(f"get_alerts被调用，当前_memory_alerts长度: {len(_memory_alerts)}")
    print(f"_memory_alerts内容: {_memory_alerts}")
    return _memory_alerts

# --- 新的基于数据库的告警服务 ---

def create_alert(event_type, details, video_path=None, frame_snapshot_path=None):
    """
    创建新的告警记录到数据库。
    """
    try:
        new_alert = Alert(
            event_type=event_type,
            details=details,
            video_path=video_path,
            frame_snapshot_path=frame_snapshot_path,
            status='unprocessed'
        )
        db.session.add(new_alert)
        db.session.commit()
        print(f"数据库告警已创建: {event_type} - {details}")
        return new_alert
    except Exception as e:
        db.session.rollback()
        print(f"创建告警失败: {e}")
        return None

def get_all_alerts(page=1, per_page=20, status=None):
    """
    从数据库获取所有告警，支持分页和按状态过滤。
    """
    query = Alert.query
    if status:
        query = query.filter_by(status=status)
    
    # 按时间降序排列
    paginated_alerts = query.order_by(Alert.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return paginated_alerts

def update_alert_status(alert_id, new_status):
    """

    更新指定ID的告警状态。
    """
    alert = Alert.query.get(alert_id)
    if alert:
        try:
            alert.status = new_status
            db.session.commit()
            return alert
        except Exception as e:
            db.session.rollback()
            print(f"更新告警状态失败: {e}")
            return None
    return None

# --- 为了平滑过渡，我们暂时重命名旧的 add_alert ---
# --- 并让 detection.py 调用新的 create_alert ---
add_alert = add_alert_memory # 默认的 add_alert 仍然指向旧的内存版本

# (其余函数保持不变, 因为它们管理的是实时处理中的临时状态)

def update_loitering_time(target_id, time_diff):
    """更新目标在危险区域的停留时间"""
    global target_loitering_time
    target_loitering_time[target_id] += time_diff
    return target_loitering_time[target_id]

def reset_loitering_time(target_id):
    """重置目标的停留时间"""
    global target_loitering_time
    target_loitering_time[target_id] = 0

def get_loitering_time(target_id):
    """获取目标的停留时间"""
    return target_loitering_time[target_id]

def update_detection_time():
    """更新检测时间并返回时间差"""
    global last_detection_time
    current_time = time.time()
    time_diff = current_time - last_detection_time
    last_detection_time = current_time
    return time_diff