import os
import shutil
import uuid
import json
from datetime import datetime
import numpy as np
from deepface import DeepFace
import mysql.connector
from app.config import Config 

# --- 全局路径和模型配置 ---

# data目录位于项目的根目录下
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'data')
# 用于存储注册人脸图片的目录
FACES_DIR = os.path.join(DATA_DIR, 'registered_faces')
# DeepFace在第一次使用时会自动下载模型，这里我们定义要使用的模型
# ArcFace是目前最先进的模型之一，推荐使用
MODEL_NAME = "ArcFace"
# 使用余弦距离进行比较
DISTANCE_METRIC = "cosine"
# 为ArcFace模型设置的识别阈值，低于此值表示匹配。可以根据经验微调。
# 这是一个比face_recognition库更可靠的阈值。
RECOGNITION_THRESHOLD = 0.68 

# --- 初始化和辅助函数 ---

def _ensure_data_dirs_exist():
    """确保存储人脸的目录存在"""
    os.makedirs(FACES_DIR, exist_ok=True)

def _get_db_connection():
    """获取数据库连接"""
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            # 增加超时设置
            connect_timeout=10
        )
        return conn
    except mysql.connector.Error as err:
        print(f"数据库连接失败: {err}")
        return None

def preload_deepface_model():
    """
    在应用启动时预加载DeepFace模型。
    这可以避免在第一次API调用时出现长时间的延迟。
    """
    try:
        print("正在预加载DeepFace模型...")
        # DeepFace.build_model方法会加载模型并将其缓存到内存中
        DeepFace.build_model(MODEL_NAME)
        print("DeepFace模型预加载完成。")
    except Exception as e:
        print(f"预加载DeepFace模型失败: {e}")

# --- 核心人脸服务函数 ---

def register_new_face(image_path, name):
    """
    使用DeepFace从图像文件注册新的人脸。
    
    参数:
        image_path (str): 上传的临时图像文件的路径。
        name (str): 人员的姓名。
        
    返回:
        dict: 表示成功或失败的字典。
    """
    conn = _get_db_connection()
    if not conn:
        return {"status": "error", "message": "数据库连接失败。"}

    cursor = conn.cursor()

    try:
        # 1. 检查姓名是否已在数据库中注册
        cursor.execute("SELECT passenger_id FROM passengers WHERE name = %s", (name,))
        if cursor.fetchone():
            return {"status": "error", "message": f"'{name}' 已被注册。"}

        # 2. 使用DeepFace验证图像
        try:
            # extract_faces 会验证图像中是否有人脸，并进行裁剪和对齐
            face_objects = DeepFace.extract_faces(
                img_path=image_path, 
                enforce_detection=True, # 强制要求检测到人脸
                detector_backend='retinaface' # 使用更高精度的检测器
            )
            if len(face_objects) > 1:
                return {"status": "error", "message": "在图像中找到多个人脸。请使用只有单一人脸的照片。"}
        except ValueError as e:
            # 如果DeepFace未找到人脸，会抛出ValueError
            return {"status": "error", "message": f"在图像中未找到人脸或图像质量不佳: {e}"}

        # 3. 保存图像文件到永久存储
        person_dir = os.path.join(FACES_DIR, name)
        os.makedirs(person_dir, exist_ok=True)
        
        # 将图片保存为 jpg 格式以保持一致性
        new_image_filename = f"{uuid.uuid4()}.jpg"
        permanent_image_path = os.path.join(person_dir, new_image_filename)
        shutil.copy(image_path, permanent_image_path)
        
        # 4. 在数据库中创建记录 (不直接存储特征向量)
        passenger_id = str(uuid.uuid4())
        insert_sql = """
        INSERT INTO passengers (
            passenger_id, name, registration_time, blacklist_flag, last_updated, image_path
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_sql, (
            passenger_id, name, datetime.now(), False, datetime.now(), permanent_image_path
        ))
        conn.commit()
    
        # 5. 清理DeepFace的数据库缓存，强制重新索引
        db_path = os.path.join(FACES_DIR, "representations_arcface.pkl")
        if os.path.exists(db_path):
            os.remove(db_path)
    
        return {"status": "success", "message": f"'{name}' 的人脸已成功注册。"}

    except mysql.connector.Error as err:
        conn.rollback() # 出错时回滚
        return {"status": "error", "message": f"数据库操作失败: {err}"}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def identify_face_from_image(unknown_image_array):
    """
    使用DeepFace在已注册的人脸数据库中识别单个人脸。
    
    参数:
        unknown_image_array (np.ndarray): 从视频帧捕获的、包含人脸的图像数组 (BGR格式)。
        
    返回:
        tuple: (姓名, 距离)。如果未找到，则返回 ("Unknown", None)。
    """
    _ensure_data_dirs_exist()
    
    # 检查注册人脸目录是否为空
    if not any(os.scandir(FACES_DIR)):
        print("[诊断] 注册人脸目录为空，返回Stranger")
        return "Stranger", None

    try:
        # DeepFace.find 在指定目录中寻找最匹配的人脸
        # 它会处理所有特征提取和比较
        dfs = DeepFace.find(
            img_path=unknown_image_array,
            db_path=FACES_DIR,
            model_name=MODEL_NAME,
            distance_metric=DISTANCE_METRIC,
            enforce_detection=False, # 图像是已经裁剪好的人脸，无需再次检测
            silent=True # 禁用详细日志输出
        )
    
        # dfs 是一个 pandas DataFrame 列表
        if dfs and not dfs[0].empty:
            # --- 增加诊断日志 ---
            print(f"[诊断] DeepFace返回的列名: {dfs[0].columns.to_list()}")
            # --- 结束诊断日志 ---

            # 按距离排序并获取最佳匹配
            best_match = dfs[0].iloc[0]
            
            # 直接使用 'distance' 作为列名，因为DeepFace的find函数始终返回这个列名
            distance = best_match['distance']
            
            # 从路径中提取姓名（无论是否匹配，都先获取名字用于日志）
            identity_path = best_match['identity']
            name = os.path.basename(os.path.dirname(identity_path))
            
            # --- 添加诊断日志 ---
            print(f"[诊断] 找到最匹配人脸: {name}, 距离: {distance:.4f}, 阈值: {RECOGNITION_THRESHOLD}")
            # --- 结束诊断日志 ---

            # 检查是否低于阈值
            if distance < RECOGNITION_THRESHOLD:
                print(f"[诊断] 成功识别! 返回: {name}, 距离: {distance:.4f}")
                return name, float(distance)
            else:
                print(f"[诊断] 距离 {distance:.4f} 超过阈值 {RECOGNITION_THRESHOLD}，返回Stranger")
        else:
            print("[诊断] DeepFace未找到任何匹配人脸")

    except Exception as e:
        # 在视频流中，我们不希望因为单帧错误而崩溃
        # 但在调试阶段，我们需要看到错误信息
        print(f"[错误] DeepFace在识别时发生异常: {e}")
        # pass # 暂时禁用静默处理

    return "Stranger", None


def get_all_registered_names():
    """从数据库返回所有已注册姓名的列表"""
    conn = _get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM passengers ORDER BY name")
        names = [row[0] for row in cursor.fetchall()]
        return names
    except mysql.connector.Error as err:
        print(f"从数据库获取姓名列表失败: {err}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
   

def delete_face(name):
    """
    按姓名删除已注册的人脸（包括图片文件和数据库记录）。
    """
    conn = _get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # 1. 从数据库删除记录
        cursor.execute("DELETE FROM passengers WHERE name = %s", (name,))
        if cursor.rowcount == 0:
            # 如果数据库中没有这个人，直接返回
            return False
        
        conn.commit()

        # 2. 从文件系统删除对应的图片目录
        person_dir = os.path.join(FACES_DIR, name)
        if os.path.exists(person_dir):
            shutil.rmtree(person_dir)
            
        # 3. 清理DeepFace的数据库缓存，强制重新索引
        db_path = os.path.join(FACES_DIR, "representations_arcface.pkl")
        if os.path.exists(db_path):
            os.remove(db_path)
            
        return True
        
    except (mysql.connector.Error, OSError) as err:
        print(f"删除人脸 '{name}' 失败: {err}")
        # 如果出错，可能需要手动回滚或处理
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- 应用启动时执行 ---

# 确保目录存在
_ensure_data_dirs_exist()
# 预加载模型，避免首次请求延迟
preload_deepface_model() 