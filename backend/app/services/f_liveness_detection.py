import numpy as np
import cv2
import dlib
from scipy.spatial import distance as dist
import os
# 获取当前文件所在目录的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录的路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
# 构建预测器文件的完整路径
predictor_path = os.path.join(project_root, "shape_predictor_68_face_landmarks.dat")

# 初始化dlib的人脸检测器
detector = dlib.get_frontal_face_detector()

# 全局变量，用于延迟加载预测器
predictor = None

def load_predictor():
    global predictor
    if predictor is None:
        try:
            print(f"加载面部特征点预测器: {predictor_path}")
            predictor = dlib.shape_predictor(predictor_path)
            print("面部特征点预测器加载成功")
        except Exception as e:
            print(f"加载预测器失败: {str(e)}")
            raise

# 定义眼睛的索引
(lStart, lEnd) = (42, 48)  # 左眼的关键点索引
(rStart, rEnd) = (36, 42)  # 右眼的关键点索引

def eye_aspect_ratio(eye):
    # 计算眼睛的纵横比
    A = dist.euclidean(eye[1], eye[5])  # 垂直距离
    B = dist.euclidean(eye[2], eye[4])  # 垂直距离
    C = dist.euclidean(eye[0], eye[3])  # 水平距离
    ear = (A + B) / (2.0 * C)  # 眼睛纵横比
    return ear

def detect_liveness(frame, COUNTER, TOTAL):
    # 确保预测器已加载
    load_predictor()
    
    # 转换为灰度图
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 检测人脸
    rects = detector(gray, 0)
    
    # 初始化返回值
    result = {
        'count_blinks_consecutives': COUNTER,
        'total_blinks': TOTAL,
        'ear': 0.0,
        'leftEye': [],
        'rightEye': [],
        'faces': len(rects)
    }
    
    # 如果没有检测到人脸，直接返回
    if len(rects) == 0:
        return result
    
    # 对每个检测到的人脸进行处理（这里只处理第一个）
    rect = rects[0]
    
    try:
        # 获取面部关键点
        shape = predictor(gray, rect)
        shape = np.array([[p.x, p.y] for p in shape.parts()])
        
        # 提取左右眼的关键点
        leftEye = shape[lStart:lEnd]
        rightEye = shape[rStart:rEnd]
        
        # 计算左右眼的纵横比
        leftEAR = eye_aspect_ratio(leftEye)
        rightEAR = eye_aspect_ratio(rightEye)
        
        # 计算平均纵横比
        ear = (leftEAR + rightEAR) / 2.0
        
        # 更新结果
        result['ear'] = ear
        result['leftEye'] = leftEye.tolist()
        result['rightEye'] = rightEye.tolist()
        
        # 检测眨眼 - 降低阈值，使检测更敏感
        EYE_AR_THRESH = 0.19  # 原来是0.23，降低阈值使检测更敏感
        EYE_AR_CONSEC_FRAMES = 2  # 原来是3，减少连续帧要求
        
        if ear < EYE_AR_THRESH:
            result['count_blinks_consecutives'] += 1
        else:
            if result['count_blinks_consecutives'] >= EYE_AR_CONSEC_FRAMES:
                result['total_blinks'] += 1
                print(f"检测到眨眼! EAR: {ear:.2f}")
            result['count_blinks_consecutives'] = 0
        
        # 在图像上绘制眼睛和纵横比
        for (x, y) in leftEye:
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
        for (x, y) in rightEye:
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
        
        # 绘制眼睛区域
        leftEyeHull = cv2.convexHull(leftEye)
        rightEyeHull = cv2.convexHull(rightEye)
        cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)
        
        # 显示EAR值和眨眼计数
        cv2.putText(frame, f"EAR: {ear:.2f}", (300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Blinks: {result['total_blinks']}", (300, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 如果EAR低于阈值，显示"眨眼"文本
        if ear < EYE_AR_THRESH:
            cv2.putText(frame, "BLINK DETECTED!", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    except Exception as e:
        print(f"处理面部关键点时出错: {str(e)}")
    
    return result

