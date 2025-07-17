import cv2
import numpy as np
from ultralytics import YOLO
from sqlalchemy.exc import IntegrityError
import os
# --- V4: 修正模块导入问题 ---
from app.services import danger_zone as danger_zone_service
from app.services.danger_zone import (
    DANGER_ZONE as danger_zone,  # 直接使用全局变量
    SAFETY_DISTANCE as safety_distance,
    LOITERING_THRESHOLD as loitering_threshold,
    TARGET_CLASSES,
    load_config
)

# 确保配置已加载
load_config()
# --- 结束 V4 ---
from app.services.alerts import (
    add_alert, update_loitering_time, reset_loitering_time, get_loitering_time,
    update_detection_time, get_alerts, reset_alerts
)
from app.utils.geometry import point_in_polygon, distance_to_polygon



from app.services import system_state
from app.services.smoking_detection_service import SmokingDetectionService
import time
from concurrent.futures import ThreadPoolExecutor
from app.services import violenceDetect
# --- 新增：导入config模块以访问其状态 ---
from app.routes import config as config_state
# --- 结束新增 ---
from app.models import BehaviorDetectionLog, Alert  # 需要创建对应的模型
import uuid
from datetime import datetime
from app import db
from collections import defaultdict  # 新增导入
from sqlalchemy.exc import IntegrityError
import io
import os
from PIL import Image
from app.services.dlib_service import get_dlib_face_service

# 常量定义（补充缺失的常量）
LOITERING_THRESHOLD = 2.0  # 停留时间阈值（秒）
SAFETY_DISTANCE = 100  # 安全距离（像素）
# --- 模型管理 (使用相对路径) ---
# 路径是相对于 backend/app/services/ 目录的
# '..' 回退到 backend/app/
# '../..' 回退到 backend/
# '../../..' 回退到项目根目录
BASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..')
MODEL_DIR = os.path.join(BASE_PATH, 'yolo-Weights') # 统一存放在 yolo-Weights 文件夹

POSE_MODEL_PATH = os.path.join(MODEL_DIR, "yolov8s-pose.pt")
OBJECT_MODEL_PATH = os.path.join(MODEL_DIR, "yolov8n.pt")
FACE_MODEL_PATH = os.path.join(MODEL_DIR, "yolov8n-face-lindevs.pt")
SMOKING_MODEL_PATH = os.path.join(MODEL_DIR, "smoking_detection.pt")

from app.models import (
    DangerZoneConfig, BehaviorDetectionLog, Alert,
)
from datetime import datetime, timedelta
import uuid

# 全局变量来持有加载的模型
pose_model = None
object_model = None
face_model = None
smoking_model = None

def get_pose_model():
    """获取姿态估计模型实例"""
    global pose_model
    if pose_model is None:
        pose_model = YOLO(POSE_MODEL_PATH)
    return pose_model

def get_object_model():
    """获取通用目标检测模型实例"""
    global object_model
    if object_model is None:
        object_model = YOLO(OBJECT_MODEL_PATH)
    return object_model

def get_face_model():
    """获取人脸检测和追踪模型实例"""
    global face_model
    if face_model is None:
        face_model = YOLO(FACE_MODEL_PATH)
    return face_model

def get_smoking_model():
    """获取抽烟检测模型实例"""
    global smoking_model
    if smoking_model is None:
        smoking_model = SmokingDetectionService(model_path=SMOKING_MODEL_PATH)
    return smoking_model

# (保留get_model函数以兼容旧代码，但现在让它返回目标检测模型)
def get_model():
    """获取YOLO模型实例（默认为目标检测）"""
    return get_object_model()

# 用于存储每个人姿态历史信息
pose_history = {}
FALL_DETECTION_THRESHOLD_SPEED = -15  # 重心Y坐标速度阈值 (像素/帧)
FALL_DETECTION_THRESHOLD_STATE_FRAMES = 10 # 确认跌倒状态需要的帧数
# 常量定义（补充缺失的常量）
LOITERING_THRESHOLD = 2.0  # 停留时间阈值（秒）
SAFETY_DISTANCE = 100  # 安全距离（像素）
OBJECT_MODEL_PATH = "yolov8n.pt"  # 替换为实际模型路径

def process_image(filepath, uploads_dir):
    """
    处理单张图片
    
    参数:
        filepath: 图片文件路径
        uploads_dir: 上传文件目录
        
    返回:
        dict: 包含处理结果的字典
    """
   
    dlib_face_service = get_dlib_face_service()
    # 重置警报，以防上次调用的状态残留
    reset_alerts()
    
    # 读取图片
    img = cv2.imread(filepath)
    if img is None:
        return {"status": "error", "message": "Failed to load image"}, 500
    
    res_plotted = img.copy() # Start with a copy of the original image
    
    # 默认使用默认摄像头和位置（可根据需要修改）
    camera_id = "default_camera"
    location_id = "default_location"
    
    # --- 修复：为静态图片处理添加模式判断 ---
    if system_state.DETECTION_MODE == 'face_only':
        # 在人脸识别模式下，直接调用人脸处理函数
        # 注意：对于静态图片，我们没有追踪状态，所以创建一个临时的state
        face_model_local = get_face_model()
        state = {'face_model': face_model_local}
        process_faces_only(res_plotted, 1, state) # frame_count 设为 1
    
    elif system_state.DETECTION_MODE == 'smoking_detection':
        # --- FIX: Use fresh, local model instances for stateless image processing ---
        face_model_local = YOLO(FACE_MODEL_PATH)
        object_model_local = YOLO(OBJECT_MODEL_PATH)
        smoking_model = get_smoking_model() # This service is a stateless wrapper, it's fine

        face_results = face_model_local.predict(img, verbose=False)
        person_results = object_model_local.predict(img, classes=[0], verbose=False)

        # Call the processing function with the results, which draws on the frame
        # 补充 camera_id 和 location_id 参数
        res_plotted, detected_count = process_smoking_detection_hybrid(
            res_plotted, 
            person_results, 
            face_results, 
            smoking_model,
            camera_id,
            location_id
        )

    elif system_state.DETECTION_MODE == 'violence_detection':
        # 暴力检测仅支持视频
        return {"status": "error", "message": "暴力检测仅支持视频文件"}, 400

    else:
          # Default execution path must also use a fresh, local instance
        model_local = YOLO(OBJECT_MODEL_PATH)
        detections = model_local.predict(img)
        res_plotted = detections[0].plot()
        
        # Draw danger zone overlay on the plotted results
        # --- V4: 使用模块访问最新的 DANGER_ZONE ---
        danger_zone_pts = np.array(danger_zone_service.DANGER_ZONE).reshape((-1, 1, 2))
        overlay = res_plotted.copy()
        cv2.fillPoly(overlay, [danger_zone_pts], (0, 0, 255))
        cv2.addWeighted(overlay, 0.4, res_plotted, 0.6, 0, res_plotted)
        cv2.polylines(res_plotted, [danger_zone_pts], True, (0, 0, 255), 3)

    # 保存处理后的图像
    output_filename = 'processed_' + os.path.basename(filepath)
    output_path = os.path.join(uploads_dir, output_filename)
    print(f"保存处理后的图像到: {output_path}")
    cv2.imwrite(output_path, res_plotted)
    
    # 使用相对URL路径
    output_url = f"/api/files/{output_filename}"
    print(f"图像处理完成，输出URL: {output_url}")
    
    return {
        "status": "success",
        "media_type": "image",
        "file_url": output_url,
        "alerts": get_alerts()
    }

def process_video(filepath, uploads_dir):
    """完整视频处理函数，支持多模式检测并优化跌倒记录"""
    # 重置警报和缓存

    dlib_face_service = get_dlib_face_service()
    reset_alerts()
    fall_events = []  # 局部变量：缓存跌倒事件（避免全局变量冲突）
    
    # 创建输出视频路径
    output_filename = 'processed_' + os.path.basename(filepath)
    output_path = os.path.join(uploads_dir, output_filename)
    print(f"处理视频: {filepath}")
    print(f"输出路径: {output_path}")
    
    # 打开视频
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        return {"status": "error", "message": "Failed to open video"}, 500
    
    # 获取视频属性
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # 创建视频写入器（优先H.264，失败则回退）
    try:
        fourcc = cv2.VideoWriter_fourcc(*"avc1")  # H.264编码器
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        if not out.isOpened():
            print("警告: H.264编码器不可用，回退到MJPG")
            output_path = output_path.replace(".mp4", ".avi")
            output_filename = output_filename.replace(".mp4", ".avi")
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    except Exception as e:
        print(f"视频编码器错误: {e}，使用无损编码")
        output_path = output_path.replace(".mp4", ".avi")
        output_filename = output_filename.replace(".mp4", ".avi")
        fourcc = cv2.VideoWriter_fourcc(*"DIB ")
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    
    # 初始化模型（为当前任务创建独立实例）
    object_model_local = YOLO(OBJECT_MODEL_PATH)
    pose_model_local = YOLO(POSE_MODEL_PATH)
    face_model_local = YOLO(FACE_MODEL_PATH)
    
    # 上下文参数（与数据库记录关联）
    camera_id = "default_camera"
    location_id = "default_location"
    face_recognition_cache = {}  # 人脸识别缓存
    
    # 处理视频帧
    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"开始处理视频，总帧数: {total_frames}")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break  # 视频处理结束
            
        frame_count += 1
        if frame_count % 10 == 0:  # 每10帧打印进度
            progress = (frame_count / total_frames) * 100
            print(f"处理视频: {progress:.1f}% 完成")
        
        # 计算时间差
        time_diff = update_detection_time()
        
        # 加载最新配置
        danger_zone_service.load_config()
        
        # 复制帧用于处理
        processed_frame = frame.copy()

        # 根据检测模式处理
        if system_state.DETECTION_MODE == 'object_detection':
            # 目标追踪
            results = object_model_local.track(processed_frame, persist=True)
            
            # 绘制危险区域（非编辑模式）
            if not config_state.edit_mode:
                overlay = processed_frame.copy()
                danger_zone_pts = np.array(danger_zone_service.DANGER_ZONE).reshape((-1, 1, 2))
                cv2.fillPoly(overlay, [danger_zone_pts], (0, 255, 255))  # 黄色填充
                cv2.addWeighted(overlay, 0.4, processed_frame, 0.6, 0, processed_frame)
                cv2.polylines(processed_frame, [danger_zone_pts], True, (0, 255, 255), 3)
                
                # 危险区域文字标注
                danger_zone_center = np.mean(danger_zone_service.DANGER_ZONE, axis=0, dtype=np.int32)
                cv2.putText(
                    processed_frame, 
                    "Danger Zone", 
                    (danger_zone_center[0] - 60, danger_zone_center[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1.2, 
                    (255, 255, 255), 
                    3
                )
                
                # 处理目标检测结果（传递camera_id和location_id）
                process_object_detection_results(
                    results, 
                    processed_frame, 
                    time_diff, 
                    frame_count,
                    camera_id="default_camera",  # 新增：传递摄像头ID
                    location_id="default_location"  # 新增：传递位置ID
                )
            
            # 处理检测结果
            process_object_detection_results(results, processed_frame, time_diff, frame_count)
        
        elif system_state.DETECTION_MODE == 'fall_detection':
            # 姿态估计追踪
            pose_results = pose_model_local.track(processed_frame, persist=True)
            # 处理跌倒检测（缓存事件）
            process_pose_estimation_results(
                pose_results, 
                processed_frame, 
                time_diff, 
                frame_count,
                camera_id=camera_id,
                location_id=location_id,
                fall_events=fall_events  # 传递事件列表
            )
        
        elif system_state.DETECTION_MODE == 'face_only':
            # 人脸识别
            if 'face_model' not in face_recognition_cache:
                face_recognition_cache['face_model'] = face_model_local
            process_faces_only(processed_frame, frame_count, face_recognition_cache)
        
        elif system_state.DETECTION_MODE == 'smoking_detection':
            # 吸烟检测
            face_results = face_model_local.predict(processed_frame, verbose=False)
            person_results = object_model_local.track(
                processed_frame, 
                persist=True, 
                classes=[0],  # 只检测人
                verbose=False
            )
            # 调用吸烟检测函数（已实现数据库记录）
            processed_frame, detected_count = process_smoking_detection_hybrid(
                processed_frame, 
                person_results, 
                face_results, 
                get_smoking_model(),
                camera_id=camera_id,
                location_id=location_id
            )
        
        elif system_state.DETECTION_MODE == 'violence_detection':
            # 暴力检测（带数据库记录）
            return process_violence_detection(
                filepath, 
                uploads_dir, 
                camera_id=camera_id, 
                location_id=location_id
            )
        
        # 写入处理后的帧（确保格式正确）
        if processed_frame is not None:
            if len(processed_frame.shape) == 2:  # 灰度转BGR
                processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_GRAY2BGR)
            elif processed_frame.shape[2] == 4:  # RGBA转BGR
                processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_RGBA2BGR)
            
            out.write(processed_frame)
    
    # 释放资源
    cap.release()
    out.release()
    print(f"视频帧写入完成: {output_path}")
    
    # 视频处理完成后，统一记录跌倒事件（去重后）
    if fall_events and system_state.DETECTION_MODE == 'fall_detection':
        # 按人员分组，每组取最严重事件（角度最小）
        person_events = defaultdict(list)
        for event in fall_events:
            person_events[event['person_id']].append(event)
        
        # 提取每组最严重事件
        severe_events = []
        for events in person_events.values():
            events.sort(key=lambda x: x['angle'])  # 角度越小越严重
            severe_events.append(events[0])
        
        # 整体最严重事件
        severe_events.sort(key=lambda x: x['angle'])
        most_severe_fall = severe_events[0]
        
        # 记录到数据库
        log_fall_detection(
            camera_id=camera_id,
            location_id=location_id,
            person_id=most_severe_fall['person_id'],
            angle=most_severe_fall['angle'],
            velocity_y=most_severe_fall['velocity_y']
        )
        print(f"视频处理完成，记录 {len(fall_events)} 次跌倒事件中的最严重一次")
    
    # 返回结果
    output_url = f"/api/files/{output_filename}"
    print(f"视频处理完成，输出URL: {output_url}")
    
    return {
        "status": "success",
        "media_type": "video",
        "file_url": output_url,
        "alerts": get_alerts()
    }


def process_smoking_detection_hybrid(frame, person_results, face_results, smoking_model, camera_id, location_id):
    """
    改进的混合吸烟检测方法，包含数据库记录功能
    """
    frame_h, frame_w = frame.shape[:2]
    detected_count = 0

    # 获取检测结果
    person_boxes = person_results[0].boxes.xyxy.cpu().numpy().astype(int) if hasattr(person_results[0].boxes, 'xyxy') else []
    face_boxes = face_results[0].boxes.xyxy.cpu().numpy().astype(int) if hasattr(face_results[0].boxes, 'xyxy') else []

    processed_person_indices = set()

    # 高置信度检测通道（基于面部区域）
    for f_box in face_boxes:
        fx1, fy1, fx2, fy2 = f_box
        face_w, face_h = fx2 - fx1, fy2 - fy1
        face_center_x = fx1 + face_w // 2

        for i, p_box in enumerate(person_boxes):
            if i in processed_person_indices:
                continue
                
            px1, _, px2, _ = p_box
            if px1 < face_center_x < px2:
                roi_x1 = max(0, fx1 - face_w // 2)
                roi_y1 = max(0, fy1 - face_h // 2)
                roi_x2 = min(frame_w, fx2 + face_w // 2)
                roi_y2 = min(frame_h, fy2 + face_h)
                
                roi_crop = frame[roi_y1:roi_y2, roi_x1:roi_x2]
                if roi_crop.size == 0: 
                    continue

                smoking_results = smoking_model.predict(roi_crop, imgsz=640, verbose=False)
                if len(smoking_results[0].boxes) > 0:
                    # 获取最高置信度的检测结果
                    max_conf_box = max(smoking_results[0].boxes, key=lambda x: x.conf)
                    confidence = max_conf_box.conf.item()
                    
                    # 记录到数据库
                    log_smoking_behavior(
                        camera_id=camera_id,
                        location_id=location_id,
                        behavior_type="Smoking",
                        confidence_score=confidence,
                        detection_area="face_region"
                    )
                    
                    # 可视化标记
                    for s_box in smoking_results[0].boxes:
                        s_xyxy = s_box.xyxy.cpu().numpy().astype(int)[0]
                        abs_x1, abs_y1 = s_xyxy[0] + roi_x1, s_xyxy[1] + roi_y1
                        abs_x2, abs_y2 = s_xyxy[2] + roi_x1, s_xyxy[3] + roi_y1
                        cv2.rectangle(frame, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 0, 255), 2)
                        cv2.putText(
                            frame, 
                            f"Smoking {s_box.conf.item():.2f}",  # 添加 .item() 转换为浮点数
                            (abs_x1, abs_y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.7, 
                            (0, 0, 255), 
                            2
                        )
                    
                    detected_count += 1
                
                processed_person_indices.add(i)
                break

    # 低置信度检测通道（基于上半身区域）
    for i, p_box in enumerate(person_boxes):
        if i in processed_person_indices:
            continue

        px1, py1, px2, py2 = p_box
        upper_body_y2 = py1 + int((py2 - py1) * 0.6)
        upper_body_crop = frame[py1:upper_body_y2, px1:px2]
        if upper_body_crop.size == 0: 
            continue

        smoking_results = smoking_model.predict(upper_body_crop, imgsz=1024, verbose=False)
        if len(smoking_results[0].boxes) > 0:
            # 获取最高置信度的检测结果
            max_conf_box = max(smoking_results[0].boxes, key=lambda x: x.conf)
            confidence = max_conf_box.conf.item()
            
            # 记录到数据库
            log_smoking_behavior(
                camera_id=camera_id,
                location_id=location_id,
                behavior_type="Smoking",
                confidence_score=confidence,
                detection_area="upper_body"
            )
            
            # 可视化标记
            for s_box in smoking_results[0].boxes:
                s_xyxy = s_box.xyxy.cpu().numpy().astype(int)[0]
                abs_x1, abs_y1 = s_xyxy[0] + px1, s_xyxy[1] + py1
                abs_x2, abs_y2 = s_xyxy[2] + px1, s_xyxy[3] + py1
                cv2.rectangle(frame, (abs_x1, abs_y1), (abs_x2, abs_y2), (0, 165, 255), 2)
                cv2.putText(
                frame, 
                f"Smoking? {s_box.conf.item():.2f}",  # 添加 .item() 转换为浮点数
                (abs_x1, abs_y1 - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (0, 165, 255), 
                2
            )
            detected_count += 1

    return frame, detected_count

def log_smoking_behavior(camera_id, location_id, behavior_type, confidence_score, detection_area):
    """记录吸烟行为到数据库"""
    try:
        # 生成唯一ID和时间戳
        detection_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        # 确定风险等级
        risk_level = "high" if confidence_score > 0.7 else "medium" if confidence_score > 0.5 else "low"
        
        # 创建行为检测记录
        behavior_log = BehaviorDetectionLog(
            detection_id=detection_id,
            camera_id=camera_id,
            location_id=location_id,
            detection_time=current_time,
            behavior_type=behavior_type,
            confidence_score=confidence_score,
            risk_level=risk_level,
            detection_area=detection_area
        )
        
        # 创建关联的报警记录
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            detection_id=detection_id,
            alert_time=current_time,
            alert_type="high_risk_behavior",
            severity=risk_level,
            status="unprocessed",
            camera_id=camera_id,
            location_id=location_id,
            message=f"检测到吸烟行为 ({detection_area}区域), 置信度: {confidence_score:.2f}"
        )
        
        # 添加到数据库会话并提交
        db.session.add(behavior_log)
        db.session.add(alert)
        db.session.commit()
        
    except Exception as e:
        # 记录错误但不要中断程序
        print(f"数据库记录失败: {str(e)}")
        db.session.rollback()

       
def process_object_detection_results(results, frame, time_diff, frame_count):
    """
    处理通用目标检测结果（危险区域、徘徊等）
    (这是您之前的 process_detection_results 函数，已重命名并保留)
    """
    # --- V3 混合驱动：在编辑模式下，跳过所有危险区域的闯入/靠近检测逻辑 ---
    if config_state.edit_mode:
        # 仍然需要绘制检测框，所以我们只跳过危险区域的部分
        if results and results[0].boxes is not None and hasattr(results[0].boxes, 'id') and results[0].boxes.id is not None:
            boxes = results[0].boxes.cpu().numpy()
            # 绘制YOLOv8的默认结果（框和ID）
            frame[:] = results[0].plot()
        return # 直接返回，不执行后续的危险区域判断
    # --- 结束新增 ---

    # 如果有追踪结果，在画面上显示追踪ID和危险区域告警
    if hasattr(results[0], 'boxes') and hasattr(results[0].boxes, 'id') and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.int().cpu().numpy()
        classes = results[0].boxes.cls.cpu().numpy()
        
        # 获取类别名称
        class_names = results[0].names
        
        for box, id, cls in zip(boxes, ids, classes):
            x1, y1, x2, y2 = box
            class_name = class_names[int(cls)]
            
            # # 只处理指定类别的目标 (暂时移除此限制，以检测所有物体)
            # if int(cls) in TARGET_CLASSES:
            # 在目标检测模式下，我们不再进行人脸识别，直接使用类别名
            display_name = class_name
            
            # 计算目标的底部中心点
            foot_point = (int((x1 + x2) / 2), int(y2))
            
            # 检查是否在危险区域内
            # --- V4: 使用模块访问最新的 DANGER_ZONE ---
            in_danger_zone = point_in_polygon(foot_point, danger_zone_service.DANGER_ZONE)
            
            # 计算到危险区域的距离
            # --- V4: 使用模块访问最新的 DANGER_ZONE ---
            distance = distance_to_polygon(foot_point, danger_zone_service.DANGER_ZONE)
            
            # 确定标签颜色和告警状态
            label_color = (0, 255, 0)  # 默认绿色
            alert_status = None
            
            # 如果在危险区域内，更新停留时间
            if in_danger_zone:
                loitering_time = update_loitering_time(id, time_diff)
                
                # 如果停留时间超过阈值，标记为红色并记录告警
                if loitering_time >= LOITERING_THRESHOLD:
                    # 使用纯红色
                    label_color = (0, 0, 255)  # BGR格式：红色
                    alert_status = f"ID:{id} ({display_name}) staying in danger zone for {loitering_time:.1f}s"
                    add_alert(alert_status)
                else:
                    # 根据停留时间从橙色到红色渐变
                    ratio = min(1.0, loitering_time / LOITERING_THRESHOLD)
                    # 从橙色(0,165,255)到红色(0,0,255)
                    label_color = (0, int(165 * (1 - ratio)), 255)
            else:
                # 如果不在区域内，重置停留时间
                reset_loitering_time(id)

                # 如果距离小于安全距离，根据距离设置颜色从绿色到黄色
                if distance < SAFETY_DISTANCE:
                    # 计算距离比例
                    ratio = distance / SAFETY_DISTANCE
                    # 从黄色(0,255,255)到绿色(0,255,0)渐变
                    label_color = (0, 255, int(255 * (1 - ratio)))
                    
                    alert_status = f"ID:{id} ({display_name}) too close to danger zone ({distance:.1f}px)"
                    add_alert(alert_status)
            
            # 在每个目标上方显示ID和类别
            label = f"ID:{id} {display_name}"

            if in_danger_zone:
                label += f" time:{get_loitering_time(id):.1f}s"
            elif distance < SAFETY_DISTANCE:
                label += f" dist:{distance:.1f}px"
            
            # 根据危险程度调整边框粗细
            thickness = 2  # 默认粗细
            if in_danger_zone:
                # 在危险区域内，根据停留时间增加边框粗细
                thickness = max(2, int(4 * min(1.0, get_loitering_time(id) / LOITERING_THRESHOLD)))
                
                # 如果停留时间超过阈值，添加警告标记
                if get_loitering_time(id) >= LOITERING_THRESHOLD:
                    # 在目标上方绘制警告三角形
                    triangle_height = 20
                    triangle_base = 20
                    triangle_center_x = int((x1 + x2) / 2)
                    triangle_top_y = int(y1) - 25
                    
                    triangle_pts = np.array([
                        [triangle_center_x - triangle_base//2, triangle_top_y + triangle_height],
                        [triangle_center_x + triangle_base//2, triangle_top_y + triangle_height],
                        [triangle_center_x, triangle_top_y]
                    ], np.int32)
                    
                    cv2.fillPoly(frame, [triangle_pts], (0, 0, 255))  # 红色填充
                    cv2.polylines(frame, [triangle_pts], True, (0, 0, 0), 1)  # 黑色边框
                    
                    # 在三角形中绘制感叹号
                    cv2.putText(frame, "!", 
                                (triangle_center_x - 3, triangle_top_y + triangle_height - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            elif distance < SAFETY_DISTANCE:
                # 不在危险区域但接近时，根据距离增加边框粗细
                thickness = max(1, int(3 * (1 - distance / SAFETY_DISTANCE)))
            
            # 绘制边框
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), label_color, thickness)
            
            # 绘制标签背景
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(frame, (int(x1), int(y1) - h - 10), (int(x1) + w, int(y1) - 5), label_color, -1)
            
            # 绘制标签文本
            cv2.putText(frame, label, (int(x1), int(y1)-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 在目标底部位置画一个点
            foot_point = (int((x1 + x2) / 2), int(y2))
            cv2.circle(frame, foot_point, 5, label_color, -1)
            
            # 如果不在危险区域内但距离小于安全距离的2倍，绘制到危险区域的连接线
            if not in_danger_zone and distance < SAFETY_DISTANCE * 2:
                draw_distance_line(frame, foot_point, distance)

def draw_distance_line(frame, foot_point, distance):
    """
    绘制从目标到危险区域的连接线
    
    参数:
        frame: 当前视频帧
        foot_point: 目标的底部中心点
        distance: 目标到危险区域的距离
    """
    # 找到危险区域上最近的点
    min_dist = float('inf')
    closest_point = None
    # --- V4: 使用模块访问最新的 DANGER_ZONE ---
    for i in range(len(danger_zone_service.DANGER_ZONE)):
        p1 = danger_zone_service.DANGER_ZONE[i]
        p2 = danger_zone_service.DANGER_ZONE[(i + 1) % len(danger_zone_service.DANGER_ZONE)]
        
        # 计算点到线段的最近点
        line_vec = p2 - p1
        line_len = np.linalg.norm(line_vec)
        line_unitvec = line_vec / line_len
        
        pt_vec = np.array(foot_point) - p1
        proj_len = np.dot(pt_vec, line_unitvec)
        
        if proj_len < 0:
            closest_pt = p1
        elif proj_len > line_len:
            closest_pt = p2
        else:
            closest_pt = p1 + line_unitvec * proj_len
        
        d = np.linalg.norm(np.array(foot_point) - closest_pt)
        if d < min_dist:
            min_dist = d
            closest_point = tuple(map(int, closest_pt))
    
    # 绘制从目标到危险区域的连接线，颜色根据距离变化
    if closest_point:
        # 根据距离调整线条粗细和样式
        line_thickness = max(1, int(3 * (1 - distance / (SAFETY_DISTANCE * 2))))
        
        # 绘制主线
        label_color = (0, 255, int(255 * (1 - distance / SAFETY_DISTANCE))) if distance < SAFETY_DISTANCE else (0, 255, 0)
        cv2.line(frame, foot_point, closest_point, label_color, line_thickness)
        
        # 在线上显示距离数字
        mid_point = ((foot_point[0] + closest_point[0]) // 2, 
                    (foot_point[1] + closest_point[1]) // 2)
        cv2.putText(frame, f"{distance:.1f}px", 
                    (mid_point[0] + 5, mid_point[1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, label_color, 1)
        
        # 如果距离小于安全距离，添加虚线效果
        if distance < SAFETY_DISTANCE:
            # 计算线段长度
            line_length = np.linalg.norm(np.array(foot_point) - np.array(closest_point))
            # 计算单位向量
            if line_length > 0:
                unit_vector = (np.array(closest_point) - np.array(foot_point)) / line_length
                # 绘制短线段形成虚线效果
                for i in range(0, int(line_length), 10):
                    start_point = np.array(foot_point) + i * unit_vector
                    end_point = start_point + 5 * unit_vector
                    start_point = tuple(map(int, start_point))
                    end_point = tuple(map(int, end_point))
                    cv2.line(frame, start_point, end_point, (0, 0, 255), line_thickness + 1)               

# 全局变量：存储检测到的跌倒事件
fall_events = []

def process_pose_estimation_results(results, frame, time_diff, frame_count, camera_id, location_id, fall_events):
    """处理姿态估计结果，缓存跌倒事件到列表（不立即写入数据库）"""
    if hasattr(results[0], 'boxes') and hasattr(results[0].boxes, 'id') and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.int().cpu().numpy()
        keypoints = results[0].keypoints.xy.cpu().numpy()

        # 绘制基本骨架和边界框
        frame[:] = results[0].plot()

        for person_id, box, kps in zip(ids, boxes, keypoints):
            velocity_y = 0
            angle = 90  # 默认为垂直

            # 1. 计算人体中心点（质心）
            visible_kps = kps[kps[:, 1] > 0]  # 过滤可见关键点
            if len(visible_kps) > 4:
                centroid_y = np.mean(visible_kps[:, 1])

                # 2. 更新历史记录并计算垂直速度
                if person_id in pose_history:
                    prev_centroid_y, _ = pose_history[person_id][-1]
                    velocity_y = centroid_y - prev_centroid_y
                    
                    pose_history[person_id].append((centroid_y, velocity_y))
                    if len(pose_history[person_id]) > 30:
                        pose_history[person_id].pop(0)  # 保持历史记录长度

                    # 3. 判断快速下坠（速度为正表示向下）
                    if velocity_y > 15:  # 可根据场景调整阈值
                        # 4. 计算身体主干角度判断跌倒
                        left_shoulder, right_shoulder = kps[5], kps[6]
                        left_hip, right_hip = kps[11], kps[12]

                        # 确保关键骨骼点可见
                        if left_shoulder[1] > 0 and right_shoulder[1] > 0 and left_hip[1] > 0 and right_hip[1] > 0:
                            shoulder_center = (left_shoulder + right_shoulder) / 2
                            hip_center = (left_hip + right_hip) / 2
                            body_vector = hip_center - shoulder_center
                            
                            # 避免除以零
                            if body_vector[0] != 0:
                                angle = np.degrees(np.arctan(abs(body_vector[1] / body_vector[0])))
                                
                                # 角度 < 45度判定为跌倒
                                if angle < 45: 
                                    # 缓存事件（不立即写入数据库）
                                    fall_events.append({
                                        "person_id": person_id,
                                        "angle": angle,
                                        "velocity_y": velocity_y,
                                        "frame_count": frame_count,
                                        "timestamp": datetime.now()
                                    })
                                    
                                    # 画面标注跌倒信息
                                    cv2.putText(
                                        frame, 
                                        f"FALL DETECTED: ID {person_id}", 
                                        (int(box[0]), int(box[1] - 10)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 
                                        1, 
                                        (0, 0, 255), 
                                        2
                                    )
                else:
                    # 初始化新人员的姿态历史
                    pose_history[person_id] = [(centroid_y, 0)]

            # 显示调试信息（ID、速度、角度）
            debug_text = f"ID:{person_id} V:{velocity_y:.1f} A:{angle:.1f}"
            cv2.putText(
                frame, 
                debug_text,
                (int(box[0]), int(box[1] - 35)),
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, 
                (255, 255, 0), 
                2
            )


def log_fall_detection(camera_id, location_id, person_id, angle, velocity_y):
    """记录跌倒检测结果到数据库（复用ORM模型）"""
    try:
        detection_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        # 计算风险等级（角度越小/速度越大，风险越高）
        if angle < 30 and velocity_y > 20:
            risk_level = "high"
        elif angle < 45 and velocity_y > 15:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 计算置信度（角度越小，置信度越高）
        confidence_score = min(1.0, (45 - angle) / 45)
        
        # 创建行为检测记录（passenger_id设为None避免外键冲突）
        behavior_log = BehaviorDetectionLog(
            detection_id=detection_id,
            passenger_id=None,  # 不关联乘客ID（避免外键约束）
            camera_id=camera_id,
            location_id=location_id,
            detection_time=current_time,
            behavior_type="Fall",
            confidence_score=confidence_score,
            risk_level=risk_level,
            detection_area="full_frame"
        )
        
        # 创建报警记录
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            detection_id=detection_id,
            alert_time=current_time,
            alert_type="high_risk_behavior",
            severity=risk_level,
            status="unprocessed",
            camera_id=camera_id,
            location_id=location_id,
            message=f"检测到跌倒行为 (人员ID: {person_id}), 置信度: {confidence_score:.2f}"
        )
        
        db.session.add(behavior_log)
        db.session.add(alert)
        db.session.commit()
        print(f"跌倒记录成功，detection_id={detection_id}")
        return detection_id
        
    except IntegrityError as e:
        print(f"跌倒记录外键冲突: {str(e)}")
        db.session.rollback()
    except Exception as e:
        print(f"跌倒记录失败: {str(e)}")
        db.session.rollback()
    return None


# --- 新的、带结果黏滞和多线程优化的高频人脸识别逻辑 ---

def process_faces_only(frame, frame_count, state):
    """
    只进行人脸检测和识别的处理。
    使用 YOLOv8 进行检测，使用 Dlib 进行识别。
    这个函数现在直接在传入的 frame 上绘图，不再返回新的 frame。
    """
    face_model_local = state.get('face_model')
    if face_model_local is None:
        face_model_local = YOLO(FACE_MODEL_PATH)
        state['face_model'] = face_model_local

    # --- 性能诊断：步骤1 ---
    t0 = time.time()
    # 使用 YOLOv8 进行人脸检测
    # 修复：对于可能为静态图的场景，使用 .predict() 而不是 .track()
    face_results = face_model_local.predict(frame, verbose=False)
    t1 = time.time()
    
    # 从结果中提取边界框
    boxes = [box.xyxy[0].tolist() for box in face_results[0].boxes] # 获取所有检测框
    
    # 如果没有检测到人脸，直接返回
    if not boxes:
        return
        
    # --- 性能诊断：步骤2 ---
    t2 = time.time()
    # 将边界框传递给 Dlib 服务进行识别

    dlib_face_service = get_dlib_face_service()
    
    recognized_faces = dlib_face_service.identify_faces(frame, boxes)
    t3 = time.time()

    # --- 打印诊断日志 ---
    print(f"DIAGNOSTICS - YOLO Detection: {t1-t0:.4f}s, Dlib Recognition: {t3-t2:.4f}s")
    
    # 3. 在帧上绘制结果
    for name, box in recognized_faces:
        # 双重保险：再次确保坐标是整数
        left, top, right, bottom = [int(p) for p in box]
        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                
        # 绘制边界框
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # 准备绘制名字的文本
        label = f"{name}"
        
        (label_width, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        
        # --- 智能定位标签位置 ---
        label_bg_height = 20 # 标签背景的高度
        
        # 判断标签应该放在框内还是框外
        if top - label_bg_height < 5: # 增加一个5像素的边距
            # 空间不足，放在内部
            cv2.rectangle(frame, (left, top), (left + label_width + 4, top + label_bg_height), color, -1)
            cv2.putText(frame, label, (left + 2, top + label_bg_height - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        else:
            # 空间充足，放在外部
            cv2.rectangle(frame, (left, top - label_bg_height), (left + label_width + 4, top), color, -1)
            cv2.putText(frame, label, (left + 2, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
    # 不再返回 frame，因为是直接在原图上修改
    # return frame



def process_violence_detection(filepath, uploads_dir, camera_id, location_id):
    """处理暴力检测并记录到数据库"""
    model_path = os.path.join(os.path.dirname(__file__), 'vd.hdf5')
    try:
        # 调用暴力检测模型
        violence_prob, non_violence_prob = violenceDetect.predict_video(
            filepath, 
            model_path=model_path
        )
        
        # 记录到数据库
        log_violence_detection(
            camera_id=camera_id,
            location_id=location_id,
            violence_prob=violence_prob,
            non_violence_prob=non_violence_prob
        )
        
    except Exception as e:
        return {"status": "error", "message": f"暴力检测失败: {str(e)}"}, 500

    # 生成输出视频（复制原视频，可扩展为标注视频）
    output_filename = 'processed_' + os.path.basename(filepath)
    output_path = os.path.join(uploads_dir, output_filename)
    if not os.path.exists(output_path):
        shutil.copy(filepath, output_path)
    output_url = f"/api/files/{output_filename}"

    # 生成警报信息
    alerts = []
    if violence_prob > 0.7:
        alerts.append("warning: 检测到高概率暴力行为!")
    elif violence_prob > 0.5:
        alerts.append("caution: 检测到可能的暴力行为")
    else:
        alerts.append("safe: 未检测到明显暴力行为")

    return {
        "status": "success",
        "media_type": "video",
        "file_url": output_url,
        "alerts": alerts,
        "violenceProbability": float(violence_prob),
        "nonViolenceProbability": float(non_violence_prob)
    }


def log_violence_detection(camera_id, location_id, violence_prob, non_violence_prob):
    """记录暴力检测结果到数据库"""
    try:
        detection_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        # 确定风险等级和报警信息
        if violence_prob > 0.7:
            risk_level = "high"
            severity = "high"
            message = f"高概率暴力行为! 概率: {violence_prob:.2f}"
        elif violence_prob > 0.5:
            risk_level = "medium"
            severity = "medium"
            message = f"可能的暴力行为 概率: {violence_prob:.2f}"
        else:
            risk_level = "low"
            severity = "low"
            message = f"未检测到明显暴力行为 概率: {violence_prob:.2f}"
        
        # 创建行为检测记录
        behavior_log = BehaviorDetectionLog(
            detection_id=detection_id,
            passenger_id=None,  # 不关联乘客
            camera_id=camera_id,
            location_id=location_id,
            detection_time=current_time,
            behavior_type="Violence",
            confidence_score=violence_prob,
            risk_level=risk_level,
            detection_area="full_frame"
        )
        
        # 创建报警记录
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            detection_id=detection_id,
            alert_time=current_time,
            alert_type="high_risk_behavior",
            severity=severity,
            status="unprocessed",
            camera_id=camera_id,
            location_id=location_id,
            message=message
        )
        
        db.session.add(behavior_log)
        db.session.add(alert)
        db.session.commit()
        print(f"暴力记录成功，detection_id={detection_id}")
        return detection_id
        
    except Exception as e:
        print(f"暴力记录失败: {str(e)}")
        db.session.rollback()
    return None