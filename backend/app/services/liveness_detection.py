import cv2
import numpy as np
from scipy.spatial import distance as dist
from imutils import face_utils
import dlib
import random
import time

class LivenessDetector:
    def __init__(self):
        # 初始化dlib的人脸检测器和面部特征点预测器
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        
        # 获取眼睛区域的索引
        (self.lStart, self.lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
        (self.rStart, self.rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
        
        # 眨眼检测参数
        self.EYE_AR_THRESH = 0.3
        self.EYE_AR_CONSEC_FRAMES = 3
        
        # 计数器
        self.COUNTER = 0
        self.TOTAL = 0
        
        # 活体检测状态
        self.reset_state()
        
    def reset_state(self):
        """重置检测状态"""
        self.current_challenge = None
        self.challenge_start_time = None
        self.challenge_complete = False
        self.blinks_required = 0
        self.blinks_detected = 0
        self.head_movement_detected = False
        self.challenge_timeout = 10  # 每个挑战的超时时间（秒）
        
    def eye_aspect_ratio(self, eye):
        """计算眼睛纵横比"""
        # 计算眼睛垂直方向的两组特征点距离
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])
        # 计算眼睛水平方向的特征点距离
        C = dist.euclidean(eye[0], eye[3])
        # 计算眼睛纵横比
        ear = (A + B) / (2.0 * C)
        return ear
        
    def detect_blink(self, frame):
        """检测眨眼动作"""
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 检测人脸
        faces = self.detector(gray, 0)
        
        for face in faces:
            # 检测面部特征点
            shape = self.predictor(gray, face)
            shape = face_utils.shape_to_np(shape)
            
            # 提取左右眼区域
            leftEye = shape[self.lStart:self.lEnd]
            rightEye = shape[self.rStart:self.rEnd]
            
            # 计算左右眼的纵横比
            leftEAR = self.eye_aspect_ratio(leftEye)
            rightEAR = self.eye_aspect_ratio(rightEye)
            
            # 平均纵横比
            ear = (leftEAR + rightEAR) / 2.0
            
            # 检查是否眨眼
            if ear < self.EYE_AR_THRESH:
                self.COUNTER += 1
            else:
                if self.COUNTER >= self.EYE_AR_CONSEC_FRAMES:
                    self.TOTAL += 1
                    if self.current_challenge == "blink":
                        self.blinks_detected += 1
                self.COUNTER = 0
                
        return self.TOTAL
        
    def generate_challenge(self):
        """生成随机活体检测挑战"""
        challenges = [
            ("blink", "Please blink 3 times", 3),  # (类型, 提示文字, 所需眨眼次数)
            ("look_left", "Please look left", 0),
            ("look_right", "Please look right", 0),
            ("nod", "Please nod your head", 0)
        ]
        
        if not self.current_challenge:
            challenge = random.choice(challenges)
            self.current_challenge = challenge[0]
            self.challenge_text = challenge[1]
            self.blinks_required = challenge[2]
            self.challenge_start_time = time.time()
            self.blinks_detected = 0
            return self.challenge_text
            
        return None
        
    def check_challenge_timeout(self):
        """检查当前挑战是否超时"""
        if self.challenge_start_time and time.time() - self.challenge_start_time > self.challenge_timeout:
            return True
        return False
        
    def process_frame(self, frame):
        """处理视频帧并返回检测结果"""
        if self.challenge_complete:
            return True, "Liveness check passed!", frame
            
        if self.check_challenge_timeout():
            self.reset_state()
            return False, "Challenge timeout. Please try again.", frame
            
        challenge_text = self.generate_challenge()
        if challenge_text:
            # 在帧上显示当前挑战
            cv2.putText(frame, challenge_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
        # 检测眨眼
        total_blinks = self.detect_blink(frame)
        
        # 根据不同挑战类型进行验证
        if self.current_challenge == "blink":
            if self.blinks_detected >= self.blinks_required:
                self.challenge_complete = True
                return True, "Liveness check passed!", frame
                
        # 添加其他动作检测逻辑...
        
        return None, challenge_text, frame 