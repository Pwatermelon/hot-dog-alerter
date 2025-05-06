import sys
import os
import time
from PyQt5.QtWidgets import QWidget, QApplication, QPushButton
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QTimer, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# Добавляем пути импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

# Импорт настроек
from src.config import OVERLAY_SETTINGS, SOUND_SETTINGS

class DetectionOverlay(QWidget):
    """
    Прозрачный оверлей для отображения обнаруженных объектов поверх экрана.
    """
    closed = pyqtSignal()  # Сигнал, отправляемый при закрытии оверлея
    
    def __init__(self):
        super().__init__()
        self.boxes = []  # Список обнаруженных боксов [(x1, y1, x2, y2, class_name, conf), ...]
        self.last_update_time = None  # Время последнего обновления с боксами
        self.show_boxes = True  # Флаг отображения боксов
        self.hide_timeout = OVERLAY_SETTINGS["hide_timeout"]  # Время в мс, через которое скрываются прямоугольники, если нет хот-догов
        self.sound_enabled = SOUND_SETTINGS["enabled"]  # Включены ли звуковые уведомления
        self.sound_file = SOUND_SETTINGS["sound_file"]  # Путь к звуковому файлу
        self.min_sound_interval = SOUND_SETTINGS["min_interval"]  # Минимальный интервал между звуками
        self.last_sound_time = 0  # Время последнего звукового уведомления
        
        # Инициализируем таймер для скрытия прямоугольников
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.check_boxes_age)
        self.hide_timer.start(1000)  # Проверка каждую секунду
        
        # Подготавливаем медиаплеер для звуков
        self.sound_player = None
        if self.sound_enabled and os.path.exists(self.sound_file):
            self.sound_player = QMediaPlayer()
            # Проверяем расширение файла
            file_url = QUrl.fromLocalFile(self.sound_file)
            self.sound_player.setMedia(QMediaContent(file_url))
            self.sound_player.setVolume(70)  # Громкость 70%
        
        self.init_ui()
        
    def init_ui(self):
        # Устанавливаем флаги для создания прозрачного окна поверх всех других окон
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint | 
            Qt.Tool
        )
        # Делаем окно полностью прозрачным
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Разворачиваем на весь экран
        self.setGeometry(QApplication.desktop().screenGeometry())
        
        # Создаем кнопку закрытия
        self.close_button = QPushButton("✕", self)
        self.close_button.setFont(QFont("Arial", 12))
        self.close_button.setStyleSheet(
            "QPushButton {"
            f"   background-color: {OVERLAY_SETTINGS['button_color']};"
            "   color: white;"
            "   border: none;"
            "   border-radius: 15px;"
            "   padding: 5px;"
            "   width: 30px;"
            "   height: 30px;"
            "}"
            "QPushButton:hover {"
            "   background-color: red;"
            "}"
        )
        self.close_button.move(20, 20)
        self.close_button.clicked.connect(self.close)
        
        # Не делаем окно прозрачным для событий мыши, только в области кнопки
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
    def enable_sound(self, enabled):
        """
        Включает или выключает звуковые уведомления.
        
        Args:
            enabled (bool): True для включения, False для выключения.
        """
        self.sound_enabled = enabled
        
    def play_notification_sound(self):
        """
        Воспроизводит звук уведомления, если прошло достаточно времени с момента последнего звука.
        """
        if not self.sound_enabled or not self.sound_player:
            return
        
        current_time = int(time.time() * 1000)  # Текущее время в мс
        if current_time - self.last_sound_time >= self.min_sound_interval:
            # Если плеер уже играет, сначала остановим его
            if self.sound_player.state() == QMediaPlayer.PlayingState:
                self.sound_player.stop()
            
            # Начинаем воспроизведение
            self.sound_player.play()
            self.last_sound_time = current_time
            
            # Выводим отладочную информацию
            print(f"Воспроизведение звука: {self.sound_file}")
        
    def update_boxes(self, boxes):
        """
        Обновляет список боксов для отображения.
        
        Args:
            boxes: список кортежей (x1, y1, x2, y2, class_name, conf)
        """
        # Проверяем, появились ли новые боксы
        if len(boxes) > 0 and (not self.boxes or len(boxes) > len(self.boxes)):
            # Воспроизводим звук уведомления при обнаружении новых объектов
            self.play_notification_sound()
        
        self.boxes = boxes
        self.last_update_time = time.time()
        self.show_boxes = True  # При обновлении показываем боксы
        self.update()  # Вызываем перерисовку
        
    def check_boxes_age(self):
        """
        Проверяет, сколько времени прошло с момента последнего обновления боксов.
        Если прошло больше hide_timeout и нет активных боксов, скрываем их.
        """
        if not self.boxes or not self.last_update_time:
            # Если нет боксов или времени последнего обновления, ничего не делаем
            return
            
        current_time = time.time()
        elapsed_ms = (current_time - self.last_update_time) * 1000
        
        if elapsed_ms > self.hide_timeout:
            if self.show_boxes:
                self.show_boxes = False
                self.update()  # Вызываем перерисовку для скрытия боксов
        
    def paintEvent(self, event):
        """
        Отрисовывает боксы на экране.
        """
        painter = QPainter(self)
        
        # Если флаг показа боксов выключен, не рисуем их
        if not self.show_boxes:
            return
            
        # Устанавливаем кисть для рамок
        frame_color = OVERLAY_SETTINGS["frame_color"]
        pen = QPen(QColor(*frame_color))  # Зеленый цвет
        pen.setWidth(3)  # Толщина линии
        painter.setPen(pen)
        
        # Устанавливаем шрифт для текста
        font = QFont("Arial", 10)
        painter.setFont(font)
        
        # Рисуем все боксы
        for box in self.boxes:
            x1, y1, x2, y2, class_name, conf = box
            
            # Рисуем прямоугольник
            painter.drawRect(QRect(x1, y1, x2 - x1, y2 - y1))
            
            # Добавляем текст с названием класса и уверенностью
            label = f"{class_name} {conf:.2f}"
            
            # Добавляем фон для текста
            text_bg_color = OVERLAY_SETTINGS["text_bg_color"]
            label_rect = QRect(x1, y1 - 25, painter.fontMetrics().width(label) + 10, 20)
            painter.fillRect(label_rect, QColor(*text_bg_color))
            
            # Рисуем текст белым цветом
            text_color = OVERLAY_SETTINGS["text_color"]
            painter.setPen(QColor(*text_color))
            painter.drawText(x1 + 5, y1 - 10, label)
            
            # Возвращаем перо для следующих рамок
            painter.setPen(pen)
            
    def closeEvent(self, event):
        """
        Обрабатывает закрытие оверлея.
        """
        self.hide_timer.stop()
        
        # Останавливаем медиаплеер, если он существует
        if self.sound_player:
            self.sound_player.stop()
            
        self.closed.emit()
        event.accept()
        
    def keyPressEvent(self, event):
        """
        Обрабатывает нажатия клавиш.
        """
        # Закрываем оверлей по нажатию Esc
        if event.key() == Qt.Key_Escape:
            self.close()
        event.accept() 