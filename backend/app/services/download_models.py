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
        
        desc = description if description else f"Downloading {os.path.basename(save_path)}"
        
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
                
        print(f"Successfully downloaded to {save_path}")
        return True
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False

def download_and_extract_zip(url, extract_dir, description=None):
    """Download a zip file and extract its contents"""
    try:
        print(f"Downloading zip from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Get file size for progress bar
        total_size = int(response.headers.get('content-length', 0))
        
        # Create directory if it doesn't exist
        os.makedirs(extract_dir, exist_ok=True)
        
        # Download with progress bar
        desc = description if description else f"Downloading zip"
        
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
            print(f"Extracting to {extract_dir}")
            z.extractall(extract_dir)
            
        print(f"Successfully extracted to {extract_dir}")
        return True
    except Exception as e:
        print(f"Error downloading or extracting zip: {e}")
        return False

def download_required_models():
    """Download all required models for face anti-spoofing"""
    # Get the app directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    
    # Create directories if they don't exist
    blink_model_dir = os.path.join(current_dir, 'blink_detection', 'model_landmarks')
    os.makedirs(blink_model_dir, exist_ok=True)
    
    # Download facial landmark predictor
    landmark_file = os.path.join(blink_model_dir, 'shape_predictor_68_face_landmarks.dat')
    if not os.path.exists(landmark_file):
        print("Downloading facial landmark predictor model...")
        landmark_url = "https://github.com/davisking/dlib-models/raw/master/shape_predictor_68_face_landmarks.dat.bz2"
        try:
            import bz2
            response = requests.get(landmark_url, stream=True)
            response.raise_for_status()
            
            # Decompress bz2 file
            decompressed_data = bz2.decompress(response.content)
            
            # Save decompressed data
            with open(landmark_file, 'wb') as f:
                f.write(decompressed_data)
                
            print(f"Successfully downloaded and extracted to {landmark_file}")
        except Exception as e:
            print(f"Error downloading facial landmark model: {e}")
            print("Trying alternative download...")
            # Alternative download link
            alt_url = "https://github.com/AKSHAYUBHAT/TensorFace/raw/master/openface/models/dlib/shape_predictor_68_face_landmarks.dat"
            download_file(alt_url, landmark_file, "Downloading facial landmark model (alternative)")
    else:
        print(f"Facial landmark model already exists at {landmark_file}")
    
    # Check if haarcascade files exist, download if not
    haarcascade_dir = os.path.join(current_dir, 'profile_detection', 'haarcascades')
    os.makedirs(haarcascade_dir, exist_ok=True)
    
    haarcascade_files = {
        'haarcascade_frontalface_alt.xml': 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_alt.xml',
        'haarcascade_profileface.xml': 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_profileface.xml'
    }
    
    for filename, url in haarcascade_files.items():
        file_path = os.path.join(haarcascade_dir, filename)
        if not os.path.exists(file_path):
            print(f"Downloading {filename}...")
            download_file(url, file_path, f"Downloading {filename}")
        else:
            print(f"{filename} already exists at {file_path}")
    
    print("All required models have been downloaded.")

if __name__ == "__main__":
    download_required_models() 