import os
import shutil
import requests
from zipfile import ZipFile
import gdown
from tqdm import tqdm

def download_file(url, output_path):
    """下载文件并显示进度条"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(output_path, 'wb') as file, tqdm(
        desc=output_path,
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)

def prepare_dataset():
    """准备香烟检测数据集"""
    print("开始准备香烟检测数据集...")
    
    # 创建必要的目录
    os.makedirs('datasets/smoking/train/images', exist_ok=True)
    os.makedirs('datasets/smoking/train/labels', exist_ok=True)
    os.makedirs('datasets/smoking/valid/images', exist_ok=True)
    os.makedirs('datasets/smoking/valid/labels', exist_ok=True)
    os.makedirs('datasets/smoking/test/images', exist_ok=True)
    os.makedirs('datasets/smoking/test/labels', exist_ok=True)
    
    # 从Google Drive下载数据集
    print("正在下载数据集...")
    
    # 这里我们使用一个开源的香烟检测数据集
    # 您需要替换为实际可用的数据集链接
    # 例如: https://drive.google.com/file/d/1234567890abcdef/view?usp=sharing
    dataset_url = "https://drive.google.com/uc?id=1234567890abcdef"
    
    try:
        output = "datasets/smoking_dataset.zip"
        gdown.download(dataset_url, output, quiet=False)
        
        # 解压数据集
        print("正在解压数据集...")
        with ZipFile(output, 'r') as zip_ref:
            zip_ref.extractall('datasets/smoking_temp')
        
        # 移动文件到正确的位置
        print("正在组织数据集文件...")
        
        # 这里的路径需要根据实际下载的数据集结构进行调整
        # 以下是一个示例
        for split in ['train', 'valid', 'test']:
            src_img_dir = f'datasets/smoking_temp/{split}/images'
            src_lbl_dir = f'datasets/smoking_temp/{split}/labels'
            
            dst_img_dir = f'datasets/smoking/{split}/images'
            dst_lbl_dir = f'datasets/smoking/{split}/labels'
            
            if os.path.exists(src_img_dir):
                for file in os.listdir(src_img_dir):
                    shutil.copy(
                        os.path.join(src_img_dir, file),
                        os.path.join(dst_img_dir, file)
                    )
            
            if os.path.exists(src_lbl_dir):
                for file in os.listdir(src_lbl_dir):
                    shutil.copy(
                        os.path.join(src_lbl_dir, file),
                        os.path.join(dst_lbl_dir, file)
                    )
        
        # 清理临时文件
        shutil.rmtree('datasets/smoking_temp')
        os.remove(output)
        
        print("数据集准备完成！")
        print(f"训练集图像: {len(os.listdir('datasets/smoking/train/images'))}")
        print(f"验证集图像: {len(os.listdir('datasets/smoking/valid/images'))}")
        print(f"测试集图像: {len(os.listdir('datasets/smoking/test/images'))}")
        
    except Exception as e:
        print(f"下载或准备数据集时出错: {e}")
        print("\n由于无法自动下载数据集，请按照以下步骤手动准备数据集:")
        print("1. 从任何公开的香烟检测数据集下载图像和标注")
        print("2. 按照YOLO格式组织数据集:")
        print("   - datasets/smoking/train/images/ (训练图像)")
        print("   - datasets/smoking/train/labels/ (训练标注)")
        print("   - datasets/smoking/valid/images/ (验证图像)")
        print("   - datasets/smoking/valid/labels/ (验证标注)")
        print("   - datasets/smoking/test/images/  (测试图像)")
        print("   - datasets/smoking/test/labels/  (测试标注)")
        print("3. 标注文件应为.txt格式，每行格式为: 类别ID x_center y_center width height")
        print("   例如: 0 0.5 0.5 0.1 0.2")
        print("4. 所有值都应归一化到0-1范围内")
        print("5. 准备好数据集后，运行 train_smoking_detector.py 开始训练")

if __name__ == "__main__":
    prepare_dataset() 