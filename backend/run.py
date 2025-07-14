import argparse
import os

# --- 设置DeepFace模型下载路径 ---
# 获取项目根目录 (backend/..)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# 定义模型存储路径
deepface_home = os.path.join(project_root, 'data', '.deepface_models')
# 设置环境变量，DeepFace会使用这个路径
os.environ['DEEPFACE_HOME'] = deepface_home
# 确保目录存在
os.makedirs(deepface_home, exist_ok=True)
# --- 结束设置 ---

from app import create_app
from ultralytics import YOLO
from app.services import db_initial

def main():
    # 解决 "OMP: Error #15" 警告
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    try:
        import cv2
        if not hasattr(cv2, 'setNumThreads'):
            cv2.setNumThreads = lambda x: None
        cv2.setNumThreads(0)
    except Exception:
        pass
    
    import ultralytics
    parser = argparse.ArgumentParser(description="Flask API exposing YOLOv8 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    parser.add_argument("--host", default="0.0.0.0", help="host address")
    args = parser.parse_args()
    
    # 初始化YOLO模型
    model = YOLO("yolo-Weights/yolov8n.pt")
    
    # 创建Flask应用
    app = create_app()
    
    print(f"API server starting on http://{args.host}:{args.port}")
    # 禁用自动重载 (use_reloader=False) 来防止服务因文件变化而意外重启
    app.run(host=args.host, port=args.port, debug=True, use_reloader=False)

if __name__ == "__main__":
    # 初始化数据库
    db_initial.init_database()

    main() 