[app]
title = Hot-Dog Alerter
package.name = hotdogalerter
package.domain = com.pwatermelon
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,onnx,mp3,ttf
source.include_patterns = models/*,sounds/*
version = 1.1.5
requirements = python3,kivy==2.3.0,numpy,opencv,pillow,pyjnius,android,requests
orientation = portrait
fullscreen = 0
android.permissions = CAMERA,INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
p4a.branch = develop
# Локальный фикс libthorvg под NDK lib64/clang
p4a.local_recipes = ./recipes
android.release_artifact = apk
android.skip_update = False

[buildozer]
log_level = 2
warn_on_root = 0
