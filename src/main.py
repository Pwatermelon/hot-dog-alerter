"""Точка входа Hot-Dog Alerter."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt5.QtWidgets import QApplication, QMessageBox

from src.config import APP_NAME, APP_VERSION, MODEL_PATH
from src.gui.app import MainWindow, apply_theme


def main() -> int:
    print(f"{APP_NAME} v{APP_VERSION}")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    apply_theme(app)

    if not os.path.exists(MODEL_PATH):
        QMessageBox.critical(
            None,
            APP_NAME,
            f"Модель не найдена:\n{MODEL_PATH}\n\n"
            "Положите yolov8n.onnx в папку models/ "
            "или выполните: python scripts/export_onnx.py",
        )
        return 1

    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Ошибка: {exc}")
        try:
            input("Нажмите Enter для выхода...")
        except EOFError:
            pass
        raise SystemExit(1)
