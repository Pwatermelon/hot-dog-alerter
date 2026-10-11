"""Глобальная конфигурация Hot-Dog Alerter."""
import os
import sys


def resource_path(*parts: str) -> str:
    """Путь к ресурсу: работает и из исходников, и из PyInstaller-бандла."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


APP_NAME = "Hot-Dog Alerter"
APP_VERSION = "1.1.0"

# Модель: компактный ONNX (без torch/ultralytics в рантайме)
MODEL_PATH = resource_path("models", "yolov8n.onnx")
MODEL_INPUT_SIZE = 320
CONFIDENCE_THRESHOLD = 0.35
NMS_THRESHOLD = 0.45
HOTDOG_CLASS_ID = 52
CLASSES = {HOTDOG_CLASS_ID: "hot dog"}

OVERLAY_SETTINGS = {
    "hide_timeout": 3000,
    "button_color": "rgba(214, 40, 40, 220)",
    "frame_color": (245, 197, 24),
    "text_bg_color": (26, 21, 18, 200),
    "text_color": (255, 248, 230),
}

SOUND_SETTINGS = {
    "enabled": True,
    "sound_file": resource_path("sounds", "hotdog_alert.mp3"),
    "min_interval": 2000,
}

STYLESHEET_PATH = resource_path("assets", "styles", "app.qss")
FONT_DIR = resource_path("assets", "fonts")
ICON_PATH = resource_path("assets", "icons", "app.png")
