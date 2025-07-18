import os
import requests
import zipfile
import io
import shutil
from tqdm import tqdm

def download_file(url, save_path, description=None):
    """Download a file with progress bar"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get file size for progress bar
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kibibyte
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        desc = description if description else f"下载 {os.path.basename(save_path)}"
        
        with open(save_path, 'wb') as file, tqdm(
            desc=desc,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(block_size):
                size = file.write(data)
                bar.update(size)
                
        print(f"成功下载到 {save_path}")
        return True
    except Exception as e:
        print(f"下载文件时出错: {e}")
        return False

def download_and_extract_zip(url, extract_dir, description=None):
    """Download a zip file and extract its contents"""
    try:
        print(f"正在从 {url} 下载压缩文件")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get file size for progress bar
        total_size = int(response.headers.get('content-length', 0))
        
        # Create directory if it doesn't exist
        os.makedirs(extract_dir, exist_ok=True)
        
        # Download with progress bar
        desc = description if description else f"下载压缩文件"
        
        # Download to memory
        content = io.BytesIO()
        with tqdm(
            desc=desc,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = content.write(data)
                bar.update(size)
        
        # Extract zip
        content.seek(0)
        with zipfile.ZipFile(content) as z:
            print(f"正在解压到 {extract_dir}")
            z.extractall(extract_dir)
            
        print(f"成功解压到 {extract_dir}")
        return True
    except Exception as e:
        print(f"下载或解压文件时出错: {e}")
        return False

def download_required_models():
    """Download all required models for face anti-spoofing"""
    # Get the app directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    
    # 下载情绪检测模型
    emotion_model_dir = os.path.join(current_dir, 'emotion_detection', 'Modelos')
    os.makedirs(emotion_model_dir, exist_ok=True)
    
    emotion_model_file = os.path.join(emotion_model_dir, 'model_dropout.hdf5')
    if not os.path.exists(emotion_model_file):
        print("情绪检测模型不存在，尝试下载...")
        # 这里需要提供一个有效的下载链接，这只是一个示例
        emotion_model_url = "https://github.com/oarriaga/face_classification/raw/master/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5"
        try:
            download_file(emotion_model_url, emotion_model_file, "下载情绪检测模型")
            print(f"情绪检测模型已下载到 {emotion_model_file}")
        except Exception as e:
            print(f"下载情绪检测模型失败: {e}")
            print("请手动下载情绪检测模型并放置在 app/services/emotion_detection/Modelos/ 目录下")
    else:
        print(f"情绪检测模型已存在于 {emotion_model_file}")
    
    # 下载人脸检测模型
    haarcascade_dir = os.path.join(current_dir, 'profile_detection', 'haarcascades')
    os.makedirs(haarcascade_dir, exist_ok=True)
    
    haarcascade_files = {
        'haarcascade_frontalface_alt.xml': 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_alt.xml',
        'haarcascade_profileface.xml': 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_profileface.xml'
    }
    
    for filename, url in haarcascade_files.items():
        file_path = os.path.join(haarcascade_dir, filename)
        if not os.path.exists(file_path):
            print(f"下载 {filename}...")
            download_file(url, file_path, f"下载 {filename}")
        else:
            print(f"{filename} 已存在于 {file_path}")
    
    print("所有必要的模型文件已下载完成。")

if __name__ == "__main__":
    download_required_models() 