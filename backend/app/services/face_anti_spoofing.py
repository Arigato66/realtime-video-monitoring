import random 
import cv2
import imutils
import time
import threading
from app.services import f_liveness_detection
from app.services import questions

# 全局变量，用于跟踪摄像头状态
_camera_in_use = threading.Lock()

def run_face_anti_spoofing():
    # 使用锁确保一次只有一个实例在运行
    if not _camera_in_use.acquire(blocking=False):
        print("另一个活体检测实例正在运行，请先关闭它")
        return
    
    try:
        _run_face_anti_spoofing_internal()
    finally:
        # 确保无论如何都释放锁
        _camera_in_use.release()

def _run_face_anti_spoofing_internal():
    # 确保在启动新摄像头前，先释放可能存在的摄像头资源
    try:
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"关闭窗口时出错: {str(e)}")
    
    # 延迟一段时间，确保之前的摄像头资源完全释放
    time.sleep(1)
    
    # 创建窗口
    cv2.namedWindow('liveness_detection')
    
    # 尝试多个摄像头索引
    cam = None
    for camera_index in [0, 1, 2]:
        try:
            # 在Windows上，尝试使用不同的API后端
            for api_preference in [cv2.CAP_ANY, cv2.CAP_DSHOW, cv2.CAP_MSMF]:
                try:
                    print(f"尝试使用API {api_preference}打开摄像头 {camera_index}")
                    cam = cv2.VideoCapture(camera_index, api_preference)
                    if cam is not None and cam.isOpened():
                        print(f"成功打开摄像头索引 {camera_index}，使用API {api_preference}")
                        # 设置摄像头属性以提高稳定性
                        cam.set(cv2.CAP_PROP_BUFFERSIZE, 3)
                        break
                    else:
                        print(f"无法使用API {api_preference}打开摄像头 {camera_index}")
                        if cam is not None:
                            cam.release()
                except Exception as e:
                    print(f"尝试使用API {api_preference}打开摄像头 {camera_index} 失败: {str(e)}")
            
            if cam is not None and cam.isOpened():
                break
        except Exception as e:
            print(f"尝试打开摄像头 {camera_index} 失败: {str(e)}")
    
    if cam is None or not cam.isOpened():
        print("无法打开任何摄像头，请检查设备连接")
        return
    
    # parameters 
    COUNTER, TOTAL = 0, 0
    counter_ok_questions = 0
    counter_ok_consecutives = 0
    limit_consecutives = 3
    limit_questions = 6
    counter_try = 0
    limit_try = 50 
    
    def show_image(cam, text, color=(0, 0, 255)):
        try:
            ret, im = cam.read()
            if not ret or im is None:
                print("无法读取摄像头帧")
                return None
            
            im = imutils.resize(im, width=720)
            cv2.putText(im, text, (10, 50), cv2.FONT_HERSHEY_COMPLEX, 1, color, 2)
            return im
        except Exception as e:
            print(f"读取摄像头帧时出错: {str(e)}")
            return None
    
    # 重置状态变量
    last_blink_time = time.time()
    
    try:
        for i_questions in range(0, limit_questions):
            # 生成随机问题
            index_question = random.randint(0, 5)
            question = questions.question_bank(index_question)
            
            # 显示问题
            im = show_image(cam, question)
            if im is None:
                # 尝试重新初始化摄像头
                print("尝试重新初始化摄像头...")
                cam.release()
                time.sleep(1)
                cam = cv2.VideoCapture(0)
                if not cam.isOpened():
                    print("无法重新初始化摄像头，退出检测")
                    break
                im = show_image(cam, question)
                if im is None:
                    print("仍然无法读取摄像头帧，退出检测")
                    break
                
            cv2.imshow('liveness_detection', im)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # q 或 ESC
                break 
            
            # 添加延迟，给用户时间阅读问题
            time.sleep(2)
            
            for i_try in range(limit_try):
                # 检查窗口是否仍然存在
                try:
                    if cv2.getWindowProperty('liveness_detection', cv2.WND_PROP_VISIBLE) < 1:
                        print("窗口已关闭，退出检测")
                        return
                except:
                    print("无法检查窗口状态，继续检测")
                
                # 读取摄像头帧
                try:
                    ret, im = cam.read()
                    if not ret or im is None:
                        print("无法读取摄像头帧，尝试重新初始化...")
                        cam.release()
                        time.sleep(1)
                        cam = cv2.VideoCapture(0)
                        if not cam.isOpened() or not cam.read()[0]:
                            print("无法重新初始化摄像头，退出检测")
                            return
                        continue
                        
                    im = imutils.resize(im, width=720)
                    im = cv2.flip(im, 1)
                except Exception as e:
                    print(f"处理摄像头帧时出错: {str(e)}")
                    continue
                
                # 检测活体
                try:
                    TOTAL_0 = TOTAL
                    out_model = f_liveness_detection.detect_liveness(im, COUNTER, TOTAL_0)
                    TOTAL = out_model['total_blinks']
                    COUNTER = out_model['count_blinks_consecutives']
                    dif_blink = TOTAL - TOTAL_0
                except Exception as e:
                    print(f"活体检测处理时出错: {str(e)}")
                    continue
                
                # 添加时间限制，避免快速通过
                current_time = time.time()
                if dif_blink > 0 and (current_time - last_blink_time) < 1.0:
                    # 如果眨眼间隔太短，忽略这次眨眼
                    TOTAL = TOTAL_0
                    dif_blink = 0
                elif dif_blink > 0:
                    last_blink_time = current_time
                    blinks_up = 1
                else:
                    blinks_up = 0
                
                # 判断挑战结果
                challenge_res = questions.challenge_result(question, out_model, blinks_up)
                
                # 显示当前状态
                im = show_image(cam, question)
                if im is None:
                    continue
                    
                cv2.imshow('liveness_detection', im)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # q 或 ESC
                    return
                
                # 处理通过情况
                if challenge_res == "pass":
                    im = show_image(cam, question + " : ok")
                    if im is None:
                        continue
                        
                    cv2.imshow('liveness_detection', im)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:
                        return
                    
                    counter_ok_consecutives += 1
                    if counter_ok_consecutives == limit_consecutives:
                        counter_ok_questions += 1
                        counter_try = 0
                        counter_ok_consecutives = 0
                        # 添加延迟，避免快速通过
                        time.sleep(1)
                        break
                    else:
                        # 添加延迟，避免快速通过
                        time.sleep(0.5)
                        continue
                
                elif challenge_res == "fail":
                    counter_try += 1
                    im = show_image(cam, question + " : fail")
                    if im is not None:
                        cv2.imshow('liveness_detection', im)
                        cv2.waitKey(1)
                    # 添加延迟，避免快速通过
                    time.sleep(0.5)
                elif i_try == limit_try - 1:
                    break
            
            # 检查是否完成所有问题
            if counter_ok_questions == limit_questions:
                result_time = time.time()
                while time.time() - result_time < 5:  # 显示结果5秒
                    im = show_image(cam, "LIVENESS SUCCESSFUL", color=(0, 255, 0))
                    if im is None:
                        break
                        
                    cv2.imshow('liveness_detection', im)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:
                        break
                    time.sleep(0.1)
                break
            elif i_try == limit_try - 1:
                result_time = time.time()
                while time.time() - result_time < 5:  # 显示结果5秒
                    im = show_image(cam, "LIVENESS FAIL")
                    if im is None:
                        break
                        
                    cv2.imshow('liveness_detection', im)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:
                        break
                    time.sleep(0.1)
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