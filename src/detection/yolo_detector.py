"""Детектор хот-догов на OpenCV DNN + YOLOv8 ONNX (без torch)."""
from __future__ import annotations

import os
from typing import List, Optional, Tuple

import cv2
import numpy as np

from src.config import (
    CLASSES,
    HOTDOG_CLASS_ID,
    MODEL_INPUT_SIZE,
    MODEL_PATH,
    NMS_THRESHOLD,
)


Detection = Tuple[int, int, int, int, int, float]  # cls, x1, y1, x2, y2, conf


class HotDogDetector:
    def __init__(
        self,
        model_path: str = MODEL_PATH,
        conf: float = 0.35,
        imgsz: int = MODEL_INPUT_SIZE,
        nms: float = NMS_THRESHOLD,
    ):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Модель не найдена: {model_path}\n"
                "Скачайте yolov8n.onnx в папку models/ или запустите scripts/export_onnx.py"
            )
        self.model_path = model_path
        self.conf = conf
        self.imgsz = imgsz
        self.nms = nms
        self.classes = CLASSES
        self.net = cv2.dnn.readNetFromONNX(model_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    def _letterbox(
        self, image: np.ndarray
    ) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        h, w = image.shape[:2]
        scale = min(self.imgsz / h, self.imgsz / w)
        nh, nw = int(round(h * scale)), int(round(w * scale))
        resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((self.imgsz, self.imgsz, 3), 114, dtype=np.uint8)
        top = (self.imgsz - nh) // 2
        left = (self.imgsz - nw) // 2
        canvas[top : top + nh, left : left + nw] = resized
        return canvas, scale, (left, top)

    def _infer(self, image: np.ndarray) -> List[Detection]:
        blob_img, scale, (pad_x, pad_y) = self._letterbox(image)
        blob = cv2.dnn.blobFromImage(
            blob_img, 1 / 255.0, (self.imgsz, self.imgsz), swapRB=True, crop=False
        )
        self.net.setInput(blob)
        outputs = self.net.forward()

        # YOLOv8: (1, 84, N) → (N, 84)
        preds = np.squeeze(outputs)
        if preds.ndim == 3:
            preds = preds[0]
        if preds.shape[0] < preds.shape[1]:
            preds = preds.T

        boxes: List[List[float]] = []
        scores: List[float] = []

        for row in preds:
            class_scores = row[4:]
            cls_id = int(np.argmax(class_scores))
            score = float(class_scores[cls_id])
            if cls_id != HOTDOG_CLASS_ID or score < self.conf:
                continue

            cx, cy, bw, bh = row[:4]
            x1 = (cx - bw / 2 - pad_x) / scale
            y1 = (cy - bh / 2 - pad_y) / scale
            x2 = (cx + bw / 2 - pad_x) / scale
            y2 = (cy + bh / 2 - pad_y) / scale
            boxes.append([x1, y1, x2 - x1, y2 - y1])
            scores.append(score)

        if not boxes:
            return []

        indices = cv2.dnn.NMSBoxes(boxes, scores, self.conf, self.nms)
        if len(indices) == 0:
            return []

        h, w = image.shape[:2]
        detections: List[Detection] = []
        for i in np.array(indices).flatten():
            x, y, bw, bh = boxes[i]
            x1 = max(0, int(x))
            y1 = max(0, int(y))
            x2 = min(w - 1, int(x + bw))
            y2 = min(h - 1, int(y + bh))
            detections.append((HOTDOG_CLASS_ID, x1, y1, x2, y2, scores[i]))
        return detections

    def detect_on_image(
        self, image: np.ndarray, draw: bool = True
    ) -> Tuple[np.ndarray, List[Detection]]:
        detections = self._infer(image)
        result = image.copy()
        if draw:
            for cls, x1, y1, x2, y2, conf in detections:
                cv2.rectangle(result, (x1, y1), (x2, y2), (0, 200, 80), 2)
                label = f"{self.classes.get(cls, str(cls))} {conf:.2f}"
                cv2.putText(
                    result,
                    label,
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 200, 80),
                    2,
                )
        return result, detections

    def detect_on_video(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        progress_callback=None,
    ) -> str:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {video_path}")

        if output_path is None:
            base = os.path.basename(video_path)
            name, ext = os.path.splitext(base)
            output_path = os.path.join(os.path.dirname(video_path), f"{name}_detected{ext or '.mp4'}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        out = cv2.VideoWriter(
            output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
        )

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            annotated, _ = self.detect_on_image(frame, draw=True)
            out.write(annotated)
            frame_idx += 1
            if progress_callback and total:
                progress_callback(frame_idx / total)

        cap.release()
        out.release()
        return output_path
