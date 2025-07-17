import cv2
import random

class FaceAntiSpoofingService:
    """Face Anti-Spoofing Service Class"""
    
    def __init__(self):
        """Initialize face anti-spoofing service"""
        # Status variables
        self.verification_status = "waiting"  # Status: waiting, in_progress, success, fail
        self.current_question = "Please wait..."
        
    def start_verification(self):
        """Start a new verification process"""
        self.verification_status = "in_progress"
        self.current_question = "Please face the camera"
        
    def process_frame(self, frame):
        """Process video frame and return results"""
        # Simply add text to the frame
        cv2.putText(frame, "Face Anti-Spoofing Mode - In Development", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.putText(frame, f"Instruction: {self.current_question}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Randomly change status for testing
        if random.random() < 0.001:  # 0.1% probability
            self.verification_status = "success"
        
        return frame, self.verification_status, self.current_question 