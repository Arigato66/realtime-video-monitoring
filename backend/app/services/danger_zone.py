import json
import os
import numpy as np
import logging

# V5: Use a JSON file as the single source of truth for the danger zone
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
ZONE_CONFIG_FILE = os.path.join(CONFIG_DIR, 'danger_zone.json')

# 确保配置目录存在
os.makedirs(CONFIG_DIR, exist_ok=True)

# 全局变量，作为内存缓存
DANGER_ZONE = []
SAFETY_DISTANCE = 50
LOITERING_THRESHOLD = 2.0
TARGET_CLASSES = [0] # 'person'

def load_config():
    """从JSON文件加载配置到全局变量中"""
    global DANGER_ZONE, SAFETY_DISTANCE, LOITERING_THRESHOLD
    try:
        if os.path.exists(ZONE_CONFIG_FILE):
            with open(ZONE_CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
                # 将点列表转换为numpy数组
                DANGER_ZONE = np.array(config_data.get('danger_zone', []))
                SAFETY_DISTANCE = config_data.get('safety_distance', 50)
                LOITERING_THRESHOLD = config_data.get('loitering_threshold', 2.0)
                logging.info(f"成功从 {ZONE_CONFIG_FILE} 加载危险区域配置。")
        else:
            # 如果文件不存在，使用默认值并创建文件
            DANGER_ZONE = np.array([[200, 200], [600, 200], [600, 400], [200, 400]])
            save_config()
            logging.warning(f"配置文件 {ZONE_CONFIG_FILE} 不存在，已使用默认值创建。")
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"加载或创建配置文件 {ZONE_CONFIG_FILE} 时出错: {e}, 使用默认值。")
        DANGER_ZONE = np.array([[200, 200], [600, 200], [600, 400], [200, 400]])
        SAFETY_DISTANCE = 50
        LOITERING_THRESHOLD = 2.0

def save_config():
    """将当前的全局配置变量保存到JSON文件"""
    try:
        config_data = {
            # 将numpy数组转换为原生列表以便JSON序列化
            'danger_zone': DANGER_ZONE.tolist() if isinstance(DANGER_ZONE, np.ndarray) else DANGER_ZONE,
            'safety_distance': SAFETY_DISTANCE,
            'loitering_threshold': LOITERING_THRESHOLD
        }
        with open(ZONE_CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
    except IOError as e:
        print(f"Error saving config file: {e}")

def update_danger_zone(new_zone):
    """更新危险区域并保存到文件"""
    global DANGER_ZONE
    DANGER_ZONE = np.array(new_zone)
    save_config()

def update_thresholds(new_safety_distance, new_loitering_threshold):
    """更新阈值并保存到文件"""
    global SAFETY_DISTANCE, LOITERING_THRESHOLD
    SAFETY_DISTANCE = new_safety_distance
    LOITERING_THRESHOLD = new_loitering_threshold
    save_config()

# 在模块首次加载时，立即从文件加载配置
load_config() 