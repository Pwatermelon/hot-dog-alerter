"""Прозрачный оверлей поверх экрана."""
from __future__ import annotations

import os
import time

from PyQt5.QtCore import Qt, QRect, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import QPushButton, QWidget

from src.config import OVERLAY_SETTINGS, SOUND_SETTINGS


class DetectionOverlay(QWidget):
    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.boxes = []
        self.last_update_time = None
        self.show_boxes = True
        self.hide_timeout = OVERLAY_SETTINGS["hide_timeout"]
        self.sound_enabled = SOUND_SETTINGS["enabled"]
        self.sound_file = SOUND_SETTINGS["sound_file"]
        self.min_sound_interval = SOUND_SETTINGS["min_interval"]
        self.last_sound_time = 0

        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.check_boxes_age)
        self.hide_timer.start(1000)

        self.sound_player = None
        if self.sound_enabled and os.path.exists(self.sound_file):
            self.sound_player = QMediaPlayer()
            self.sound_player.setMedia(QMediaContent(QUrl.fromLocalFile(self.sound_file)))
            self.sound_player.setVolume(70)

        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        self.close_button = QPushButton("✕", self)
        self.close_button.setFont(QFont("Oswald", 14))
        self.close_button.setStyleSheet(
            "QPushButton {"
            f" background-color: {OVERLAY_SETTINGS['button_color']};"
            " color: white; border: none; border-radius: 16px;"
            " width: 32px; height: 32px; font-weight: 700;"
            "}"
            "QPushButton:hover { background-color: #ff3b3b; }"
        )
        self.close_button.move(20, 20)
        self.close_button.clicked.connect(self.close)

    def enable_sound(self, enabled: bool):
        self.sound_enabled = enabled

    def set_sound_file(self, path: str) -> bool:
        """Подключает файл уведомления (mp3/wav/ogg)."""
        if not path or not os.path.exists(path):
            return False
        self.sound_file = path
        if self.sound_player is None:
            self.sound_player = QMediaPlayer()
            self.sound_player.setVolume(70)
        if self.sound_player.state() == QMediaPlayer.PlayingState:
            self.sound_player.stop()
        self.sound_player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        return True

    def play_notification_sound(self):
        if not self.sound_enabled:
            return
        if self.sound_player is None and self.sound_file and os.path.exists(self.sound_file):
            self.set_sound_file(self.sound_file)
        if not self.sound_player:
            return
        now = int(time.time() * 1000)
        if now - self.last_sound_time < self.min_sound_interval:
            return
        if self.sound_player.state() == QMediaPlayer.PlayingState:
            self.sound_player.stop()
        self.sound_player.play()
        self.last_sound_time = now

    def update_boxes(self, boxes):
        if boxes and (not self.boxes or len(boxes) > len(self.boxes)):
            self.play_notification_sound()
        self.boxes = boxes
        self.last_update_time = time.time()
        self.show_boxes = True
        self.update()

    def check_boxes_age(self):
        if not self.boxes or not self.last_update_time:
            return
        if (time.time() - self.last_update_time) * 1000 > self.hide_timeout:
            if self.show_boxes:
                self.show_boxes = False
                self.update()

    def paintEvent(self, event):
        if not self.show_boxes:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        frame_color = OVERLAY_SETTINGS["frame_color"]
        pen = QPen(QColor(*frame_color), 3)
        painter.setPen(pen)
        painter.setFont(QFont("Oswald", 11, QFont.Bold))

        for box in self.boxes:
            x1, y1, x2, y2, class_name, conf = box
            painter.drawRect(QRect(x1, y1, x2 - x1, y2 - y1))
            label = f"{class_name} {conf:.2f}"
            metrics = painter.fontMetrics()
            label_rect = QRect(x1, max(0, y1 - 26), metrics.width(label) + 12, 22)
            painter.fillRect(label_rect, QColor(*OVERLAY_SETTINGS["text_bg_color"]))
            painter.setPen(QColor(*OVERLAY_SETTINGS["text_color"]))
            painter.drawText(x1 + 6, max(14, y1 - 10), label)
            painter.setPen(pen)

    def closeEvent(self, event):
        self.hide_timer.stop()
        if self.sound_player:
            self.sound_player.stop()
        self.closed.emit()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        event.accept()
