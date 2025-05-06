import cv2
import numpy as np
import pyautogui
import time
import os
import sys
import threading

# Добавляем пути импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

# Импорты модулей приложения
from src.detection.yolo_detector import HotDogDetector
from src.config import MODEL_PATH, CONFIDENCE_THRESHOLD, OVERLAY_SETTINGS

class ScreenCapture:
    def __init__(self, region=None, detection_enabled=True, overlay_callback=None):
        """
        Инициализация захвата экрана.
        
        Args:
            region (tuple, optional): Область захвата (left, top, width, height).
                                      None для полного экрана.
            detection_enabled (bool): Включить детекцию хот-догов на захваченных кадрах.
            overlay_callback (callable, optional): Функция обратного вызова для отправки 
                                                  данных обнаружения на оверлей.
        """
        self.region = region
        self.detection_enabled = detection_enabled
        self.running = False
        self.overlay_callback = overlay_callback
        self.pause_detection = False
        self.detection_thread = None
        self.processing_lock = threading.Lock()
        self.latest_frame = None
        self.latest_detections = []
        
        # Создаем детектор, если нужна детекция
        if detection_enabled:
            self.detector = HotDogDetector(MODEL_PATH, conf=CONFIDENCE_THRESHOLD)
    
    def capture_frame(self):
        """
        Захват одного кадра с экрана.
        
        Returns:
            numpy.ndarray: Захваченный кадр в формате OpenCV (BGR).
        """
        screenshot = pyautogui.screenshot(region=self.region)
        frame = np.array(screenshot)
        # Конвертация из RGB в BGR для OpenCV
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    def process_frame(self, frame):
        """
        Обрабатывает кадр для обнаружения хот-догов.
        Этот метод будет вызываться в отдельном потоке.
        """
        if not self.running or self.pause_detection:
            return
            
        # Обнаруживаем хот-доги на кадре
        result_frame, detected_objects = self.detector.detect_on_image(frame)
        
        # Обновляем последние обнаружения
        with self.processing_lock:
            self.latest_frame = result_frame
            
            # Преобразуем detected_objects в формат для оверлея
            overlay_boxes = []
            for cls, x1, y1, x2, y2, conf in detected_objects:
                class_name = self.detector.classes.get(cls, str(cls))
                overlay_boxes.append((x1, y1, x2, y2, class_name, conf))
            
            self.latest_detections = overlay_boxes
            
            # Вызываем callback для обновления оверлея
            if self.overlay_callback and self.latest_detections:
                self.overlay_callback(self.latest_detections)
    
    def start_capture(self, callback=None, fps=10, save_path=None, use_overlay=False):
        """
        Начать непрерывный захват экрана.
        
        Args:
            callback (callable, optional): Функция обратного вызова для обработки кадра.
                                          Если None и включена детекция, будет сохранять кадры.
            fps (int, optional): Целевое количество кадров в секунду.
            save_path (str, optional): Папка для сохранения скриншотов.
            use_overlay (bool, optional): Использовать прозрачный оверлей вместо сохранения кадров.
        """
        self.running = True
        delay = 1.0 / fps
        
        # Папка для сохранения скриншотов по умолчанию, если оверлей не используется
        if not use_overlay and save_path is None:
            save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
            # Создаем папку, если она не существует
            if not os.path.exists(save_path):
                os.makedirs(save_path)
        
        if use_overlay:
            print("Захват экрана запущен. Нажмите ESC для выхода.")
            
        frame_count = 0
        last_detection_time = time.time()
        
        try:
            while self.running:
                start_time = time.time()
                
                # Захватываем кадр
                frame = self.capture_frame()
                
                # Если включена детекция, обрабатываем кадр
                if self.detection_enabled:
                    # Запускаем обработку в отдельном потоке, если ещё не запущен или не активен
                    if self.detection_thread is None or not self.detection_thread.is_alive():
                        self.detection_thread = threading.Thread(target=self.process_frame, args=(frame.copy(),))
                        self.detection_thread.daemon = True
                        self.detection_thread.start()
                    
                    # Используем ранее обнаруженные объекты для оверлея
                    with self.processing_lock:
                        if self.latest_detections and use_overlay:
                            # Обновляем время последнего обнаружения
                            if self.latest_detections:
                                last_detection_time = time.time()
                            
                            # Проверяем, не прошло ли слишком много времени с момента последнего обнаружения
                            current_time = time.time()
                            time_since_last_detection = (current_time - last_detection_time) * 1000
                            
                            # Если прошло больше времени, чем hide_timeout, снимаем отметки с оверлея
                            if time_since_last_detection > OVERLAY_SETTINGS["hide_timeout"]:
                                if self.overlay_callback:
                                    self.overlay_callback([])  # Отправляем пустой список для скрытия отметок
                            
                        # Если есть callback или нужно сохранять кадры, но не используется оверлей
                        if callback:
                            result_frame = self.latest_frame if self.latest_frame is not None else frame
                            callback(result_frame)
                        elif not use_overlay and self.latest_frame is not None:
                            # Сохраняем кадр на диск
                            timestamp = time.strftime("%Y%m%d-%H%M%S")
                            filename = os.path.join(save_path, f"hotdog_screen_{timestamp}_{frame_count:04d}.jpg")
                            cv2.imwrite(filename, self.latest_frame)
                            
                            # Если обнаружены хот-доги, выводим сообщение
                            if self.latest_detections:
                                print(f"Обнаружено хот-догов: {len(self.latest_detections)}")
                else:
                    # Если нет детекции, просто сохраняем кадр или передаем в callback
                    if callback:
                        callback(frame)
                    elif not use_overlay:
                        timestamp = time.strftime("%Y%m%d-%H%M%S")
                        filename = os.path.join(save_path, f"screen_{timestamp}_{frame_count:04d}.jpg")
                        cv2.imwrite(filename, frame)
                
                frame_count += 1
                
                # Контроль частоты кадров
                process_time = time.time() - start_time
                sleep_time = max(0, delay - process_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            print("Захват экрана остановлен")
        finally:
            self.stop_capture()
            if use_overlay:
                print("Захват экрана завершен.")
            
    def stop_capture(self):
        """Останавливает захват экрана."""
        self.running = False
        
        # Если есть активный поток детекции, ждем его завершения
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)
            
        # Очищаем ресурсы
        self.latest_frame = None
        self.latest_detections = []

# Пример использования
if __name__ == "__main__":
    # Создаем захват экрана с детекцией хот-догов
    screen_cap = ScreenCapture(detection_enabled=True)
    # Запускаем захват
    screen_cap.start_capture(fps=5)  # Меньший FPS для меньшей нагрузки 