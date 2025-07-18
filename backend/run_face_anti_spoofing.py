import os
import sys
import urllib.request
import bz2

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 检查并下载dlib模型
def download_model_if_not_exists():
    # 检查blink_detection模型
    blink_model_path = os.path.join(current_dir, "app", "services", "blink_detection", "model_landmarks", "shape_predictor_68_face_landmarks.dat")
    os.makedirs(os.path.dirname(blink_model_path), exist_ok=True)
    
    if not os.path.exists(blink_model_path):
        print("正在下载眨眼检测模型，请稍候...")
        # 下载地址
        url = "https://github.com/davisking/dlib-models/raw/master/shape_predictor_68_face_landmarks.dat.bz2"
        bz2_path = blink_model_path + ".bz2"
        
        # 下载压缩文件
        urllib.request.urlretrieve(url, bz2_path)
        
        # 解压文件
        print("正在解压模型文件...")
        with bz2.BZ2File(bz2_path) as fr, open(blink_model_path, "wb") as fw:
            fw.write(fr.read())
        
        # 删除压缩文件
        os.remove(bz2_path)
        print("眨眼检测模型下载完成！")
    else:
        print("眨眼检测模型文件已存在，无需下载。")
    
    # 检查profile_detection模型
    profile_dir = os.path.join(current_dir, "app", "services", "profile_detection", "haarcascades")
    os.makedirs(profile_dir, exist_ok=True)
    
    frontal_face_path = os.path.join(profile_dir, "haarcascade_frontalface_alt.xml")
    profile_face_path = os.path.join(profile_dir, "haarcascade_profileface.xml")
    
    if not os.path.exists(frontal_face_path) or not os.path.exists(profile_face_path):
        print("正在下载人脸检测模型，请稍候...")
        
        # 下载正脸检测器
        frontal_url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_alt.xml"
        urllib.request.urlretrieve(frontal_url, frontal_face_path)
        
        # 下载侧脸检测器
        profile_url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_profileface.xml"
        urllib.request.urlretrieve(profile_url, profile_face_path)
        
        print("人脸检测模型下载完成！")
    else:
        print("人脸检测模型文件已存在，无需下载。")
    
    # 检查emotion_detection模型
    emotion_model_path = os.path.join(current_dir, "app", "services", "emotion_detection", "Modelos", "model_dropout.hdf5")
    os.makedirs(os.path.dirname(emotion_model_path), exist_ok=True)
    
    if not os.path.exists(emotion_model_path):
        print("情绪检测模型不存在，需要从其他来源获取。")
        print("请将情绪检测模型放置在以下位置：")
        print(emotion_model_path)
    else:
        print("情绪检测模型文件已存在。")

# 下载模型
download_model_if_not_exists()

try:
    # 导入活体检测服务
    from app.services.face_anti_spoofing import run_face_anti_spoofing
    
    # 脚本直接运行face_anti_spoofing.py中的代码
    print("启动活体检测...")
    print("按 'q' 键退出")
    
    # 运行活体检测
    run_face_anti_spoofing()
except Exception as e:
    print(f"启动活体检测失败: {str(e)}")
    import traceback
    traceback.print_exc() 