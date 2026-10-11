#!/usr/bin/env python3
"""Экспорт yolov8n.pt → компактный ONNX для OpenCV DNN."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument(
        "--pt",
        default=os.path.join(ROOT, "models", "yolov8n.pt"),
        help="Путь к .pt весам",
    )
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError:
        print("Установите ultralytics: pip install ultralytics onnx")
        return 1

    if not os.path.exists(args.pt):
        print(f"Не найден {args.pt}")
        print("Скачайте: https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt")
        return 1

    model = YOLO(args.pt)
    out = model.export(format="onnx", imgsz=args.imgsz, simplify=True, opset=12)
    print(f"OK: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
