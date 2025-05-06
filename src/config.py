# Конфигурация приложения
# Используем стандартную модель YOLOv8, которая уже умеет распознавать хот-доги (класс 52)
import os
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "yolov8n.pt")  # Путь к весам YOLO
CONFIDENCE_THRESHOLD = 0.35  # Пониженный порог уверенности для лучшей детекции хот-догов
NMS_THRESHOLD = 0.4
CLASSES = {
    52: "hot dog",  # Класс 52 в COCO - это хот-дог
}

# Настройки оверлея
OVERLAY_SETTINGS = {
    "hide_timeout": 3000,  # Время в мс, через которое скрываются прямоугольники, если нет хот-догов
    "button_color": "rgba(255, 0, 0, 200)",  # Цвет кнопки закрытия
    "frame_color": (0, 255, 0),  # Цвет рамки (зеленый)
    "text_bg_color": (0, 0, 0, 180),  # Цвет фона текста
    "text_color": (255, 255, 255),  # Цвет текста
}

# Настройки звуковых уведомлений
SOUND_SETTINGS = {
    "enabled": True,  # Звуковые уведомления включены по умолчанию
    "sound_file": os.path.join(os.path.dirname(os.path.dirname(__file__)), "sounds", "hotdog_alert.mp3"),  # Звук уведомления (поддерживает MP3)
    "min_interval": 2000,  # Минимальный интервал между звуковыми уведомлениями (мс)
} 