import argparse
import os
from app import create_app
from ultralytics import YOLO
from app.services import db_initial

def main():
    # 解决 "OMP: Error #15" 警告
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    parser = argparse.ArgumentParser(description="Flask API exposing YOLOv8 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    parser.add_argument("--host", default="0.0.0.0", help="host address")
    args = parser.parse_args()
    
    # 初始化YOLO模型
    model = YOLO("yolov8n.pt")
    
    # 创建Flask应用
    app = create_app()
    
    print(f"API server starting on http://{args.host}:{args.port}")
    # 禁用自动重载 (use_reloader=False) 来防止服务因文件变化而意外重启
    app.run(host=args.host, port=args.port, debug=True, use_reloader=False)

if __name__ == "__main__":
    # 初始化数据库
    db_initial.init_database()

    main() 