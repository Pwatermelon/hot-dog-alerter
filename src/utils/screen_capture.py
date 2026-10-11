"""Быстрый захват экрана через mss (без pyautogui)."""
from __future__ import annotations

import os
import threading
import time
from typing import Callable, List, Optional, Tuple

import cv2
import mss
import numpy as np

from src.config import CONFIDENCE_THRESHOLD, MODEL_PATH, OVERLAY_SETTINGS
from src.detection.yolo_detector import HotDogDetector


class ScreenCapture:
    def __init__(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        detection_enabled: bool = True,
        overlay_callback: Optional[Callable] = None,
    ):
        self.region = region
        self.detection_enabled = detection_enabled
        self.running = False
        self.overlay_callback = overlay_callback
        self.detection_thread: Optional[threading.Thread] = None
        self.processing_lock = threading.Lock()
        self.latest_frame = None
        self.latest_detections: List[Tuple] = []
        self.detector = (
            HotDogDetector(MODEL_PATH, conf=CONFIDENCE_THRESHOLD)
            if detection_enabled
            else None
        )

    def capture_frame(self, sct: mss.mss) -> np.ndarray:
        if self.region:
            left, top, width, height = self.region
            monitor = {"left": left, "top": top, "width": width, "height": height}
        else:
            monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        frame = np.array(shot)[:, :, :3]  # BGRA → BGR
        return frame

    def process_frame(self, frame: np.ndarray) -> None:
        if not self.running or not self.detector:
            return
        result_frame, detected_objects = self.detector.detect_on_image(frame, draw=True)
        overlay_boxes = [
            (x1, y1, x2, y2, self.detector.classes.get(cls, str(cls)), conf)
            for cls, x1, y1, x2, y2, conf in detected_objects
        ]
        with self.processing_lock:
            self.latest_frame = result_frame
            self.latest_detections = overlay_boxes
            if self.overlay_callback:
                self.overlay_callback(overlay_boxes)

    def start_capture(
        self,
        callback=None,
        fps: int = 10,
        save_path: Optional[str] = None,
        use_overlay: bool = False,
    ) -> None:
        self.running = True
        delay = 1.0 / max(1, fps)
        frame_count = 0
        last_detection_time = time.time()

        if not use_overlay and save_path is None:
            save_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "screenshots"
            )
            os.makedirs(save_path, exist_ok=True)

        with mss.mss() as sct:
            try:
                while self.running:
                    start = time.time()
                    frame = self.capture_frame(sct)

                    if self.detection_enabled and self.detector:
                        if self.detection_thread is None or not self.detection_thread.is_alive():
                            self.detection_thread = threading.Thread(
                                target=self.process_frame, args=(frame.copy(),), daemon=True
                            )
                            self.detection_thread.start()

                        with self.processing_lock:
                            if self.latest_detections:
                                last_detection_time = time.time()
                            elapsed_ms = (time.time() - last_detection_time) * 1000
                            if (
                                use_overlay
                                and self.overlay_callback
                                and elapsed_ms > OVERLAY_SETTINGS["hide_timeout"]
                            ):
                                self.overlay_callback([])

                            if callback and self.latest_frame is not None:
                                callback(self.latest_frame)
                            elif (
                                not use_overlay
                                and save_path
                                and self.latest_frame is not None
                            ):
                                ts = time.strftime("%Y%m%d-%H%M%S")
                                path = os.path.join(
                                    save_path, f"hotdog_screen_{ts}_{frame_count:04d}.jpg"
                                )
                                cv2.imwrite(path, self.latest_frame)

                    frame_count += 1
                    sleep_for = delay - (time.time() - start)
                    if sleep_for > 0:
                        time.sleep(sleep_for)
            finally:
                self.stop_capture()

    def stop_capture(self) -> None:
        self.running = False
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)
        self.latest_frame = None
        self.latest_detections = []
