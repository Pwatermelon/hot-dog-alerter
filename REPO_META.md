# Метаданные репозитория GitHub

Скопируй в настройки репозитория: **Settings → General**.

## Description (описание)

```
Локальный детектор хот-догов: экран, видео и Android-камера. YOLOv8 ONNX + OpenCV, без облака.
```

Короткий EN-вариант:

```
Local hot-dog detector for desktop screen/video and Android camera. YOLOv8 ONNX + OpenCV, offline.
```

## Topics (теги)

Добавь через **About → ⚙️ → Topics**:

```
hot-dog
yolov8
object-detection
opencv
onnx
pyqt5
python
screen-capture
android
kivy
computer-vision
desktop-app
github-actions
cross-platform
```

## Website (опционально)

```
https://github.com/Pwatermelon/hot-dog-alerter/releases
```

## Как выпустить релиз

```bash
git add -A
git commit -m "Release-ready: UI, ONNX runtime, CI builds"
git push origin main
git tag v1.1.0
git push origin v1.1.0
```

После пуша тега workflow **Build & Release** соберёт Windows / macOS / Linux / APK и приложит файлы к релизу.
