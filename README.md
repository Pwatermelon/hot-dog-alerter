# Hot-Dog Alerter

<p align="center">
  <img src="assets/icons/app.png" alt="Hot-Dog Alerter" width="120"/>
</p>

<p align="center">
  <a href="https://github.com/Pwatermelon/hot-dog-alerter/releases"><img src="https://img.shields.io/github/v/release/Pwatermelon/hot-dog-alerter?style=flat-square&color=f5c518&label=release" alt="Release"/></a>
  <a href="https://github.com/Pwatermelon/hot-dog-alerter/actions/workflows/release.yml"><img src="https://img.shields.io/github/actions/workflow/status/Pwatermelon/hot-dog-alerter/release.yml?style=flat-square&label=build" alt="Build"/></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square" alt="Python"/>
  <img src="https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-brightgreen?style=flat-square" alt="Platforms"/>
  <img src="https://img.shields.io/badge/inference-OpenCV%20DNN%20%2B%20ONNX-orange?style=flat-square" alt="Inference"/>
</p>

<p align="center"><b>Локальный детектор хот-догов</b> для экрана, видео и камеры Android.<br/>Без облака, без PyTorch в рантайме — компактные бинарники из GitHub Releases.</p>

---

## Что умеет

- Анализ видеофайлов с сохранением размеченного результата
- Захват экрана в реальном времени + прозрачный оверлей
- Звуковой алерт при обнаружении
- RU / EN интерфейс, настройка порога и цвета рамок
- Android APK — детекция через камеру

## Скачать

Готовые сборки появляются в [Releases](https://github.com/Pwatermelon/hot-dog-alerter/releases) после пуша тега `v*`:

| Платформа | Файл |
|-----------|------|
| Windows x64 | `HotDogAlerter-windows-x64.exe` |
| macOS Intel | `HotDogAlerter-macos-x64` |
| macOS Apple Silicon | `HotDogAlerter-macos-arm64` |
| Linux x64 | `HotDogAlerter-linux-x64` |
| Android | `HotDogAlerter-android.apk` |

```bash
# Создать релиз (из корня репозитория)
git tag v1.1.0
git push origin v1.1.0
```

Или вручную: **Actions → Build & Release → Run workflow**.

## Быстрый старт из исходников

```bash
git clone https://github.com/Pwatermelon/hot-dog-alerter.git
cd hot-dog-alerter

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# модель models/yolov8n.onnx уже в репозитории;
# пересобрать: pip install ultralytics onnx && python scripts/export_onnx.py

python src/main.py
```

## Локальная сборка бинарника

```bash
pip install -r requirements-dev.txt
python scripts/build_desktop.py
# → dist/HotDogAlerter[.exe]
```

Сборка **onefile**, без `torch`/`ultralytics` в бандле. Если в системе есть [UPX](https://upx.github.io/), размер дополнительно сжимается.

## Android

Клиент в `android/` (Kivy + OpenCV DNN + та же ONNX-модель). CI собирает debug APK через Buildozer.

Локально (Linux):

```bash
cp models/yolov8n.onnx android/models/
cd android
buildozer android debug
```

## Почему бинарники легче

Раньше рантайм тянул **PyTorch + Ultralytics** (сотни МБ). Сейчас:

1. YOLOv8n экспортирован в **ONNX** (`imgsz=320`)
2. Инференс через **OpenCV DNN**
3. Захват экрана через **mss** вместо pyautogui
4. PyInstaller excludes + опциональный UPX

## Структура

```
hot-dog-alerter/
├── src/                  # десктоп (PyQt5)
├── android/              # APK (Kivy)
├── models/yolov8n.onnx   # компактная модель
├── assets/               # стили, шрифты, иконка
├── scripts/              # export + build
└── .github/workflows/    # CI и релизы
```

Подробности алгоритмов — в [TECHNICAL.md](TECHNICAL.md).

## Требования

- Python 3.10+
- Desktop: Windows 10+, macOS 12+, или современный Linux с X11/Wayland
- Android 7.0+ (arm64)

## Автор

**platinum_watermelon** — [github.com/Pwatermelon](https://github.com/Pwatermelon)

---

Сделано для тех, кто не пропускает ни одного хот-дога.
