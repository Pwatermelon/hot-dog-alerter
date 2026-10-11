"""Главное окно Hot-Dog Alerter."""
from __future__ import annotations

import json
import os
import threading

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.config import (
    APP_NAME,
    APP_VERSION,
    CONFIDENCE_THRESHOLD,
    FONT_DIR,
    ICON_PATH,
    MODEL_PATH,
    OVERLAY_SETTINGS,
    SOUND_SETTINGS,
    STYLESHEET_PATH,
)
from src.detection.yolo_detector import HotDogDetector
from src.utils.overlay import DetectionOverlay
from src.utils.screen_capture import ScreenCapture

LANG_DIR = os.path.join(os.path.dirname(__file__), "lang")


class Translator:
    def __init__(self, lang: str = "ru"):
        self.lang = lang
        self.translations = {}
        self.load_language(lang)

    def load_language(self, lang: str):
        path = os.path.join(LANG_DIR, f"{lang}.json")
        with open(path, "r", encoding="utf-8") as f:
            self.translations = json.load(f)
        self.lang = lang

    def t(self, key: str) -> str:
        return self.translations.get(key, key)


class WorkerSignals(QObject):
    progress = pyqtSignal(float)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)


def load_fonts() -> None:
    if not os.path.isdir(FONT_DIR):
        return
    for name in os.listdir(FONT_DIR):
        if name.lower().endswith((".ttf", ".otf")):
            QFontDatabase.addApplicationFont(os.path.join(FONT_DIR, name))


def apply_theme(app: QApplication) -> None:
    load_fonts()
    app.setFont(QFont("DM Sans", 11))
    if os.path.exists(STYLESHEET_PATH):
        with open(STYLESHEET_PATH, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.translator = Translator("ru")
        self.video_path = None
        self.detector = HotDogDetector(MODEL_PATH, conf=CONFIDENCE_THRESHOLD)
        self.screen_capturer = None
        self.overlay = None
        self.overlay_settings = OVERLAY_SETTINGS.copy()
        self.sound_settings = SOUND_SETTINGS.copy()
        self.video_signals = WorkerSignals()
        self.video_signals.progress.connect(self._on_video_progress)
        self.video_signals.finished.connect(self._on_video_done)
        self.video_signals.failed.connect(self._on_video_fail)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{self.translator.t('app_title')} · v{APP_VERSION}")
        self.setMinimumSize(820, 640)
        self.resize(900, 700)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        root = QWidget()
        root.setObjectName("centralRoot")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(18)

        outer.addLayout(self._build_hero())

        self.tabs = QTabWidget()
        self.video_tab = QWidget()
        self.screen_tab = QWidget()
        self.settings_tab = QWidget()
        self.init_video_tab()
        self.init_screen_tab()
        self.init_settings_tab()
        self.tabs.addTab(self.video_tab, self.translator.t("video_tab"))
        self.tabs.addTab(self.screen_tab, self.translator.t("screen_tab"))
        self.tabs.addTab(self.settings_tab, self.translator.t("settings_tab"))
        outer.addWidget(self.tabs, 1)

    def _build_hero(self) -> QHBoxLayout:
        hero = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(4)

        self.brand = QLabel(APP_NAME.upper())
        self.brand.setObjectName("brandTitle")
        self.brand.setFont(QFont("Oswald", 34, QFont.Bold))

        self.tagline = QLabel(self.translator.t("tagline"))
        self.tagline.setObjectName("brandSubtitle")
        self.tagline.setWordWrap(True)

        left.addWidget(self.brand)
        left.addWidget(self.tagline)
        hero.addLayout(left, 1)

        right = QVBoxLayout()
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_chip = QLabel(self.translator.t("status_ready"))
        self.status_chip.setObjectName("statusChip")
        self.status_chip.setAlignment(Qt.AlignCenter)
        right.addWidget(self.status_chip)
        hero.addLayout(right)
        return hero

    def _section_header(self, title_key: str, hint_key: str) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)
        title = QLabel(self.translator.t(title_key))
        title.setObjectName("sectionTitle")
        title.setFont(QFont("Oswald", 18, QFont.Bold))
        hint = QLabel(self.translator.t(hint_key))
        hint.setObjectName("hintText")
        hint.setWordWrap(True)
        box.addWidget(title)
        box.addWidget(hint)
        setattr(self, f"_title_{title_key}", title)
        setattr(self, f"_hint_{hint_key}", hint)
        return box

    def init_video_tab(self):
        layout = QVBoxLayout(self.video_tab)
        layout.setContentsMargins(8, 20, 8, 8)
        layout.setSpacing(16)
        layout.addLayout(self._section_header("video_section_title", "video_section_hint"))

        self.video_label = QLabel(self.translator.t("no_video_selected"))
        self.video_label.setObjectName("filePill")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumHeight(88)
        layout.addWidget(self.video_label)

        row = QHBoxLayout()
        self.open_btn = QPushButton(self.translator.t("open_video"))
        self.open_btn.setObjectName("secondaryBtn")
        self.open_btn.clicked.connect(self.open_video)
        self.detect_btn = QPushButton(self.translator.t("start_detection"))
        self.detect_btn.setEnabled(False)
        self.detect_btn.clicked.connect(self.start_detection)
        row.addWidget(self.open_btn)
        row.addWidget(self.detect_btn, 1)
        layout.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        layout.addStretch(1)

    def init_screen_tab(self):
        layout = QVBoxLayout(self.screen_tab)
        layout.setContentsMargins(8, 20, 8, 8)
        layout.setSpacing(16)
        layout.addLayout(self._section_header("screen_section_title", "screen_section_hint"))

        fps_row = QHBoxLayout()
        self.fps_caption = QLabel(self.translator.t("fps"))
        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setMinimum(1)
        self.fps_slider.setMaximum(30)
        self.fps_slider.setValue(10)
        self.fps_label = QLabel("10")
        self.fps_slider.valueChanged.connect(lambda v: self.fps_label.setText(str(v)))
        fps_row.addWidget(self.fps_caption)
        fps_row.addWidget(self.fps_slider, 1)
        fps_row.addWidget(self.fps_label)
        layout.addLayout(fps_row)

        checks = QHBoxLayout()
        self.use_overlay_checkbox = QCheckBox(self.translator.t("use_overlay"))
        self.use_overlay_checkbox.setChecked(True)
        self.use_sound_checkbox = QCheckBox(self.translator.t("use_sound"))
        self.use_sound_checkbox.setChecked(self.sound_settings["enabled"])
        checks.addWidget(self.use_overlay_checkbox)
        checks.addWidget(self.use_sound_checkbox)
        checks.addStretch(1)
        layout.addLayout(checks)

        btns = QHBoxLayout()
        self.start_screen_btn = QPushButton(self.translator.t("start_screen_capture"))
        self.start_screen_btn.clicked.connect(self.start_screen_capture)
        self.stop_screen_btn = QPushButton(self.translator.t("stop_screen_capture"))
        self.stop_screen_btn.setObjectName("dangerBtn")
        self.stop_screen_btn.clicked.connect(self.stop_screen_capture)
        self.stop_screen_btn.setEnabled(False)
        btns.addWidget(self.start_screen_btn, 1)
        btns.addWidget(self.stop_screen_btn)
        layout.addLayout(btns)
        layout.addStretch(1)

    def init_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(8, 20, 8, 8)
        layout.setSpacing(14)
        layout.addLayout(self._section_header("settings_section_title", "settings_section_hint"))

        lang_row = QHBoxLayout()
        self.lang_caption = QLabel(self.translator.t("language"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        lang_row.addWidget(self.lang_caption)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch(1)
        layout.addLayout(lang_row)

        conf_row = QHBoxLayout()
        self.conf_caption = QLabel(self.translator.t("confidence"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setMinimum(1)
        self.conf_slider.setMaximum(95)
        self.conf_slider.setValue(int(CONFIDENCE_THRESHOLD * 100))
        self.conf_label = QLabel(f"{CONFIDENCE_THRESHOLD:.2f}")
        self.conf_slider.valueChanged.connect(self.change_confidence)
        conf_row.addWidget(self.conf_caption)
        conf_row.addWidget(self.conf_slider, 1)
        conf_row.addWidget(self.conf_label)
        layout.addLayout(conf_row)

        color_row = QHBoxLayout()
        self.color_caption = QLabel(self.translator.t("frame_color"))
        self.color_btn = QPushButton()
        self.color_btn.setObjectName("colorSwatch")
        self.color_btn.setFixedSize(36, 36)
        self.set_button_color(self.color_btn, QColor(*self.overlay_settings["frame_color"]))
        self.color_btn.clicked.connect(self.select_frame_color)
        color_row.addWidget(self.color_caption)
        color_row.addWidget(self.color_btn)
        color_row.addStretch(1)
        layout.addLayout(color_row)

        hide_row = QHBoxLayout()
        self.hide_caption = QLabel(self.translator.t("hide_timeout"))
        self.hide_slider = QSlider(Qt.Horizontal)
        self.hide_slider.setMinimum(1000)
        self.hide_slider.setMaximum(10000)
        self.hide_slider.setSingleStep(500)
        self.hide_slider.setValue(self.overlay_settings["hide_timeout"])
        self.hide_label = QLabel(
            f"{self.overlay_settings['hide_timeout'] / 1000:.1f} {self.translator.t('seconds')}"
        )
        self.hide_slider.valueChanged.connect(self.change_hide_timeout)
        hide_row.addWidget(self.hide_caption)
        hide_row.addWidget(self.hide_slider, 1)
        hide_row.addWidget(self.hide_label)
        layout.addLayout(hide_row)

        sound_row = QHBoxLayout()
        self.sound_caption = QLabel(self.translator.t("sound_interval"))
        self.sound_slider = QSlider(Qt.Horizontal)
        self.sound_slider.setMinimum(500)
        self.sound_slider.setMaximum(5000)
        self.sound_slider.setSingleStep(500)
        self.sound_slider.setValue(self.sound_settings["min_interval"])
        self.sound_label = QLabel(
            f"{self.sound_settings['min_interval'] / 1000:.1f} {self.translator.t('seconds')}"
        )
        self.sound_slider.valueChanged.connect(self.change_sound_interval)
        sound_row.addWidget(self.sound_caption)
        sound_row.addWidget(self.sound_slider, 1)
        sound_row.addWidget(self.sound_label)
        layout.addLayout(sound_row)

        line = QFrame()
        line.setObjectName("divider")
        layout.addWidget(line)

        self.version_label = QLabel(f"{APP_NAME} v{APP_VERSION}")
        self.version_label.setObjectName("hintText")
        layout.addWidget(self.version_label)
        layout.addStretch(1)

    def set_button_color(self, button, color: QColor):
        button.setStyleSheet(
            f"QPushButton#colorSwatch {{ background-color: rgb({color.red()}, {color.green()}, {color.blue()}); "
            f"border: 2px solid #fff4e0; border-radius: 6px; }}"
        )

    def select_frame_color(self):
        current = QColor(*self.overlay_settings["frame_color"])
        color = QColorDialog.getColor(current, self, self.translator.t("select_frame_color"))
        if color.isValid():
            self.set_button_color(self.color_btn, color)
            self.overlay_settings["frame_color"] = (color.red(), color.green(), color.blue())
            if self.overlay:
                OVERLAY_SETTINGS["frame_color"] = self.overlay_settings["frame_color"]
                self.overlay.update()

    def change_hide_timeout(self, value: int):
        self.overlay_settings["hide_timeout"] = value
        self.hide_label.setText(f"{value / 1000:.1f} {self.translator.t('seconds')}")
        if self.overlay:
            OVERLAY_SETTINGS["hide_timeout"] = value
            self.overlay.hide_timeout = value

    def change_sound_interval(self, value: int):
        self.sound_settings["min_interval"] = value
        self.sound_label.setText(f"{value / 1000:.1f} {self.translator.t('seconds')}")
        if self.overlay:
            SOUND_SETTINGS["min_interval"] = value
            self.overlay.min_sound_interval = value

    def open_video(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            self.translator.t("select_video"),
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)",
        )
        if file_name:
            self.video_path = file_name
            self.video_label.setText(os.path.basename(file_name))
            self.detect_btn.setEnabled(True)
            self.status_chip.setText(self.translator.t("status_video_loaded"))
        else:
            self.video_label.setText(self.translator.t("no_video_selected"))
            self.detect_btn.setEnabled(False)

    def change_language(self):
        self.translator.load_language(self.lang_combo.currentData())
        self.update_ui_texts()

    def change_confidence(self):
        value = self.conf_slider.value() / 100
        self.conf_label.setText(f"{value:.2f}")
        self.detector.conf = value
        if self.screen_capturer and self.screen_capturer.detector:
            self.screen_capturer.detector.conf = value

    def update_ui_texts(self):
        self.setWindowTitle(f"{self.translator.t('app_title')} · v{APP_VERSION}")
        self.tagline.setText(self.translator.t("tagline"))
        if not self.screen_capturer:
            self.status_chip.setText(self.translator.t("status_ready"))

        self.tabs.setTabText(0, self.translator.t("video_tab"))
        self.tabs.setTabText(1, self.translator.t("screen_tab"))
        self.tabs.setTabText(2, self.translator.t("settings_tab"))

        for key in (
            "video_section_title",
            "screen_section_title",
            "settings_section_title",
        ):
            w = getattr(self, f"_title_{key}", None)
            if w:
                w.setText(self.translator.t(key))
        for key in (
            "video_section_hint",
            "screen_section_hint",
            "settings_section_hint",
        ):
            w = getattr(self, f"_hint_{key}", None)
            if w:
                w.setText(self.translator.t(key))

        if self.video_path:
            self.video_label.setText(os.path.basename(self.video_path))
        else:
            self.video_label.setText(self.translator.t("no_video_selected"))
        self.open_btn.setText(self.translator.t("open_video"))
        self.detect_btn.setText(self.translator.t("start_detection"))
        self.fps_caption.setText(self.translator.t("fps"))
        self.use_overlay_checkbox.setText(self.translator.t("use_overlay"))
        self.use_sound_checkbox.setText(self.translator.t("use_sound"))
        self.start_screen_btn.setText(self.translator.t("start_screen_capture"))
        self.stop_screen_btn.setText(self.translator.t("stop_screen_capture"))
        self.lang_caption.setText(self.translator.t("language"))
        self.conf_caption.setText(self.translator.t("confidence"))
        self.color_caption.setText(self.translator.t("frame_color"))
        self.hide_caption.setText(self.translator.t("hide_timeout"))
        self.sound_caption.setText(self.translator.t("sound_interval"))
        self.hide_label.setText(
            f"{self.overlay_settings['hide_timeout'] / 1000:.1f} {self.translator.t('seconds')}"
        )
        self.sound_label.setText(
            f"{self.sound_settings['min_interval'] / 1000:.1f} {self.translator.t('seconds')}"
        )

    def start_detection(self):
        if not self.video_path:
            return
        self.detect_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.status_chip.setText(self.translator.t("detection_in_progress"))
        path = self.video_path

        def job():
            try:
                out = self.detector.detect_on_video(
                    path, progress_callback=lambda p: self.video_signals.progress.emit(p)
                )
                self.video_signals.finished.emit(out)
            except Exception as exc:  # noqa: BLE001
                self.video_signals.failed.emit(str(exc))

        threading.Thread(target=job, daemon=True).start()

    def _on_video_progress(self, value: float):
        self.progress.setValue(int(value * 100))

    def _on_video_done(self, output_path: str):
        self.progress.hide()
        self.detect_btn.setEnabled(True)
        self.open_btn.setEnabled(True)
        self.status_chip.setText(self.translator.t("status_ready"))
        QMessageBox.information(
            self,
            self.translator.t("info"),
            f"{self.translator.t('detection_complete')}\n{self.translator.t('saved_to')}: {output_path}",
        )

    def _on_video_fail(self, message: str):
        self.progress.hide()
        self.detect_btn.setEnabled(True)
        self.open_btn.setEnabled(True)
        self.status_chip.setText(self.translator.t("status_ready"))
        QMessageBox.critical(
            self,
            self.translator.t("error"),
            f"{self.translator.t('detection_error')}: {message}",
        )

    def update_overlay(self, boxes):
        if self.overlay is not None:
            self.overlay.update_boxes(boxes)

    def start_screen_capture(self):
        try:
            use_overlay = self.use_overlay_checkbox.isChecked()
            use_sound = self.use_sound_checkbox.isChecked()
            for key, value in self.overlay_settings.items():
                OVERLAY_SETTINGS[key] = value
            SOUND_SETTINGS["enabled"] = use_sound
            for key, value in self.sound_settings.items():
                SOUND_SETTINGS[key] = value

            if use_overlay:
                if not self.overlay:
                    self.overlay = DetectionOverlay()
                    self.overlay.closed.connect(self.stop_screen_capture)
                self.overlay.enable_sound(use_sound)
                self.overlay.show()
                self.hide()

            fps = self.fps_slider.value()
            self.screen_capturer = ScreenCapture(
                detection_enabled=True,
                overlay_callback=self.update_overlay if use_overlay else None,
            )
            self.screen_capturer.detector.conf = self.detector.conf
            self.start_screen_btn.setEnabled(False)
            self.stop_screen_btn.setEnabled(True)
            self.status_chip.setText(self.translator.t("status_capturing"))

            screenshots_dir = None
            if not use_overlay:
                screenshots_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "screenshots",
                )
                os.makedirs(screenshots_dir, exist_ok=True)
                QMessageBox.information(
                    self,
                    self.translator.t("info"),
                    f"{self.translator.t('screen_capture_started')}\n"
                    f"{self.translator.t('saved_to')}: {screenshots_dir}",
                )

            self.screen_thread = threading.Thread(
                target=self.screen_capturer.start_capture,
                kwargs={"fps": fps, "save_path": screenshots_dir, "use_overlay": use_overlay},
                daemon=True,
            )
            self.screen_thread.start()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                self.translator.t("error"),
                f"{self.translator.t('screen_capture_error')}: {exc}",
            )
            self.stop_screen_capture()

    def stop_screen_capture(self):
        if self.screen_capturer:
            self.screen_capturer.stop_capture()
            self.screen_capturer = None
        if self.overlay:
            self.overlay.close()
            self.overlay = None
            self.show()
        self.start_screen_btn.setEnabled(True)
        self.stop_screen_btn.setEnabled(False)
        self.status_chip.setText(self.translator.t("status_ready"))

    def closeEvent(self, event):
        self.stop_screen_capture()
        event.accept()
