import cv2
import numpy as np
from ultralytics import YOLO
import os
from app.services.danger_zone import DANGER_ZONE, SAFETY_DISTANCE, LOITERING_THRESHOLD, TARGET_CLASSES
from app.services.alerts import (
    add_alert, update_loitering_time, reset_loitering_time, get_loitering_time,
    update_detection_time, get_alerts, reset_alerts
)
from app.utils.geometry import point_in_polygon, distance_to_polygon
from app.services import face_service
from app.services import system_state
from deepface import DeepFace
import time
from concurrent.futures import ThreadPoolExecutor

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


# 全局变量来持有加载的模型
pose_model = None
object_model = None
face_model = None

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
    # 读取图片
    img = cv2.imread(filepath)
    if img is None:
        return {"status": "error", "message": "Failed to load image"}, 500
    
    # 为单张图片创建一个独立的、无状态的模型实例
    # 这可以防止从视频流等其他操作中遗留的追踪器状态导致崩溃
    model = YOLO(OBJECT_MODEL_PATH)
    
    # 使用 .predict() 明确表示这是单张图片预测
    detections = model.predict(img)
    
    # 处理检测结果
    res_plotted = detections[0].plot()
    
    # 绘制危险区域
    danger_zone_pts = DANGER_ZONE.reshape((-1, 1, 2))
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
    """
    处理视频文件
    
    参数:
        filepath: 视频文件路径
        uploads_dir: 上传文件目录
        
    返回:
        dict: 包含处理结果的字典
    """
    # 重置警报
    reset_alerts()
    
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
    
    # 创建视频写入器 - 使用H.264编码器替代mp4v
    try:
        # 尝试使用H.264编码器
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        
        # 如果H.264编码器不可用，回退到MJPG
        if not out.isOpened():
            print("警告: H.264编码器不可用，回退到MJPG")
            output_path_avi = output_path.replace(".mp4", ".avi")
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            out = cv2.VideoWriter(output_path_avi, fourcc, fps, (frame_width, frame_height))
            output_filename = output_filename.replace(".mp4", ".avi")
    except Exception as e:
        print(f"视频编码器错误: {e}")
        # 最后的回退选项 - 使用无损编码
        fourcc = cv2.VideoWriter_fourcc(*"DIB ")
        out = cv2.VideoWriter(output_path.replace(".mp4", ".avi"), fourcc, fps, (frame_width, frame_height))
        output_filename = output_filename.replace(".mp4", ".avi")
    
    # 初始化此视频处理任务专用的YOLOv8模型
    # 避免在多个后台任务中共享模型实例及其追踪器状态
    object_model_local = YOLO(OBJECT_MODEL_PATH)
    pose_model_local = YOLO(POSE_MODEL_PATH)
    face_model_local = YOLO(FACE_MODEL_PATH)
    
    # 为本次视频处理创建一个新的人脸识别缓存
    face_recognition_cache = {}
    
    # 处理视频帧
    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"开始处理视频，总帧数: {total_frames}")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        if frame_count % 10 == 0:  # 每10帧打印一次进度
            progress = (frame_count / total_frames) * 100
            print(f"处理视频: {progress:.1f}% 完成")
        
        # 计算时间差
        time_diff = update_detection_time()
        
        # --- 检测模式处理 ---
        processed_frame = frame.copy() # 复制一份用于处理

        # 根据当前模式决定处理方式
        if system_state.DETECTION_MODE == 'object_detection':
            # 执行目标追踪
            results = object_model_local.track(processed_frame, persist=True)
            
            # --- 绘图顺序调整 ---
            # 1. 首先，绘制危险区域的半透明叠加层作为背景
            overlay = processed_frame.copy()
            danger_zone_pts = DANGER_ZONE.reshape((-1, 1, 2))
            cv2.fillPoly(overlay, [danger_zone_pts], (0, 0, 255))
            cv2.addWeighted(overlay, 0.4, processed_frame, 0.6, 0, processed_frame)
            cv2.polylines(processed_frame, [danger_zone_pts], True, (0, 0, 255), 3)
            
            # 在危险区域中添加文字
            danger_zone_center = np.mean(DANGER_ZONE, axis=0, dtype=np.int32)
            cv2.putText(processed_frame, "Danger Zone", 
                        (danger_zone_center[0] - 60, danger_zone_center[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
            
            # 2. 然后，在已经有了危险区域的帧上，处理检测结果（绘制追踪框、标签等前景）
            process_object_detection_results(results, processed_frame, time_diff, frame_count)
        
        elif system_state.DETECTION_MODE == 'fall_detection':
            # 执行姿态估计追踪
            pose_results = pose_model_local.track(processed_frame, persist=True)
            process_pose_estimation_results(pose_results, processed_frame, time_diff, frame_count)

        elif system_state.DETECTION_MODE == 'face_only':
            # 优化：传入人脸识别缓存以保存状态
            # 确保人脸模型被正确地传递给处理函数
            if 'face_model' not in face_recognition_cache:
                face_recognition_cache['face_model'] = face_model_local
            process_faces_only(processed_frame, frame_count, face_recognition_cache)

        # 写入处理后的帧到输出视频
        # 确保帧是BGR格式，这是OpenCV的标准格式
        if processed_frame is not None:
            # 确保帧是BGR格式，这是OpenCV的标准格式
            if len(processed_frame.shape) == 2:  # 灰度图像
                processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_GRAY2BGR)
            elif processed_frame.shape[2] == 4:  # RGBA图像
                processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_RGBA2BGR)
            
            # 打印帧信息，帮助调试
            print(f"写入帧: 形状={processed_frame.shape}, 类型={processed_frame.dtype}, 最小值={processed_frame.min()}, 最大值={processed_frame.max()}")
            
            out.write(processed_frame)
    
    # 释放资源
    cap.release()
    out.release()
    
    # 使用相对URL路径
    output_url = f"/api/files/{output_filename}"
    print(f"视频处理完成，输出URL: {output_url}")
    
    return {
        "status": "success",
        "media_type": "video",
        "file_url": output_url,
        "alerts": get_alerts()
    }

def process_object_detection_results(results, frame, time_diff, frame_count):
    """
    处理通用目标检测结果（危险区域、徘徊等）
    (这是您之前的 process_detection_results 函数，已重命名并保留)
    """
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
            in_danger_zone = point_in_polygon(foot_point, DANGER_ZONE)
            
            # 计算到危险区域的距离
            distance = distance_to_polygon(foot_point, DANGER_ZONE)
            
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

def process_pose_estimation_results(results, frame, time_diff, frame_count):
    """
    处理姿态估计结果，进行跌倒检测
    """
    # 如果有追踪结果，则进行跌倒检测
    if hasattr(results[0], 'boxes') and hasattr(results[0].boxes, 'id') and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.int().cpu().numpy()
        keypoints = results[0].keypoints.xy.cpu().numpy()  # 获取关键点

        # 首先，让YOLOv8的plot函数绘制基本的骨架和边界框
        frame[:] = results[0].plot()

        for person_id, box, kps in zip(ids, boxes, keypoints):
            # --- 跌倒检测逻辑 ---
            velocity_y = 0
            angle = 90 # 默认为垂直

            # 1. 计算人体中心点（质心）
            visible_kps = kps[kps[:, 1] > 0] 
            if len(visible_kps) > 4:
                centroid_y = np.mean(visible_kps[:, 1])

                # 2. 更新历史记录并计算垂直速度
                if person_id in pose_history:
                    prev_centroid_y, _ = pose_history[person_id][-1]
                    velocity_y = centroid_y - prev_centroid_y
                    
                    pose_history[person_id].append((centroid_y, velocity_y))
                    if len(pose_history[person_id]) > 30:
                        pose_history[person_id].pop(0)

                    # 3. 判断是否快速下坠 (速度为正表示向下,因为图像坐标系Y轴向下)
                    if velocity_y > 15: # 阈值需要调试
                        
                        # 4. 确认跌倒状态: 检查身体主干角度
                        left_shoulder, right_shoulder = kps[5], kps[6]
                        left_hip, right_hip = kps[11], kps[12]

                        # 确保关键点都可见
                        if left_shoulder[1] > 0 and right_shoulder[1] > 0 and left_hip[1] > 0 and right_hip[1] > 0:
                            shoulder_center = (left_shoulder + right_shoulder) / 2
                            hip_center = (left_hip + right_hip) / 2
                            body_vector = hip_center - shoulder_center
                            
                            # 避免除以零的错误
                            if body_vector[0] != 0:
                                # 计算身体与水平线的夹角
                                angle = np.degrees(np.arctan(abs(body_vector[1] / body_vector[0])))
                                
                                # 角度小于45度，意味着身体更趋向于水平
                                if angle < 45: 
                                    alert_message = f"警告: 人员 {person_id} 可能已跌倒!"
                                    add_alert(alert_message) # 修正：只传递一个参数
                                    # 在人的边界框上方用红色字体标注
                                    cv2.putText(frame, f"FALL DETECTED: ID {person_id}", 
                                                (int(box[0]), int(box[1] - 10)),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    # 初始化这个人的姿态历史记录
                    pose_history[person_id] = [(centroid_y, 0)]

            # --- 在画面上显示调试信息 ---
            debug_text = f"ID:{person_id} V:{velocity_y:.1f} A:{angle:.1f}"
            cv2.putText(frame, debug_text,
                        (int(box[0]), int(box[1] - 35)), # 显示在FALL DETECTED文字的上方
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)


# 为了保持兼容，我们将旧的函数重命名
process_detection_results = process_object_detection_results


# --- 新的、带结果黏滞和多线程优化的高频人脸识别逻辑 ---

def process_faces_only(frame, frame_count, state):
    """
    使用YOLOv8追踪，并通过后台线程进行高频、非阻塞、结果稳定的识别。
    
    参数:
        state: 在多次调用间保持状态的字典。
    """
    # --- 1. 初始化 ---
    if 'executor' not in state:
        state['executor'] = ThreadPoolExecutor(max_workers=5)
    if 'track_data' not in state:
        state['track_data'] = {}
    
    executor = state['executor']
    track_data = state['track_data']
    face_model = state.get('face_model')
    if not face_model: return

    # --- 2. 配置 ---
    RECOGNITION_INTERVAL = 0.5  # (秒) 每0.5秒尝试识别一次
    UNKNOWN_CONFIDENCE_THRESHOLD = 5 # 连续5次识别为陌生人才确认
    BLUR_THRESHOLD = 25.0 # 大幅降低清晰度阈值，允许更多图像通过
    FORCE_RECOGNITION_TIME = 3.0 # 即使图像模糊，也至少每3秒尝试一次识别

    # --- 3. 追踪与状态清理 ---
    face_results = face_model.track(frame, persist=True, verbose=False)
    current_time = time.time()
    
    current_track_ids = set()
    if face_results[0].boxes.id is not None:
        current_track_ids = set(face_results[0].boxes.id.int().cpu().numpy())
    
    for track_id in list(track_data.keys()):
        if track_id not in current_track_ids:
            del track_data[track_id]

    if face_results[0].boxes.id is None:
        return

    # --- 4. 处理每个被追踪的人脸 ---
    boxes = face_results[0].boxes.xyxy.cpu().numpy()
    track_ids = face_results[0].boxes.id.int().cpu().numpy()

    for box, track_id in zip(boxes, track_ids):
        if track_id not in track_data:
            track_data[track_id] = {
                "identity": "Identifying...",
                "last_checked": 0,
                "future": None,
                "consecutive_unknowns": 0
            }
        
        person = track_data[track_id]

        # --- 5. 获取已完成的后台识别结果 ---
        if person["future"] is not None and person["future"].done():
            try:
                # result会是一个元组, e.g., ('zjz', 0.45) 或 ('Stranger', None)
                identity, distance = person["future"].result()
                print(f"[Debug Detection] Task done for ID {track_id}. Result: {identity}, Dist: {distance}")
                
                # 'Stranger'是服务返回的原始结果，代表未识别
                if identity == "Stranger":
                    person["consecutive_unknowns"] += 1
                else:
                    # 只要有一次成功识别，就重置计数器并更新身份
                    person["consecutive_unknowns"] = 0
                    person["identity"] = identity
                
                # 只有连续失败达到阈值，才将最终身份标记为'Stranger'
                if person["consecutive_unknowns"] >= UNKNOWN_CONFIDENCE_THRESHOLD:
                    person["identity"] = "Stranger"

                print(f"[Debug Detection] ID {track_id} new identity is '{person['identity']}'")

            except Exception as e:
                print(f"后台识别任务出错 (ID: {track_id}): {e}")
                person["identity"] = "Error"
            
            person["future"] = None # 清理任务

        # --- 6. 提交新的识别任务到后台 ---
        is_recognizing = person["future"] is not None
        # 检查是否需要提交新的识别任务
        time_since_last_check = current_time - person["last_checked"]
        should_recognize = (time_since_last_check > RECOGNITION_INTERVAL) and not is_recognizing
        
        # 强制识别：如果长时间没有识别，并且当前状态是"Identifying..."，则强制提交任务
        force_recognize = (time_since_last_check > FORCE_RECOGNITION_TIME) and (person["identity"] == "Identifying...")
        
        if should_recognize or force_recognize:
            person["last_checked"] = current_time
            
            x1, y1, x2, y2 = map(int, box)
            padding = 10 # 增加一点边缘，提高识别率
            face_crop = frame[max(0, y1-padding):min(frame.shape[0], y2+padding), 
                              max(0, x1-padding):min(frame.shape[1], x2+padding)]

            if face_crop.size > 0:
                # --- 新增：图像质量评估 ---
                gray_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                clarity = cv2.Laplacian(gray_face, cv2.CV_64F).var()
                
                # 只有清晰的图像才送去识别，除非是强制识别
                if clarity > BLUR_THRESHOLD or force_recognize:
                    if force_recognize:
                        print(f"[Debug Detection] FORCING recognition for ID {track_id} after {time_since_last_check:.1f}s. Current state: {person['identity']}")
                    else:
                        print(f"[Debug Detection] Submitting task for ID {track_id}. Clarity: {clarity:.2f}")
                    
                    future = executor.submit(face_service.identify_face_from_image, face_crop)
                    person["future"] = future
                else:
                    # 对于模糊图像，我们不提交识别，但可以在此打印日志以供调试
                    print(f"[Debug Detection] Skipped task for ID {track_id}. Clarity: {clarity:.2f} <= {BLUR_THRESHOLD}")

        # --- 7. 绘制 ---
        x1, y1, x2, y2 = map(int, box)
        display_name = person["identity"]
        
        # 识别成功为绿色，其他情况（未知, 正在识别, 错误）为红色
        color = (0, 255, 0) # 绿色
        if display_name in ["Stranger", "Identifying...", "Error"]:
            color = (0, 0, 255) # 红色
            
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"ID:{track_id} {display_name}"
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)


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
    for i in range(len(DANGER_ZONE)):
        p1 = DANGER_ZONE[i]
        p2 = DANGER_ZONE[(i + 1) % len(DANGER_ZONE)]
        
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