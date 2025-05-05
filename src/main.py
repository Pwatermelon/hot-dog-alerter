from gui.app import MainWindow
from PyQt5.QtWidgets import QApplication
import sys

def main():
    print("Hot-Dog Alerter запущен. Здесь будет анализ видео и детекция хот-догов.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 