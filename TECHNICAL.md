# 🔍 Техническое описание Hot-Dog Alerter

## Архитектура приложения

Hot-Dog Alerter построен по модульной архитектуре с четким разделением ответственности между компонентами. Основные модули приложения:

```
hot-dog-alerter/
├── src/
│   ├── main.py                # Точка входа приложения
│   ├── config.py              # Глобальные настройки
│   ├── detection/             # Модули обнаружения объектов
│   ├── gui/                   # Графический интерфейс
│   └── utils/                 # Вспомогательные компоненты
```

## Алгоритмы и технические решения

### 1. Обнаружение хот-догов (YOLOv8)

#### Общий принцип работы

Для обнаружения хот-догов используется **YOLOv8n в формате ONNX** и инференс через **OpenCV DNN** (без PyTorch/Ultralytics в рантайме):

1. **Предварительная обработка**: Входное изображение (кадр видео или скриншот) преобразуется в формат, понятный для YOLOv8.
2. **Инференс модели**: Изображение передается в нейросеть YOLOv8.
3. **Постобработка результатов**: 
   - Фильтрация обнаруженных объектов по классу (оставляем только хот-доги, класс 52 в датасете COCO)
   - Применение порога уверенности (confidence threshold) для исключения ложных срабатываний
   - Формирование списка обнаруженных объектов с координатами и уверенностью

#### Ключевые части кода

Основные операции выполняются в классе `HotDogDetector` (`src/detection/yolo_detector.py`):

```python
class HotDogDetector:
    def __init__(self, model_path, conf=0.5):
        self.model = YOLO(model_path)  # Загрузка модели
        self.conf = conf  # Порог уверенности
        self.classes = CLASSES  # Используемые классы (хот-доги)
        
    def detect_on_image(self, image):
        # Запускаем детекцию с настроенным порогом уверенности
        results = self.model(image, conf=self.conf)
        
        # Фильтрация результатов и формирование списка обнаружений
        detected_objects = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls = int(box.cls[0])
                
                # Проверяем, что это хот-дог (класс 52)
                if cls not in self.classes:
                    continue
                    
                x1, y1, x2, y2 = map(int, box.xyxy[0])  # Координаты прямоугольника
                conf = float(box.conf[0])  # Уверенность
                
                # Добавляем в список детекций
                detected_objects.append((cls, x1, y1, x2, y2, conf))
        
        return detected_objects
```

### 2. Захват экрана и многопоточная обработка

Захват экрана реализован с использованием библиотеки `pyautogui` и оптимизирован с помощью многопоточности для снижения нагрузки на CPU:

#### Алгоритм работы

1. **Основной поток**:
   - Захватывает скриншоты экрана с заданной частотой (FPS)
   - Конвертирует изображение из RGB в BGR (формат OpenCV)
   - Передаёт копию кадра в отдельный поток для обработки

2. **Поток обработки**:
   - Выполняет обнаружение хот-догов с помощью YOLOv8
   - Обновляет список обнаруженных объектов в памяти
   - Вызывает callback-функцию для обновления оверлея при обнаружении

3. **Синхронизация потоков**:
   - Использует `threading.Lock` для безопасного доступа к общим данным
   - Предотвращает обработку нового кадра, пока не завершена обработка предыдущего

#### Ключевые части кода

```python
def start_capture(self, callback=None, fps=10, save_path=None, use_overlay=False):
    # ...
    while self.running:
        start_time = time.time()
        
        # Захватываем кадр
        frame = self.capture_frame()
        
        # Если включена детекция, обрабатываем кадр в отдельном потоке
        if self.detection_enabled:
            if self.detection_thread is None or not self.detection_thread.is_alive():
                self.detection_thread = threading.Thread(
                    target=self.process_frame, 
                    args=(frame.copy(),)
                )
                self.detection_thread.daemon = True
                self.detection_thread.start()
            
            # Используем ранее обнаруженные объекты для оверлея
            with self.processing_lock:
                if self.latest_detections and use_overlay:
                    # ...обновление оверлея...
        
        # Контроль частоты кадров
        process_time = time.time() - start_time
        sleep_time = max(0, delay - process_time)
        if sleep_time > 0:
            time.sleep(sleep_time)
```

### 3. Прозрачный оверлей

Для отображения обнаруженных хот-догов поверх других окон используется прозрачное окно на базе `QWidget` из PyQt5:

#### Особенности реализации

1. **Прозрачное окно**:
   - Использование флагов `Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool`
   - Установка атрибута `Qt.WA_TranslucentBackground` для полной прозрачности фона

2. **Отрисовка рамок**:
   - Использование `QPainter` для отрисовки прямоугольников и текста
   - Настраиваемый цвет и стиль рамок через конфигурацию

3. **Автоматическое скрытие**:
   - Таймер для отслеживания времени с последнего обнаружения
   - Автоматическое скрытие рамок после заданного таймаута

4. **Звуковые уведомления**:
   - Использование `QMediaPlayer` для воспроизведения MP3-звуков
   - Контроль минимального интервала между уведомлениями

#### Ключевой код

```python
class DetectionOverlay(QWidget):
    def __init__(self):
        # ...
        self.boxes = []  # Список боксов [(x1, y1, x2, y2, class_name, conf), ...]
        self.last_update_time = None
        self.hide_timeout = OVERLAY_SETTINGS["hide_timeout"]
        
        # Таймер для скрытия прямоугольников
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.check_boxes_age)
        self.hide_timer.start(1000)  # Проверка каждую секунду
        
        # Медиаплеер для звуков
        self.sound_player = QMediaPlayer()
        # ...
        
    def update_boxes(self, boxes):
        # Воспроизводим звук при новых обнаружениях
        if len(boxes) > 0 and (not self.boxes or len(boxes) > len(self.boxes)):
            self.play_notification_sound()
        
        self.boxes = boxes
        self.last_update_time = time.time()
        self.show_boxes = True
        self.update()  # Вызов перерисовки
        
    def check_boxes_age(self):
        # Скрываем боксы, если прошло больше hide_timeout мс
        if self.last_update_time:
            elapsed_ms = (time.time() - self.last_update_time) * 1000
            if elapsed_ms > self.hide_timeout and self.show_boxes:
                self.show_boxes = False
                self.update()
                
    def paintEvent(self, event):
        # Отрисовка боксов и текста
        # ...
```

### 4. Звуковые уведомления

В приложении реализована система звуковых уведомлений с использованием QMediaPlayer для поддержки MP3-файлов:

#### Алгоритм работы

1. При обнаружении новых хот-догов система проверяет, прошло ли достаточно времени с момента последнего уведомления
2. Если условие выполняется, воспроизводится звуковой файл
3. Обновляется время последнего уведомления

#### Ключевые особенности:

- Минимальный интервал между уведомлениями (настраиваемый)
- Проверка существования звукового файла
- Управление громкостью воспроизведения

```python
def play_notification_sound(self):
    if not self.sound_enabled or not self.sound_player:
        return
    
    current_time = int(time.time() * 1000)  # Текущее время в мс
    if current_time - self.last_sound_time >= self.min_sound_interval:
        # Если плеер уже играет, сначала остановим его
        if self.sound_player.state() == QMediaPlayer.PlayingState:
            self.sound_player.stop()
        
        # Начинаем воспроизведение
        self.sound_player.play()
        self.last_sound_time = current_time
```

## Оптимизация производительности

### 1. Многопоточность

Для предотвращения "подвисаний" интерфейса при обработке видео и захвате экрана, тяжелые вычисления (обнаружение объектов) вынесены в отдельный поток:

```python
self.detection_thread = threading.Thread(
    target=self.process_frame, 
    args=(frame.copy(),)
)
self.detection_thread.daemon = True
self.detection_thread.start()
```

### 2. Контроль частоты кадров

Для снижения нагрузки реализован точный контроль времени между кадрами:

```python
process_time = time.time() - start_time
sleep_time = max(0, delay - process_time)
if sleep_time > 0:
    time.sleep(sleep_time)
```

### 3. Ленивая инициализация ресурсов

Такие ресурсоёмкие объекты, как модель YOLO и медиаплеер, инициализируются только при первой необходимости:

```python
if detection_enabled:
    self.detector = HotDogDetector(MODEL_PATH, conf=CONFIDENCE_THRESHOLD)
```

## Настройки и конфигурация

Все настраиваемые параметры вынесены в модуль конфигурации `config.py`:

```python
# Настройки нейросети
MODEL_PATH = os.path.join("models", "yolov8n.pt")
CONFIDENCE_THRESHOLD = 0.35
NMS_THRESHOLD = 0.4
CLASSES = {52: "hot dog"}

# Настройки оверлея
OVERLAY_SETTINGS = {
    "hide_timeout": 3000,
    "button_color": "rgba(255, 0, 0, 200)",
    "frame_color": (0, 255, 0),
    "text_bg_color": (0, 0, 0, 180),
    "text_color": (255, 255, 255),
}

# Настройки звуковых уведомлений
SOUND_SETTINGS = {
    "enabled": True,
    "sound_file": os.path.join("sounds", "hotdog_alert.mp3"),
    "min_interval": 2000,
}
```

## Интернационализация

Приложение поддерживает многоязычность с использованием JSON-файлов для хранения строк интерфейса. Переводы загружаются динамически при запуске и при смене языка.

```
src/gui/lang/
├── en.json  # Английский
└── ru.json  # Русский
```

Система переводов реализована таким образом, что добавление новых языков не требует изменения кода приложения - достаточно создать новый JSON-файл с переводами.

## Возможности для расширения

Архитектура приложения спроектирована с учетом возможного расширения функциональности:

1. **Поддержка новых объектов** - достаточно добавить новые классы в словарь `CLASSES` в `config.py`
2. **Поддержка других моделей** - архитектура позволяет подключать разные модели обнаружения
3. **Новые источники видео** - благодаря модульной структуре можно добавить поддержку веб-камеры, IP-камер и других источников

## Возможные оптимизации

1. **Переход на ONNX или TensorRT** для ускорения инференса модели
2. **Использование GPU** для обработки видео и детекции
3. **Оптимизация размера захватываемой области** для повышения FPS при скрининге

## Технический долг и ограничения

1. Приложение может значительно нагружать CPU при высоких значениях FPS
2. Есть ограничения на совместимость с некоторыми графическими API при захвате экрана
3. Требуется 4+ ГБ ОЗУ для работы нейросети YOLOv8 