"""Android-клиент Hot-Dog Alerter (камера + OpenCV DNN)."""
from __future__ import annotations

import os

import cv2
import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout

HOTDOG_CLASS_ID = 52
IMGSZ = 320
CONF = 0.35
NMS = 0.45

KV = """
<root>:
    orientation: 'vertical'
    padding: dp(16)
    spacing: dp(12)
    canvas.before:
        Color:
            rgba: 0.08, 0.06, 0.05, 1
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: 'HOT-DOG ALERTER'
        size_hint_y: None
        height: dp(40)
        font_size: '26sp'
        bold: True
        color: 0.96, 0.77, 0.09, 1

    Label:
        id: status
        text: 'Наведите камеру на хот-дог'
        size_hint_y: None
        height: dp(28)
        color: 0.91, 0.79, 0.63, 1

    Image:
        id: preview
        allow_stretch: True
        keep_ratio: True

    BoxLayout:
        size_hint_y: None
        height: dp(52)
        spacing: dp(10)
        Button:
            id: toggle
            text: 'Старт'
            background_color: 0.96, 0.77, 0.09, 1
            color: 0.1, 0.07, 0.05, 1
            on_press: root.toggle()
        Button:
            text: 'Выход'
            background_color: 0.84, 0.16, 0.16, 1
            on_press: app.stop()
"""


def resource(*parts: str) -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


class Detector:
    def __init__(self, model_path: str):
        self.net = cv2.dnn.readNetFromONNX(model_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

    def detect(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        scale = min(IMGSZ / h, IMGSZ / w)
        nh, nw = int(round(h * scale)), int(round(w * scale))
        resized = cv2.resize(frame, (nw, nh))
        canvas = np.full((IMGSZ, IMGSZ, 3), 114, dtype=np.uint8)
        top = (IMGSZ - nh) // 2
        left = (IMGSZ - nw) // 2
        canvas[top : top + nh, left : left + nw] = resized
        blob = cv2.dnn.blobFromImage(
            canvas, 1 / 255.0, (IMGSZ, IMGSZ), swapRB=True, crop=False
        )
        self.net.setInput(blob)
        out = self.net.forward()
        preds = np.squeeze(out)
        if preds.ndim == 3:
            preds = preds[0]
        if preds.shape[0] < preds.shape[1]:
            preds = preds.T

        boxes, scores = [], []
        for row in preds:
            cls_scores = row[4:]
            cls_id = int(np.argmax(cls_scores))
            score = float(cls_scores[cls_id])
            if cls_id != HOTDOG_CLASS_ID or score < CONF:
                continue
            cx, cy, bw, bh = row[:4]
            x1 = (cx - bw / 2 - left) / scale
            y1 = (cy - bh / 2 - top) / scale
            boxes.append([x1, y1, bw / scale, bh / scale])
            scores.append(score)

        if not boxes:
            return []
        idx = cv2.dnn.NMSBoxes(boxes, scores, CONF, NMS)
        result = []
        for i in np.array(idx).flatten():
            x, y, bw, bh = boxes[i]
            result.append((int(x), int(y), int(x + bw), int(y + bh), scores[i]))
        return result


class Root(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capture = None
        self.event = None
        self.detector = None
        self.running = False
        model = resource("models", "yolov8n.onnx")
        if os.path.exists(model):
            self.detector = Detector(model)
        else:
            self.ids.status.text = "Модель не найдена"

    def toggle(self):
        if self.running:
            self.stop_cam()
        else:
            self.start_cam()

    def start_cam(self):
        if not self.detector:
            return
        self.capture = cv2.VideoCapture(0)
        if not self.capture.isOpened():
            self.ids.status.text = "Камера недоступна"
            return
        self.running = True
        self.ids.toggle.text = "Стоп"
        self.event = Clock.schedule_interval(self.update, 1 / 12)

    def stop_cam(self):
        self.running = False
        self.ids.toggle.text = "Старт"
        if self.event:
            self.event.cancel()
            self.event = None
        if self.capture:
            self.capture.release()
            self.capture = None
        self.ids.status.text = "Остановлено"

    def update(self, _dt):
        ok, frame = self.capture.read()
        if not ok:
            return
        boxes = self.detector.detect(frame)
        for x1, y1, x2, y2, conf in boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 80), 2)
            cv2.putText(
                frame,
                f"hot dog {conf:.2f}",
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 200, 80),
                2,
            )
        self.ids.status.text = (
            f"Найдено: {len(boxes)}" if boxes else "Ищем хот-доги…"
        )
        buf = cv2.flip(frame, 0).tobytes()
        tex = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt="bgr")
        tex.blit_buffer(buf, colorfmt="bgr", bufferfmt="ubyte")
        self.ids.preview.texture = tex


class HotDogAndroidApp(App):
    def build(self):
        self.title = "Hot-Dog Alerter"
        Builder.load_string(KV)
        return Root()


if __name__ == "__main__":
    HotDogAndroidApp().run()
