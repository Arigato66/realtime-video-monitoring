import sounddevice as sd
import numpy as np
import librosa
import tensorflow as tf
import tkinter as tk
from threading import Thread

def load_model_with_fallback():
    # try:
    #     # 首选标准加载方式
    #     model = tf.keras.models.load_model("scream_detector_model.h5")
    #     print("Model loaded successfully with standard method")
    #     return model
    # except Exception as e:
    #     print(f"Standard model loading failed: {e}")
    #     print("Attempting fallback loading method...")
        
        try:
            # 备选方案：创建模型结构后加载权重
            # 修改模型结构为3层（与保存的模型层数匹配）
            model = tf.keras.Sequential([
                tf.keras.layers.Input(shape=(13,)),  # 13个MFCC特征
                tf.keras.layers.Dense(64, activation='relu'),
                tf.keras.layers.Dense(32, activation='relu'),  # 新增中间层
                tf.keras.layers.Dense(1, activation='sigmoid')
            ])
            model.load_weights("scream_detector_model.h5")
            print("Model loaded successfully with weights fallback")
            return model
        except Exception as e2:
            print(f"Fallback model loading failed: {e2}")
            raise RuntimeError("Both model loading methods failed. Please check model file and compatibility.")

# 加载模型
try:
    model = load_model_with_fallback()
except Exception as e:
    print(f"Critical error: {e}")
    # 提供更友好的错误提示
    error_msg = (
        "Failed to load model. Possible causes:\n"
        "1. Model file 'scream_detector_model.h5' is missing or corrupted\n"
        "2. TensorFlow version incompatibility\n"
        "3. Model structure mismatch (expected 3 layers but found 2 in fallback)\n\n"
        "Solutions:\n"
        "1. Check file exists and is accessible\n"
        "2. Ensure numpy version is <2 (run: pip install 'numpy<2')\n"
        "3. Re-train model with current TensorFlow version\n"
        "4. Verify model architecture in train_model.py"
    )
    print(error_msg)
    exit(1)

# Function to extract features from audio data
def extract_features(audio, sr):
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
    return np.mean(mfcc.T, axis=0)

# Function to process real-time audio
def detect_scream(indata, frames, time, status):
    audio_data = indata[:, 0]  
    features = extract_features(audio_data, 22050)  # Use 22050Hz sample rate

    # 修改：关闭预测进度条输出 (verbose=0)
    prediction = model.predict(np.array([features]), verbose=0)[0][0]

    if prediction > 0.5:
        # 修改:只更新GUI状态，不发送警报
        status_label.config(text="🚨 Scream detected!", fg="red")
    else:
        status_label.config(text="✅ No scream detected", fg="green")

# Function to start real-time detection
def start_detection():
    global stream
    status_label.config(text="🎤 Listening for screams...", fg="blue")
    stream = sd.InputStream(callback=detect_scream, samplerate=22050, channels=1)
    stream.start()
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)

# Function to stop detection
def stop_detection():
    global stream
    stream.stop()
    status_label.config(text="Detection Stopped ❌", fg="black")
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)

# GUI Setup
root = tk.Tk()
root.title("Scream Detection System")
root.geometry("400x300")
root.config(bg="white")

title_label = tk.Label(root, text="🔊 Scream Detection System", font=("Arial", 16, "bold"), fg="black", bg="white")
title_label.pack(pady=10)

status_label = tk.Label(root, text="Click Start to Begin", font=("Arial", 12), fg="gray", bg="white")
status_label.pack(pady=5)

start_button = tk.Button(root, text="Start Detection", font=("Arial", 12), command=lambda: Thread(target=start_detection).start(), bg="green", fg="white", padx=10, pady=5)
start_button.pack(pady=10)

stop_button = tk.Button(root, text="Stop Detection", font=("Arial", 12), command=stop_detection, bg="red", fg="white", padx=10, pady=5, state=tk.DISABLED)
stop_button.pack(pady=10)

root.mainloop()
