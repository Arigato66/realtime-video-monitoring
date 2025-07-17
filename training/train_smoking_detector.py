from ultralytics import YOLO
import os
import yaml

# 确保目录存在
os.makedirs('datasets/smoking', exist_ok=True)

# 创建数据集配置文件
dataset_config = {
    'path': './datasets/smoking',  # 数据集根目录
    'train': 'train/images',       # 训练集图像路径
    'val': 'valid/images',         # 验证集图像路径
    'test': 'test/images',         # 测试集图像路径
    'names': {
        0: 'cigarette',            # 类别名称
    }
}

# 保存配置文件
with open('datasets/smoking/data.yaml', 'w') as f:
    yaml.dump(dataset_config, f)

def train_model():
    """
    训练香烟检测模型
    """
    print("开始训练香烟检测模型...")
    
    # 加载预训练的YOLOv8n模型
    model = YOLO('yolov8n.pt')
    
    # 开始训练
    results = model.train(
        data='datasets/smoking/data.yaml',
        epochs=100,               # 训练轮数
        imgsz=640,                # 图像大小
        batch=16,                 # 批次大小
        name='smoking_detector',  # 实验名称
        verbose=True              # 显示详细信息
    )
    
    # 验证模型
    model.val()
    
    # 将模型保存到指定位置
    os.makedirs('yolo-Weights', exist_ok=True)
    model_path = os.path.join('yolo-Weights', 'yolov8n-smoking.pt')
    model.export(format='pt', save=True)
    
    # 复制模型到指定位置
    import shutil
    shutil.copy('runs/detect/smoking_detector/weights/best.pt', model_path)
    
    print(f"模型训练完成，已保存到 {model_path}")
    return model_path

if __name__ == "__main__":
    train_model() 