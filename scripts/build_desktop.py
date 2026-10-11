#!/usr/bin/env python3
"""Сборка оптимизированного десктоп-бинаря через PyInstaller."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")


def app_name() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "HotDogAlerter.exe"
    if system == "darwin":
        return "HotDogAlerter"
    return "HotDogAlerter"


def main() -> int:
    os.chdir(ROOT)
    for path in (DIST, BUILD):
        if os.path.isdir(path):
            shutil.rmtree(path)

    sep = ";" if platform.system() == "Windows" else ":"
    add_data = [
        f"models/yolov8n.onnx{sep}models",
        f"sounds{sep}sounds",
        f"assets{sep}assets",
        f"src/gui/lang{sep}src/gui/lang",
    ]

    # Исключаем тяжёлые/ненужные модули
    excludes = [
        "torch",
        "torchaudio",
        "torchvision",
        "ultralytics",
        "matplotlib",
        "scipy",
        "pandas",
        "sklearn",
        "tensorboard",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "tkinter",
    ]

    icon = os.path.join("assets", "icons", "app.ico")
    if not os.path.exists(icon):
        icon = os.path.join("assets", "icons", "app.png")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name=HotDogAlerter",
        f"--icon={icon}",
        "--paths=.",
        "--hidden-import=PyQt5.QtMultimedia",
        "--collect-submodules=mss",
    ]
    for item in add_data:
        cmd.append(f"--add-data={item}")
    for mod in excludes:
        cmd.append(f"--exclude-module={mod}")

    # UPX сильно уменьшает размер, если установлен
    if shutil.which("upx"):
        cmd.append("--upx-exclude=Qt5*.dll")
        cmd.append("--upx-exclude=*.qml")
    else:
        cmd.append("--noupx")

    cmd.append(os.path.join("src", "main.py"))
    print(" ".join(cmd))
    subprocess.check_call(cmd)

    binary = os.path.join(DIST, app_name())
    if not os.path.exists(binary):
        # macOS onefile всё равно кладёт в dist/HotDogAlerter
        candidates = [
            os.path.join(DIST, "HotDogAlerter"),
            os.path.join(DIST, "HotDogAlerter.exe"),
        ]
        binary = next((c for c in candidates if os.path.exists(c)), binary)

    size_mb = os.path.getsize(binary) / (1024 * 1024) if os.path.exists(binary) else 0
    print(f"Built: {binary} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
