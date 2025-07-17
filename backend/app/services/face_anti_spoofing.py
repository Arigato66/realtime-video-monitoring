import random 
import cv2
import imutils
import time
import os
from app.services import f_utils
from app.services.profile_detection import f_detector
from app.services.emotion_detection import f_emotion_detection
import numpy as np
import dlib
from app.services import config
from app.services.download_models import download_required_models

# 全局变量，用于指示使用哪种人脸检测器
USE_DLIB = True

# 检查并下载所需的模型文件
def ensure_models_exist():
    # 检查情绪检测模型
    if not os.path.exists(config.path_model):
        print("情绪检测模型不存在，请确保已下载模型文件")
        return False
    
    # 检查人脸检测模型
    if not os.path.exists(config.detect_frontal_face) or not os.path.exists(config.detect_perfil_face):
        print("人脸检测模型不存在，正在下载...")
        download_required_models()
    
    return True

# 确保模型文件存在
if not ensure_models_exist():
    print("无法找到所需的模型文件，请确保已下载")

# 初始化检测器
try:
    # 检查dlib是否有get_frontal_face_detector方法
    if hasattr(dlib, 'get_frontal_face_detector'):
        frontal_face_detector = dlib.get_frontal_face_detector()
        print("成功初始化dlib人脸检测器")
    else:
        raise AttributeError("dlib模块没有get_frontal_face_detector方法")
except Exception as e:
    print(f"初始化dlib人脸检测器失败: {str(e)}")
    # 使用OpenCV的人脸检测器作为备用
    # 检查cv2是否有data属性
    if hasattr(cv2, 'data'):
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    else:
        # 使用绝对路径
        cascade_path = config.detect_frontal_face
    
    frontal_face_detector = cv2.CascadeClassifier(cascade_path)
    USE_DLIB = False
    print(f"使用OpenCV人脸检测器作为备用，路径: {cascade_path}")

# 初始化其他检测器
try:
    profile_detector = f_detector.detect_face_orientation()
    print("成功初始化侧脸检测器")
except Exception as e:
    print(f"初始化侧脸检测器失败: {str(e)}")

try:
    emotion_detector = f_emotion_detection.predict_emotions()
    print("成功初始化情绪检测器")
except Exception as e:
    print(f"初始化情绪检测器失败: {str(e)}")

def detect_faces(gray):
    """根据不同的检测器类型检测人脸"""
    global USE_DLIB
    
    if USE_DLIB:
        # 使用dlib检测器
        try:
            rectangles = frontal_face_detector(gray, 0)
            return rectangles
        except Exception as e:
            print(f"dlib人脸检测失败: {str(e)}")
            # 如果dlib检测失败，尝试使用OpenCV
            USE_DLIB = False
            print("切换到OpenCV人脸检测器")
            return detect_faces(gray)
    else:
        # 使用OpenCV检测器
        faces = frontal_face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        # 将OpenCV格式转换为dlib格式
        rectangles = []
        for (x, y, w, h) in faces:
            # 检查dlib是否有rectangle类
            try:
                if hasattr(dlib, 'rectangle'):
                    rect = dlib.rectangle(x, y, x+w, y+h)
                else:
                    # 创建一个类似dlib.rectangle的对象
                    class Rectangle:
                        def __init__(self, left, top, right, bottom):
                            self.left = left
                            self.top = top
                            self.right = right
                            self.bottom = bottom
                            
                    rect = Rectangle(x, y, x+w, y+h)
                rectangles.append(rect)
            except Exception as e:
                print(f"创建dlib.rectangle对象失败: {str(e)}")
        return rectangles

def run_face_anti_spoofing():
    # 创建窗口
    cv2.namedWindow('liveness_detection', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('liveness_detection', 800, 600)
    
    # 尝试打开摄像头
    print("正在打开摄像头...")
    cam = None
    for api_preference in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
        try:
            cam = cv2.VideoCapture(0, api_preference)
            if cam.isOpened():
                print(f"成功打开摄像头，使用API {api_preference}")
                break
        except Exception as e:
            print(f"尝试使用API {api_preference}打开摄像头失败: {str(e)}")
    
    if cam is None or not cam.isOpened():
        print("无法打开摄像头，请检查设备连接")
        return
    
    # parameters 
    COUNTER, TOTAL = 0, 0
    counter_ok_questions = 0
    counter_ok_consecutives = 0
    limit_consecutives = 3
    limit_questions = 5  # 修改为5个问题，因为删除了眨眼检测
    counter_try = 0
    limit_try = 50 
    
    def show_image(cam, text, color=(0, 0, 255)):
        ret, im = cam.read()
        if not ret or im is None:
            print("无法读取摄像头帧")
            return None
        im = imutils.resize(im, width=720)
        cv2.putText(im, text, (10, 50), cv2.FONT_HERSHEY_COMPLEX, 1, color, 2)
        return im
    
    try:
        # 导入questions模块
        from app.services import questions
        
        for i_questions in range(0, limit_questions):
            # 生成随机问题
            index_question = random.randint(0, 4)  # 修改为0-4，因为删除了眨眼检测
            question = questions.question_bank(index_question)
            
            print(f"当前问题: {question}")
            im = show_image(cam, question)
            if im is None:
                break
                
            cv2.imshow('liveness_detection', im)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break 
            
            # 给用户时间阅读问题
            time.sleep(2)
            
            for i_try in range(limit_try):
                # 读取摄像头帧
                ret, im = cam.read()
                if not ret or im is None:
                    print("无法读取摄像头帧")
                    break
                    
                im = imutils.resize(im, width=720)
                im = cv2.flip(im, 1)
                
                # 灰度转换
                gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                
                # 人脸检测
                rectangles = detect_faces(gray)
                boxes_face = f_utils.convert_rectangles2array(rectangles, im)
                if len(boxes_face) != 0:
                    # 使用最大的人脸
                    areas = f_utils.get_areas(boxes_face)
                    index = np.argmax(areas)
                    if USE_DLIB:
                        rectangles = rectangles[index]
                    else:
                        rectangles = rectangles[0] if rectangles else None
                    boxes_face = [list(boxes_face[index])]
                    
                    # 情绪检测
                    _, emotion = emotion_detector.get_emotion(im, boxes_face)
                    
                    # 在图像上绘制人脸框
                    x0, y0, x1, y1 = boxes_face[0]
                    cv2.rectangle(im, (x0, y0), (x1, y1), (0, 255, 0), 2)
                else:
                    boxes_face = []
                    emotion = []
                
                # 侧脸检测
                box_orientation, orientation = profile_detector.face_orientation(gray)
                
                # 输出结果
                output = {
                    'box_face_frontal': boxes_face,
                    'box_orientation': box_orientation,
                    'emotion': emotion,
                    'orientation': orientation
                }
                
                # 判断挑战结果
                challenge_res = questions.challenge_result(question, output, 0)  # 第三个参数不再使用
                
                # 显示当前状态
                im = show_image(cam, question)
                if im is None:
                    break
                    
                cv2.imshow('liveness_detection', im)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break 
                
                # 处理通过情况
                if challenge_res == "pass":
                    im = show_image(cam, question + " : ok", color=(0, 255, 0))
                    if im is None:
                        break
                        
                    cv2.imshow('liveness_detection', im)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    
                    print(f"挑战通过: {question}")
                    counter_ok_consecutives += 1
                    if counter_ok_consecutives == limit_consecutives:
                        counter_ok_questions += 1
                        counter_try = 0
                        counter_ok_consecutives = 0
                        break
                    else:
                        continue
                
                elif challenge_res == "fail":
                    counter_try += 1
                    im = show_image(cam, question + " : fail", color=(0, 0, 255))
                    if im is not None:
                        cv2.imshow('liveness_detection', im)
                        cv2.waitKey(1)
                elif i_try == limit_try - 1:
                    break
                    
            # 检查是否完成所有问题
            if counter_ok_questions == limit_questions:
                while True:
                    im = show_image(cam, "LIVENESS SUCCESSFUL", color=(0, 255, 0))
                    if im is None:
                        break
                        
                    cv2.imshow('liveness_detection', im)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    time.sleep(0.1)
                
                # 显示3秒后自动关闭窗口
                time.sleep(3)
                break
            elif i_try == limit_try - 1:
                while True:
                    im = show_image(cam, "LIVENESS FAIL", color=(0, 0, 255))
                    if im is None:
                        break
                        
                    cv2.imshow('liveness_detection', im)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    time.sleep(0.1)
                
                # 显示3秒后自动关闭窗口
                time.sleep(3)
                break
            else:
                continue
    except Exception as e:
        print(f"活体检测过程中出现错误: {str(e)}")
    finally:
        # 释放资源
        print("正在释放摄像头资源...")
        if cam is not None:
            cam.release()
        cv2.destroyAllWindows()
        print("摄像头资源已释放")

# 如果直接运行这个文件，则执行活体检测
if __name__ == "__main__":
    run_face_anti_spoofing() 