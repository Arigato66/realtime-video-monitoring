import os
import cv2
import numpy as np
from keras.models import load_model
import pickle

LIVENESS_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'liveness', 'liveness.model')
LE_PATH = os.path.join(os.path.dirname(__file__), 'liveness', 'le.pickle')

try:
    liveness_model = load_model(LIVENESS_MODEL_PATH)
except Exception as e:
    raise RuntimeError(f'活体检测模型加载失败: {e}')

with open(LE_PATH, 'rb') as f:
    le = pickle.load(f)

def predict_liveness(face_img):
    """
    输入: face_img (BGR, np.ndarray, 单个人脸区域)
    输出: (label, confidence)
    """
    face = cv2.resize(face_img, (32, 32))
    face = face.astype("float") / 255.0
    face = np.expand_dims(face, axis=0)
    preds = liveness_model.predict(face)[0]
    j = np.argmax(preds)
    label = le.classes_[j]
    confidence = float(preds[j])
    return label, confidence