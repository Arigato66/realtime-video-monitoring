import cv2
import numpy as np
from ultralytics import YOLO
from sqlalchemy.exc import IntegrityError
import os
# --- V4: 修正模块导入问题 ---
from app.services import danger_zone as danger_zone_service
from app.services.danger_zone import SAFETY_DISTANCE, LOITERING_THRESHOLD, TARGET_CLASSES
# --- 结束 V4 ---
from app.services.alerts import (
    add_alert_memory as add_alert, # 保留旧的内存告警作为兼容
    create_alert, # 导入新的数据库告警函数
    update_loitering_time, reset_loitering_time, get_loitering_time,
    update_detection_time, get_alerts, reset_alerts
)
from app.utils.geometry import point_in_polygon, distance_to_polygon
from app.services.dlib_service import dlib_face_service
from app.services import system_state
from app.services.smoking_detection_service import SmokingDetectionService
import time
from concurrent.futures import ThreadPoolExecutor
from app.services import violenceDetect
# --- 新增：导入config模块以访问其状态 ---
from app.routes import config as config_state
# --- 结束新增 ---


# --- 快照保存路径 ---
SNAPSHOTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'snapshots')
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


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


def process_image(filepath, uploads_dir):
    """
    处理单张图片
    
    参数:
        filepath: 图片文件路径
        uploads_dir: 上传文件目录
        
    返回:
        dict: 包含处理结果的字典
    """
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
    
    # --- FIX: 返回真实的数据库告警, 而不是旧的内存告警 ---
    # get_alerts() 返回的是一个临时的内存列表，而 create_alert 已将告警存入数据库
    # 此处我们返回一个确认信息，前端应通过访问告警中心API来获取最新列表
    final_alerts = get_alerts() # 获取内存中的告警，用于即时（但不可靠）的反馈
    
    return {
        "status": "success",
        "media_type": "image",
        "file_url": output_url,
        "alerts": final_alerts, # 返回处理期间生成的内存告警
        "message": "Processing complete. Check alert center for persistent alerts."
    }

def process_video(filepath, uploads_dir):
    """完整视频处理函数，支持多模式检测并优化跌倒记录"""
    # 重置警报和缓存
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
    
    # --- FIX: 同上, 视频处理也应明确返回处理期间的告警 ---
    final_alerts = get_alerts()
    
    return {
        "status": "success",
        "media_type": "video",
        "file_url": output_url,
        "alerts": final_alerts,
        "message": "Processing complete. Check alert center for persistent alerts."
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
                    snapshot_path = save_snapshot(frame) # 保存快照
                    add_alert("High-Confidence Smoking Detection in ROI", 
                             event_type="smoking_detection", 
                             details="高置信度吸烟检测行为", 
                             snapshot_path=snapshot_path)
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
            snapshot_path = save_snapshot(frame) # 保存快照
            add_alert("Low-Confidence/Distant Smoking Detection in Upper Body",
                     event_type="smoking_detection",
                     details="低置信度/远距离吸烟检测行为",
                     snapshot_path=snapshot_path)
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


# 全局缓存：记录已处理的事件，避免重复写入数据库
zone_enter_history = set()  # 已记录闯入的目标ID
loitering_logged = set()    # 已记录停留超时的目标ID
too_close_logged = dict()   # 已记录距离过近的目标ID: 上次记录时间

def is_target_in_zone_history(target_id):
    """判断目标是否已记录过闯入事件"""
    return target_id in zone_enter_history

def add_target_to_zone_history(target_id):
    """添加目标到闯入历史"""
    zone_enter_history.add(target_id)

def is_loitering_logged(target_id):
    """判断目标是否已记录过停留超时"""
    return target_id in loitering_logged

def mark_loitering_logged(target_id):
    """标记目标为已记录停留超时"""
    loitering_logged.add(target_id)

def is_too_close_logged(target_id):
    """判断目标是否已记录过距离过近（5秒内不重复）"""
    last_time = too_close_logged.get(target_id)
    if not last_time:
        return False
    return (datetime.now() - last_time).total_seconds() < 5  # 5秒内不重复

def mark_too_close_logged(target_id, timeout=5):
    """标记目标为已记录距离过近"""
    too_close_logged[target_id] = datetime.now()
    
def process_object_detection_results(results, frame, time_diff, frame_count, camera_id, location_id):
    """
    处理通用目标检测结果（危险区域、徘徊等）
    """
    # 设置当前处理的帧
    set_current_frame(frame)
    
    # 编辑模式跳过检测逻辑
    if config_state.edit_mode:
        if results and results[0].boxes is not None and hasattr(results[0].boxes, 'id'):
            frame[:] = results[0].plot()
        return

    # 有追踪结果时处理
    if hasattr(results[0], 'boxes') and hasattr(results[0].boxes, 'id'):
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.int().cpu().numpy()
        classes = results[0].boxes.cls.cpu().numpy()
        class_names = results[0].names
        
        # 获取危险区域配置
        danger_zone = danger_zone_service.get_danger_zone(location_id)
        if not danger_zone:
            print(f"警告：位置 {location_id} 的危险区域未配置")
            return
            
        for box, target_id, cls in zip(boxes, ids, classes):
            x1, y1, x2, y2 = box
            class_name = class_names[int(cls)]
            foot_point = (int((x1 + x2) / 2), int(y2))  # 目标底部中心点
            
            # 检查是否在危险区域内
            in_danger_zone = point_in_polygon(foot_point, danger_zone)
            # 计算到危险区域的距离
            distance = distance_to_polygon(foot_point, danger_zone)
            # 获取安全距离和停留阈值
            safety_distance = danger_zone_service.get_safety_distance(location_id)
            loitering_threshold = danger_zone_service.get_loitering_threshold(location_id)
            
            # 1. 危险区域闯入记录
            if in_danger_zone and not is_target_in_zone_history(target_id):
                log_danger_zone_behavior(
                    camera_id=camera_id,
                    location_id=location_id,
                    target_id=target_id,
                    behavior_type="zone_enter"
                )
                add_target_to_zone_history(target_id)
            
            # 2. 停留超时记录
            if in_danger_zone:
                loitering_time = update_loitering_time(target_id, time_diff)
                if loitering_time >= loitering_threshold and not is_loitering_logged(target_id):
                    log_danger_zone_behavior(
                        camera_id=camera_id,
                        location_id=location_id,
                        target_id=target_id,
                        behavior_type="loitering",
                        loitering_time=loitering_time
                    )
                    mark_loitering_logged(target_id)
            else:
                reset_loitering_time(target_id)
            
            # 3. 距离过近记录
            if not in_danger_zone and distance < safety_distance and not is_too_close_logged(target_id):
                log_danger_zone_behavior(
                    camera_id=camera_id,
                    location_id=location_id,
                    target_id=target_id,
                    behavior_type="too_close",
                    distance=distance
                )
                mark_too_close_logged(target_id, timeout=5)
            
            # 确定标签颜色和告警状态
            label_color = (0, 255, 0)  # 默认绿色
            alert_status = None
            
            # 如果在危险区域内，更新停留时间
            if in_danger_zone:
                loitering_time = update_loitering_time(target_id, time_diff)
                
                # 如果停留时间超过阈值，标记为红色并记录告警
                if loitering_time >= LOITERING_THRESHOLD:
                    # 使用纯红色
                    label_color = (0, 0, 255)  # BGR格式：红色
                    alert_status = f"ID:{id} ({display_name}) staying in danger zone for {loitering_time:.1f}s"
                    snapshot_path = save_snapshot(frame) # 保存快照
                    add_alert(alert_status,
                             event_type="danger_zone_intrusion",
                             details=f"人员 {display_name} 在危险区域停留 {loitering_time:.1f} 秒",
                             snapshot_path=snapshot_path)
                else:
                    # 根据停留时间从橙色到红色渐变
                    ratio = min(1.0, loitering_time / LOITERING_THRESHOLD)
                    # 从橙色(0,165,255)到红色(0,0,255)
                    label_color = (0, int(165 * (1 - ratio)), 255)
            else:
                # 如果不在区域内，重置停留时间
                reset_loitering_time(target_id)

                # 如果距离小于安全距离，根据距离设置颜色从绿色到黄色
                if distance < SAFETY_DISTANCE:
                    # 计算距离比例
                    ratio = distance / SAFETY_DISTANCE
                    # 从黄色(0,255,255)到绿色(0,255,0)渐变
                    label_color = (0, 255, int(255 * (1 - ratio)))
                    
                    alert_status = f"ID:{id} ({display_name}) too close to danger zone ({distance:.1f}px)"
                    snapshot_path = save_snapshot(frame) # 保存快照
                    add_alert(alert_status,
                             event_type="proximity_warning",
                             details=f"人员 {display_name} 过于接近危险区域，距离 {distance:.1f} 像素",
                             snapshot_path=snapshot_path)
            
            # 在每个目标上方显示ID和类别
            label = f"ID:{target_id} {class_name}"

            if in_danger_zone:
                label += f" time:{get_loitering_time(target_id):.1f}s"
            elif distance < SAFETY_DISTANCE:
                label += f" dist:{distance:.1f}px"
            
            # 根据危险程度调整边框粗细
            thickness = 2  # 默认粗细
            if in_danger_zone:
                # 在危险区域内，根据停留时间增加边框粗细
                thickness = max(2, int(4 * min(1.0, get_loitering_time(target_id) / LOITERING_THRESHOLD)))
                
                # 如果停留时间超过阈值，添加警告标记
                if get_loitering_time(target_id) >= LOITERING_THRESHOLD:
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

def draw_distance_line(frame, foot_point, distance, color):
    """绘制目标到危险区域的距离线"""
    # 找到危险区域最近点
    min_dist = float('inf')
    closest_point = None
    for i in range(len(danger_zone_service.DANGER_ZONE)):
        p1 = np.array(danger_zone_service.DANGER_ZONE[i])
        p2 = np.array(danger_zone_service.DANGER_ZONE[(i + 1) % len(danger_zone_service.DANGER_ZONE)])
        line_vec = p2 - p1
        line_len = np.linalg.norm(line_vec)
        if line_len == 0:
            continue
        line_unitvec = line_vec / line_len
        pt_vec = np.array(foot_point) - p1
        proj_len = np.dot(pt_vec, line_unitvec)
        proj_len = max(0, min(line_len, proj_len))
        closest_pt = p1 + line_unitvec * proj_len
        dist = np.linalg.norm(np.array(foot_point) - closest_pt)
        if dist < min_dist:
            min_dist = dist
            closest_point = tuple(map(int, closest_pt))

    # 绘制距离线
    if closest_point:
        cv2.line(frame, foot_point, closest_point, color, 2)
        mid_point = (
            (foot_point[0] + closest_point[0]) // 2,
            (foot_point[1] + closest_point[1]) // 2
        )
        cv2.putText(frame, f"{distance:.1f}px", mid_point,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

import cv2
import numpy as np
from datetime import datetime
import uuid
from sqlalchemy.exc import IntegrityError
import io
from PIL import Image

# 新增全局变量，用于存储当前帧图像
current_frame = None

def set_current_frame(frame):
    """设置当前处理的帧图像"""
    global current_frame
    current_frame = frame.copy()

def log_danger_zone_behavior(camera_id, location_id, target_id, behavior_type, distance=None, loitering_time=None):
    """
    记录目标检测相关行为（危险区域闯入/停留/过近）到数据库，并保存相关图像
    
    参数:
        camera_id: 摄像头ID
        location_id: 位置ID
        target_id: 目标追踪ID
        behavior_type: 行为类型（"zone_enter"/"loitering"/"too_close"）
        distance: 目标到危险区域的距离（仅用于"too_close"）
        loitering_time: 停留时间（仅用于"loitering"）
    """
    try:
        # 生成唯一ID和时间戳
        detection_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        # 确定风险等级和置信度
        if behavior_type == "loitering" and loitering_time is not None:
            risk_level = "high" if loitering_time > 5 else "medium"
            confidence_score = min(1.0, loitering_time / 10)
        elif behavior_type == "zone_enter":
            risk_level = "high"
            confidence_score = 1.0
        elif behavior_type == "too_close" and distance is not None:
            safety_distance = danger_zone_service.get_safety_distance(location_id)
            risk_level = "high" if distance < safety_distance * 0.5 else "medium"
            confidence_score = 1.0 - (distance / (safety_distance * 2))
        
        # 行为描述信息
        if behavior_type == "zone_enter":
            behavior_desc = f"目标 {target_id} 闯入危险区域"
        elif behavior_type == "loitering":
            behavior_desc = f"目标 {target_id} 在危险区域停留超时（{loitering_time:.1f}秒）"
        else:  # too_close
            behavior_desc = f"目标 {target_id} 距离危险区域过近（{distance:.1f}px）"
        
        # 创建行为检测记录
        behavior_log = BehaviorDetectionLog(
            detection_id=detection_id,
            passenger_id=None,
            camera_id=camera_id,
            location_id=location_id,
            detection_time=current_time,
            behavior_type=behavior_type,
            confidence_score=confidence_score,
            risk_level=risk_level,
            detection_area="danger_zone"
        )
        
        # 创建告警记录
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            detection_id=detection_id,
            alert_time=current_time,
            alert_type="danger_zone_violation",
            severity=risk_level,
            status="unprocessed",
            camera_id=camera_id,
            location_id=location_id,
            message=behavior_desc
        )
        
        # 截取并保存相关图像
        if current_frame is not None:
            # 截取整个帧作为图像
            img = current_frame.copy()
            
            # 将图像转换为二进制格式
            is_success, buffer = cv2.imencode(".jpg", img)
            io_buf = io.BytesIO(buffer)
            img_bytes = io_buf.getvalue()
            
            # 创建图像记录
            from app.models import DetectionImage  # 假设存在这个模型
            detection_image = DetectionImage(
                image_id=str(uuid.uuid4()),
                detection_id=detection_id,
                image_data=img_bytes,  # 存储二进制图像数据
                image_format="jpg",
                timestamp=current_time
            )
            
            db.session.add(detection_image)
        
        # 提交到数据库
        db.session.add(behavior_log)
        db.session.add(alert)
        db.session.commit()
        print(f"目标检测行为记录成功，detection_id={detection_id}")
        return detection_id
        
    except Exception as e:
        print(f"目标检测记录失败: {str(e)}")
        db.session.rollback()
        return None

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
                                    alert_message = f"警告: 人员 {person_id} 可能已跌倒!"
                                    snapshot_path = save_snapshot(frame) # 保存快照
                                    add_alert(f"Fall Detected: Person ID {person_id} may have fallen.",
                                             event_type="fall_detection",
                                             details=f"检测到人员 {person_id} 可能跌倒，身体角度 {angle:.1f} 度",
                                             snapshot_path=snapshot_path)
                                    # 在人的边界框上方用红色字体标注
                                    cv2.putText(frame, f"FALL DETECTED: ID {person_id}", 
                                                (int(box[0]), int(box[1] - 10)),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    # 初始化新人员的姿态历史
                    pose_history[person_id] = [(centroid_y, 0)]

            # 显示调试信息（ID、速度、角度）
            debug_text = f"ID:{person_id} V:{velocity_y:.1f} A:{angle:.1f}"
            cv2.putText(frame, debug_text,
                        (int(box[0]), int(box[1] - 35)), # 显示在FALL DETECTED文字的上方
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)


# 为了保持兼容，我们将旧的函数重命名
process_detection_results = process_object_detection_results

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
        add_alert(f"High probability ({violence_prob:.2f}) of violence detected.",
                 event_type="violence_detection",
                 details=f"检测到高概率暴力行为，置信度 {violence_prob:.2f}")
    elif violence_prob > 0.5:
        alerts.append("caution: 检测到可能的暴力行为")
        add_alert(f"Possible violence detected ({violence_prob:.2f}).",
                 event_type="violence_detection", 
                 details=f"检测到可能的暴力行为，置信度 {violence_prob:.2f}")
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

def save_snapshot(frame):
    """保存当前帧的快照并返回相对路径"""
    timestamp = int(time.time() * 1000)
    filename = f"snapshot_{timestamp}.jpg"
    filepath = os.path.join(SNAPSHOTS_DIR, filename)
    
    try:
        cv2.imwrite(filepath, frame)
        # 返回可供前端访问的相对URL
        return f"/api/files/snapshots/{filename}"
    except Exception as e:
        print(f"快照保存失败: {e}")
        return None
