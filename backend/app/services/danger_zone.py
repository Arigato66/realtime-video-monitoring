import os
import json
import numpy as np

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'danger_zone_config.json')

def load_danger_zone_config():
    """
    加载危险区域配置
    
    返回:
        tuple: (危险区域坐标, 安全距离, 停留时间阈值)
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                danger_zone = np.array(config['danger_zone'], np.int32)
                safety_distance = config.get('safety_distance', 100)
                loitering_threshold = config.get('loitering_threshold', 2.0)
                return danger_zone, safety_distance, loitering_threshold
        except Exception as e:
            print(f"Error loading config: {e}")
    
    # 默认值
    return np.array([[100, 700], [600, 700], [600, 800], [100, 800]], np.int32), 100, 2.0

def save_danger_zone_config(danger_zone, safety_distance, loitering_threshold):
    """
    保存危险区域配置
    
    参数:
        danger_zone: 危险区域坐标数组
        safety_distance: 安全距离
        loitering_threshold: 停留时间阈值
        
    返回:
        bool: 保存成功返回True，否则返回False
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            config = {
                'danger_zone': danger_zone.tolist(),
                'safety_distance': safety_distance,
                'loitering_threshold': loitering_threshold
            }
            json.dump(config, f)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# 初始化全局变量
DANGER_ZONE, SAFETY_DISTANCE, LOITERING_THRESHOLD = load_danger_zone_config()

# 需要检测的目标类别 (扩展到人和车辆)
TARGET_CLASSES = [0, 2, 7]  # person, car, truck 