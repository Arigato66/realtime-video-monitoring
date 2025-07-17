import os
import sys
import urllib.request
import bz2

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 检查并下载dlib模型
def download_model_if_not_exists():
    model_path = os.path.join(current_dir, "shape_predictor_68_face_landmarks.dat")
    if not os.path.exists(model_path):
        print("正在下载面部特征点预测器模型，请稍候...")
        # 下载地址
        url = "https://github.com/davisking/dlib-models/raw/master/shape_predictor_68_face_landmarks.dat.bz2"
        bz2_path = model_path + ".bz2"
        
        # 下载压缩文件
        urllib.request.urlretrieve(url, bz2_path)
        
        # 解压文件
        print("正在解压模型文件...")
        with bz2.BZ2File(bz2_path) as fr, open(model_path, "wb") as fw:
            fw.write(fr.read())
        
        # 删除压缩文件
        os.remove(bz2_path)
        print("模型下载完成！")
    else:
        print("模型文件已存在，无需下载。")

# 下载模型
download_model_if_not_exists()

# 导入活体检测服务
from app.services.face_anti_spoofing import run_face_anti_spoofing

# 脚本直接运行face_anti_spoofing.py中的代码
print("启动活体检测...")
print("按 'q' 键退出")

# 运行活体检测
run_face_anti_spoofing() 