import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QFileDialog, QVBoxLayout, QWidget, QComboBox, QHBoxLayout,
    QTabWidget, QGroupBox, QSlider, QCheckBox, QMessageBox, QColorDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

# Добавляем пути импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.insert(0, src_dir)

# Импорты модулей приложения
from src.detection.yolo_detector import HotDogDetector
from src.utils.screen_capture import ScreenCapture
from src.utils.overlay import DetectionOverlay
from src.config import MODEL_PATH, CONFIDENCE_THRESHOLD, OVERLAY_SETTINGS, SOUND_SETTINGS

LANG_DIR = os.path.join(os.path.dirname(__file__), 'lang')

class Translator:
    def __init__(self, lang='ru'):
        self.lang = lang
        self.translations = {}
        self.load_language(lang)

    def load_language(self, lang):
        path = os.path.join(LANG_DIR, f'{lang}.json')
        with open(path, 'r', encoding='utf-8') as f:
            self.translations = json.load(f)
        self.lang = lang

    def t(self, key):
        return self.translations.get(key, key)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.translator = Translator('ru')
        self.video_path = None
        self.detector = HotDogDetector(MODEL_PATH, conf=CONFIDENCE_THRESHOLD)
        self.screen_capturer = None  # Будет создан при необходимости
        self.overlay = None  # Оверлей для обнаружения
        
        # Копируем настройки оверлея, чтобы не изменять глобальные
        self.overlay_settings = OVERLAY_SETTINGS.copy()
        self.sound_settings = SOUND_SETTINGS.copy()
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(self.translator.t('app_title'))
        self.setGeometry(100, 100, 600, 400)
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        
        # Вкладка видео
        self.video_tab = QWidget()
        self.init_video_tab()
        
        # Вкладка захвата экрана
        self.screen_tab = QWidget()
        self.init_screen_tab()
        
        # Вкладка настроек
        self.settings_tab = QWidget()
        self.init_settings_tab()
        
        # Добавляем вкладки
        self.tabs.addTab(self.video_tab, self.translator.t('video_tab'))
        self.tabs.addTab(self.screen_tab, self.translator.t('screen_tab'))
        self.tabs.addTab(self.settings_tab, self.translator.t('settings_tab'))
        
        # Устанавливаем вкладки как центральный виджет
        self.setCentralWidget(self.tabs)

    def init_video_tab(self):
        layout = QVBoxLayout()
        
        # Виджет для отображения выбранного видео
        self.video_label = QLabel(self.translator.t('no_video_selected'))
        self.video_label.setAlignment(Qt.AlignCenter)
        
        # Кнопки для открытия видео и запуска детекции
        self.open_btn = QPushButton(self.translator.t('open_video'))
        self.open_btn.clicked.connect(self.open_video)
        
        self.detect_btn = QPushButton(self.translator.t('start_detection'))
        self.detect_btn.setEnabled(False)
        self.detect_btn.clicked.connect(self.start_detection)
        
        # Добавляем виджеты на вкладку
        layout.addWidget(self.video_label)
        layout.addWidget(self.open_btn)
        layout.addWidget(self.detect_btn)
        
        self.video_tab.setLayout(layout)
    
    def init_screen_tab(self):
        layout = QVBoxLayout()
        
        # Группа настроек захвата экрана
        self.screen_group = QGroupBox(self.translator.t('screen_capture_settings'))
        screen_layout = QVBoxLayout()
        
        # Выбор частоты кадров
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel(self.translator.t('fps')))
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setMinimum(1)
        self.fps_slider.setMaximum(30)
        self.fps_slider.setValue(10)
        self.fps_label = QLabel("10")
        self.fps_slider.valueChanged.connect(lambda v: self.fps_label.setText(str(v)))
        fps_layout.addWidget(self.fps_slider)
        fps_layout.addWidget(self.fps_label)
        
        # Опция использования оверлея и звуков
        overlay_layout = QHBoxLayout()
        self.use_overlay_checkbox = QCheckBox(self.translator.t('use_overlay'))
        self.use_overlay_checkbox.setChecked(True)  # По умолчанию включен
        overlay_layout.addWidget(self.use_overlay_checkbox)
        
        self.use_sound_checkbox = QCheckBox(self.translator.t('use_sound'))
        self.use_sound_checkbox.setChecked(self.sound_settings["enabled"])
        overlay_layout.addWidget(self.use_sound_checkbox)
        
        # Кнопки запуска и остановки захвата экрана
        self.start_screen_btn = QPushButton(self.translator.t('start_screen_capture'))
        self.start_screen_btn.clicked.connect(self.start_screen_capture)
        
        self.stop_screen_btn = QPushButton(self.translator.t('stop_screen_capture'))
        self.stop_screen_btn.clicked.connect(self.stop_screen_capture)
        self.stop_screen_btn.setEnabled(False)
        
        # Добавляем виджеты в группу
        screen_layout.addLayout(fps_layout)
        screen_layout.addLayout(overlay_layout)
        screen_layout.addWidget(self.start_screen_btn)
        screen_layout.addWidget(self.stop_screen_btn)
        
        self.screen_group.setLayout(screen_layout)
        
        # Добавляем группу на вкладку
        layout.addWidget(self.screen_group)
        layout.addStretch()
        
        self.screen_tab.setLayout(layout)
    
    def init_settings_tab(self):
        layout = QVBoxLayout()
        
        # Настройка языка
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(self.translator.t('language')))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem('Русский', 'ru')
        self.lang_combo.addItem('English', 'en')
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        
        # Настройка порога уверенности
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel(self.translator.t('confidence')))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setMinimum(1)
        self.conf_slider.setMaximum(95)
        self.conf_slider.setValue(int(CONFIDENCE_THRESHOLD * 100))
        self.conf_label = QLabel(f"{CONFIDENCE_THRESHOLD:.2f}")
        self.conf_slider.valueChanged.connect(self.change_confidence)
        conf_layout.addWidget(self.conf_slider)
        conf_layout.addWidget(self.conf_label)
        
        # Настройка цвета рамки
        frame_color_layout = QHBoxLayout()
        frame_color_layout.addWidget(QLabel(self.translator.t('frame_color')))
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 30)
        frame_color = self.overlay_settings["frame_color"]
        color = QColor(*frame_color)
        self.set_button_color(self.color_btn, color)
        self.color_btn.clicked.connect(self.select_frame_color)
        frame_color_layout.addWidget(self.color_btn)
        frame_color_layout.addStretch()
        
        # Настройка времени автоскрытия
        hide_layout = QHBoxLayout()
        hide_layout.addWidget(QLabel(self.translator.t('hide_timeout')))
        self.hide_slider = QSlider(Qt.Horizontal)
        self.hide_slider.setMinimum(1000)
        self.hide_slider.setMaximum(10000)
        self.hide_slider.setSingleStep(1000)
        self.hide_slider.setValue(self.overlay_settings["hide_timeout"])
        self.hide_label = QLabel(f"{self.overlay_settings['hide_timeout'] / 1000:.1f} {self.translator.t('seconds')}")
        self.hide_slider.valueChanged.connect(self.change_hide_timeout)
        hide_layout.addWidget(self.hide_slider)
        hide_layout.addWidget(self.hide_label)
        
        # Настройка звуковых уведомлений
        sound_layout = QHBoxLayout()
        sound_layout.addWidget(QLabel(self.translator.t('sound_interval')))
        self.sound_slider = QSlider(Qt.Horizontal)
        self.sound_slider.setMinimum(500)
        self.sound_slider.setMaximum(5000)
        self.sound_slider.setSingleStep(500)
        self.sound_slider.setValue(self.sound_settings["min_interval"])
        self.sound_label = QLabel(f"{self.sound_settings['min_interval'] / 1000:.1f} {self.translator.t('seconds')}")
        self.sound_slider.valueChanged.connect(self.change_sound_interval)
        sound_layout.addWidget(self.sound_slider)
        sound_layout.addWidget(self.sound_label)
        
        # Добавляем настройки на вкладку
        layout.addLayout(lang_layout)
        layout.addLayout(conf_layout)
        layout.addLayout(frame_color_layout)
        layout.addLayout(hide_layout)
        layout.addLayout(sound_layout)
        layout.addStretch()
        
        self.settings_tab.setLayout(layout)

    def set_button_color(self, button, color):
        """Устанавливает цвет фона кнопки"""
        button.setStyleSheet(
            f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); "
            "border: 1px solid black;"
        )

    def select_frame_color(self):
        """Открывает диалог выбора цвета рамки"""
        current_color = QColor(*self.overlay_settings["frame_color"])
        color = QColorDialog.getColor(current_color, self, self.translator.t('select_frame_color'))
        
        if color.isValid():
            # Обновляем цвет кнопки
            self.set_button_color(self.color_btn, color)
            
            # Обновляем настройки оверлея
            self.overlay_settings["frame_color"] = (color.red(), color.green(), color.blue())
            
            # Если оверлей активен, обновляем его настройки
            if self.overlay:
                OVERLAY_SETTINGS["frame_color"] = self.overlay_settings["frame_color"]
                self.overlay.update()  # Обновляем отображение

    def change_hide_timeout(self, value):
        """Изменяет время автоскрытия рамок"""
        self.overlay_settings["hide_timeout"] = value
        self.hide_label.setText(f"{value / 1000:.1f} {self.translator.t('seconds')}")
        
        # Обновляем глобальные настройки, если оверлей активен
        if self.overlay:
            OVERLAY_SETTINGS["hide_timeout"] = value
            self.overlay.hide_timeout = value
    
    def change_sound_interval(self, value):
        """Изменяет минимальный интервал между звуковыми уведомлениями"""
        self.sound_settings["min_interval"] = value
        self.sound_label.setText(f"{value / 1000:.1f} {self.translator.t('seconds')}")
        
        # Обновляем глобальные настройки, если оверлей активен
        if self.overlay:
            SOUND_SETTINGS["min_interval"] = value
            self.overlay.min_sound_interval = value

    def open_video(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            self.translator.t('select_video'), 
            '', 
            'Video Files (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)'
        )
        if file_name:
            self.video_path = file_name
            self.video_label.setText(os.path.basename(file_name))
            self.detect_btn.setEnabled(True)
        else:
            self.video_label.setText(self.translator.t('no_video_selected'))
            self.detect_btn.setEnabled(False)

    def change_language(self):
        lang = self.lang_combo.currentData()
        self.translator.load_language(lang)
        self.update_ui_texts()

    def change_confidence(self):
        value = self.conf_slider.value() / 100
        self.conf_label.setText(f"{value:.2f}")
        # Обновляем порог уверенности в детекторе
        self.detector.conf = value
        if self.screen_capturer:
            self.screen_capturer.detector.conf = value

    def update_ui_texts(self):
        # Обновляем заголовок окна
        self.setWindowTitle(self.translator.t('app_title'))
        
        # Обновляем тексты вкладок
        self.tabs.setTabText(0, self.translator.t('video_tab'))
        self.tabs.setTabText(1, self.translator.t('screen_tab'))
        self.tabs.setTabText(2, self.translator.t('settings_tab'))
        
        # Обновляем тексты на вкладке видео
        if self.video_path:
            self.video_label.setText(os.path.basename(self.video_path))
        else:
            self.video_label.setText(self.translator.t('no_video_selected'))
        self.open_btn.setText(self.translator.t('open_video'))
        self.detect_btn.setText(self.translator.t('start_detection'))
        
        # Обновляем тексты на вкладке захвата экрана
        self.screen_group.setTitle(self.translator.t('screen_capture_settings'))
        self.use_overlay_checkbox.setText(self.translator.t('use_overlay'))
        self.use_sound_checkbox.setText(self.translator.t('use_sound'))
        self.start_screen_btn.setText(self.translator.t('start_screen_capture'))
        self.stop_screen_btn.setText(self.translator.t('stop_screen_capture'))
        
        # Обновляем тексты на вкладке настроек
        self.lang_combo.setItemText(0, 'Русский')
        self.lang_combo.setItemText(1, 'English')
        
        # Обновляем текст для времени автоскрытия
        self.hide_label.setText(f"{self.overlay_settings['hide_timeout'] / 1000:.1f} {self.translator.t('seconds')}")
        
        # Обновляем текст для интервала звуков
        self.sound_label.setText(f"{self.sound_settings['min_interval'] / 1000:.1f} {self.translator.t('seconds')}")

    def start_detection(self):
        if self.video_path:
            self.video_label.setText(self.translator.t('detection_in_progress'))
            # Отключаем кнопку, чтобы избежать повторного нажатия
            self.detect_btn.setEnabled(False)
            # Запускаем детекцию
            try:
                output_path = self.detector.detect_on_video(self.video_path)
                QMessageBox.information(
                    self,
                    self.translator.t('info'),
                    f"{self.translator.t('detection_complete')}\n{self.translator.t('saved_to')}: {output_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.translator.t('error'),
                    f"{self.translator.t('detection_error')}: {str(e)}"
                )
            # После завершения детекции возвращаем исходное состояние кнопки
            self.detect_btn.setEnabled(True)
            self.video_label.setText(os.path.basename(self.video_path))

    def update_overlay(self, boxes):
        """
        Обновляет оверлей с обнаруженными объектами.
        """
        if self.overlay and boxes is not None:
            self.overlay.update_boxes(boxes)

    def start_screen_capture(self):
        try:
            use_overlay = self.use_overlay_checkbox.isChecked()
            use_sound = self.use_sound_checkbox.isChecked()
            
            # Применяем текущие настройки оверлея к глобальным настройкам
            for key, value in self.overlay_settings.items():
                OVERLAY_SETTINGS[key] = value
                
            # Применяем настройки звука
            SOUND_SETTINGS["enabled"] = use_sound
            for key, value in self.sound_settings.items():
                SOUND_SETTINGS[key] = value
            
            # Создаем оверлей, если нужно
            if use_overlay:
                if not self.overlay:
                    self.overlay = DetectionOverlay()
                    self.overlay.closed.connect(self.stop_screen_capture)
                
                # Устанавливаем состояние звука
                self.overlay.enable_sound(use_sound)
                self.overlay.show()
                
                # Скрываем главное окно
                self.hide()
            
            # Создаем объект захвата экрана
            fps = self.fps_slider.value()
            self.screen_capturer = ScreenCapture(
                detection_enabled=True, 
                overlay_callback=self.update_overlay if use_overlay else None
            )
            self.screen_capturer.detector.conf = self.detector.conf  # Установка того же порога уверенности
            
            # Меняем состояние кнопок
            self.start_screen_btn.setEnabled(False)
            self.stop_screen_btn.setEnabled(True)
            
            # Создаем папку для скриншотов если нужно
            screenshots_dir = None
            if not use_overlay:
                screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")
                if not os.path.exists(screenshots_dir):
                    os.makedirs(screenshots_dir)
                
                # Информируем пользователя
                QMessageBox.information(
                    self,
                    self.translator.t('info'),
                    f"{self.translator.t('screen_capture_started')}\n{self.translator.t('saved_to')}: {screenshots_dir}"
                )
            
            # Запускаем захват в отдельном потоке
            import threading
            self.screen_thread = threading.Thread(
                target=self.screen_capturer.start_capture,
                kwargs={
                    "fps": fps, 
                    "save_path": screenshots_dir,
                    "use_overlay": use_overlay
                }
            )
            self.screen_thread.daemon = True
            self.screen_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, self.translator.t('error'), f"{self.translator.t('screen_capture_error')}: {str(e)}")
            self.stop_screen_capture()

    def stop_screen_capture(self):
        if self.screen_capturer:
            self.screen_capturer.stop_capture()
            self.screen_capturer = None
        
        # Закрываем оверлей, если он открыт
        if self.overlay:
            self.overlay.close()
            self.overlay = None
            # Показываем главное окно снова
            self.show()
        
        # Возвращаем состояние кнопок
        self.start_screen_btn.setEnabled(True)
        self.stop_screen_btn.setEnabled(False)

    def closeEvent(self, event):
        # При закрытии окна останавливаем захват экрана, если он был запущен
        self.stop_screen_capture()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 