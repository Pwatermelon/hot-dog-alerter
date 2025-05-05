import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QFileDialog, QVBoxLayout, QWidget, QComboBox, QHBoxLayout
)
from PyQt5.QtCore import Qt
from detection.yolo_detector import HotDogDetector
from config import MODEL_PATH

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
        self.detector = HotDogDetector(MODEL_PATH)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(self.translator.t('app_title'))
        self.setGeometry(100, 100, 500, 200)

        self.label = QLabel(self.translator.t('no_video_selected'))
        self.label.setAlignment(Qt.AlignCenter)

        self.open_btn = QPushButton(self.translator.t('open_video'))
        self.open_btn.clicked.connect(self.open_video)

        self.detect_btn = QPushButton(self.translator.t('start_detection'))
        self.detect_btn.setEnabled(False)
        self.detect_btn.clicked.connect(self.start_detection)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem('Русский', 'ru')
        self.lang_combo.addItem('English', 'en')
        self.lang_combo.currentIndexChanged.connect(self.change_language)

        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(self.translator.t('language')))
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(lang_layout)
        layout.addWidget(self.label)
        layout.addWidget(self.open_btn)
        layout.addWidget(self.detect_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def open_video(self):
        file_name, _ = QFileDialog.getOpenFileName(self, self.translator.t('select_video'), '', 'Video Files (*.mp4 *.avi *.mov)')
        if file_name:
            self.video_path = file_name
            self.label.setText(os.path.basename(file_name))
            self.detect_btn.setEnabled(True)
        else:
            self.label.setText(self.translator.t('no_video_selected'))
            self.detect_btn.setEnabled(False)

    def change_language(self):
        lang = self.lang_combo.currentData()
        self.translator.load_language(lang)
        self.setWindowTitle(self.translator.t('app_title'))
        self.label.setText(self.translator.t('no_video_selected') if not self.video_path else os.path.basename(self.video_path))
        self.open_btn.setText(self.translator.t('open_video'))
        self.detect_btn.setText(self.translator.t('start_detection'))
        self.lang_combo.setItemText(0, 'Русский')
        self.lang_combo.setItemText(1, 'English')

    def start_detection(self):
        if self.video_path:
            self.label.setText(self.translator.t('detection_in_progress'))
            self.detector.detect_on_video(self.video_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 