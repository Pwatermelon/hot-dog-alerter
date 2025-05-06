import cv2
from ultralytics import YOLO
import numpy as np
import os
import sys

# Добавляем пути импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

# Импорты модулей приложения
from src.config import CLASSES

class HotDogDetector:
    def __init__(self, model_path, conf=0.5):
        self.model = YOLO(model_path)
        self.conf = conf
        self.classes = CLASSES  # Используем классы из config

    def detect_on_video(self, video_path, output_path=None, class_names=None):
        """
        Детектирует хот-доги на видео.
        
        Args:
            video_path (str): Путь к видеофайлу
            output_path (str, optional): Путь для сохранения обработанного видео
            class_names (dict, optional): Словарь с названиями классов (переопределяет self.classes)
        """
        # Используем self.classes по умолчанию, если не переданы class_names
        if class_names is None and hasattr(self, 'classes'):
            class_names = self.classes
            
        cap = cv2.VideoCapture(video_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        # Создаем имя выходного файла, если не передано
        if output_path is None:
            base_name = os.path.basename(video_path)
            name, ext = os.path.splitext(base_name)
            output_path = os.path.join(os.path.dirname(video_path), f"{name}_detected{ext}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        
        print(f"Обработка видео, результат будет сохранен в: {output_path}")
        
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Запускаем детекцию
            results = self.model(frame, conf=self.conf)
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    
                    # Если мы хотим отображать только хот-доги и текущий класс не хот-дог, пропускаем
                    if class_names and cls not in class_names:
                        continue
                        
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    
                    # Рамка зелёного цвета
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Название объекта и уверенность
                    label = f"{class_names.get(cls, str(cls))} {conf:.2f}"
                    cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            
            # Записываем результат в выходной файл
            out.write(frame)
            
            # Выводим прогресс
            frame_count += 1
            if frame_count % 10 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Обработано {frame_count}/{total_frames} кадров ({progress:.1f}%)")
                
        cap.release()
        out.release()
        
        print(f"Обработка завершена. Результат сохранен в: {output_path}")
        return output_path
        
    def detect_on_image(self, image):
        """
        Детектирует хот-доги на одном изображении.
        
        Args:
            image (numpy.ndarray): Входное изображение (BGR)
            
        Returns:
            numpy.ndarray: Изображение с отмеченными хот-догами
            list: Список найденных боксов в формате [(класс, x1, y1, x2, y2, conf), ...]
        """
        # Создаем копию изображения для рисования
        result_image = image.copy()
        
        # Запускаем детекцию
        results = self.model(image, conf=self.conf)
        
        detected_objects = []
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                
                # Если это не хот-дог, пропускаем
                if cls not in self.classes:
                    continue
                    
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                
                # Добавляем в список детекций
                detected_objects.append((cls, x1, y1, x2, y2, conf))
                
                # Рамка зелёного цвета
                cv2.rectangle(result_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Название объекта и уверенность
                label = f"{self.classes.get(cls, str(cls))} {conf:.2f}"
                cv2.putText(result_image, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        
        return result_image, detected_objects 