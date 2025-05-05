import cv2
from ultralytics import YOLO
import numpy as np

class HotDogDetector:
    def __init__(self, model_path, conf=0.5):
        self.model = YOLO(model_path)
        self.conf = conf

    def detect_on_video(self, video_path, output_path=None, class_names=None):
        cap = cv2.VideoCapture(video_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = None
        if output_path:
            fps = cap.get(cv2.CAP_PROP_FPS)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            results = self.model(frame, conf=self.conf)
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    if class_names and class_names[cls] != 'hot dog':
                        continue
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = class_names[cls] if class_names else str(cls)
                    cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            if out:
                out.write(frame)
            cv2.imshow('Hot-Dog Detection', frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break
        cap.release()
        if out:
            out.release()
        cv2.destroyAllWindows() 