import torch
from ultralytics import YOLO
from supervision.draw.color import ColorPalette
from supervision import Detections, BoxAnnotator
import os

class SmokingDetectionService:
    def __init__(self, model_path='yolov8n.pt'):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = self.load_model(model_path)
        self.class_names = self.model.model.names
        self.box_annotator = BoxAnnotator(
            color=ColorPalette.from_hex(['#FF0000']), 
            thickness=2
        )

    def load_model(self, model_path):
        # 确保模型路径是绝对的
        if not os.path.isabs(model_path):
            # 修正路径，使其指向项目根目录下的 yolo-Weights
            model_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'yolo-Weights', 'smoking_detection.pt')
        
        model = YOLO(model_path)
        model.fuse()
        return model

    def predict(self, frame):
        return self.model(frame)

    def plot_bboxes(self, results, frame):
        detections = Detections(
            xyxy=results[0].boxes.xyxy.cpu().numpy(),
            confidence=results[0].boxes.conf.cpu().numpy(),
            class_id=results[0].boxes.cls.cpu().numpy().astype(int),
        )
        
        frame = self.box_annotator.annotate(scene=frame, detections=detections)
        
        is_smoking_detected = len(detections) > 0
        
        return frame, is_smoking_detected 