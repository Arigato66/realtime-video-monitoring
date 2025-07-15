import sounddevice as sd
import numpy as np
import librosa
import tensorflow as tf
from threading import Thread, Event
import time
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "scream_detector_model.h5")

def load_model_with_fallback():
    try:
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(13,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        model.load_weights(MODEL_PATH)
        print("Model loaded successfully with weights fallback")
        return model
    except Exception as e2:
        print(f"Fallback model loading failed: {e2}")
        raise RuntimeError("Both model loading methods failed. Please check model file and compatibility.")

try:
    model = load_model_with_fallback()
except Exception as e:
    print(f"Critical error: {e}")
    exit(1)

def extract_features(audio, sr):
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
    return np.mean(mfcc.T, axis=0)

# 检测线程控制
scream_thread = None
scream_stop_event = Event()

# 检测主函数
def _scream_detect_worker(callback, samplerate=22050, interval=0.05):
    global scream_stop_event
    scream_active_until = 0
    def detect_scream(indata, frames, t, status):
        nonlocal scream_active_until
        audio_data = indata[:, 0]
        features = extract_features(audio_data, samplerate)
        prediction = model.predict(np.array([features]), verbose=0)[0][0]
        now = time.time()
        # 计算音量（RMS分贝，映射到0~1）
        rms = float(np.sqrt(np.mean(audio_data ** 2)))
        # 分贝归一化（常用音频范围-60dB~0dB，0dB为最大）
        db = 20 * np.log10(rms + 1e-8)
        # 归一化到0~1（-60dB为0，0dB为1）
        volume_norm = min(max((db + 60) / 60, 0), 1)
        if prediction > 0.7:
            scream_active_until = now + 60
        if now < scream_active_until:
            callback({'status': 'scream', 'prob': float(prediction), 'volume': volume_norm})
        else:
            callback({'status': 'normal', 'prob': float(prediction), 'volume': volume_norm})
    with sd.InputStream(callback=detect_scream, samplerate=samplerate, channels=1):
        while not scream_stop_event.is_set():
            time.sleep(interval)

def start_scream_detection(callback):
    global scream_thread, scream_stop_event
    if scream_thread and scream_thread.is_alive():
        return
    scream_stop_event.clear()
    scream_thread = Thread(target=_scream_detect_worker, args=(callback,), daemon=True)
    scream_thread.start()

def stop_scream_detection():
    global scream_stop_event, scream_thread
    scream_stop_event.set()
    if scream_thread:
        scream_thread.join(timeout=2)
        scream_thread = None
