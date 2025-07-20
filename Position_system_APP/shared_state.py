import threading

# Глобальные переменные для состояния приложения
serial_conn = None             # Объект последовательного соединения
current_angle = 0.0            # Текущий угол мотора
is_connected = False           # Флаг подключения Arduino
available_ports = []           # Список доступных COM-портов
selected_port = ""             # Выбранный порт
baud_rate = 9600               # Скорость передачи данных
response_buffer = ""           # Буфер для ответов от Arduino
running = True                 # Флаг работы приложения
data_flow = None               # Поток для чтения данных
serial_lock = threading.Lock() # Блокировка для безопасного доступа к порту

# Переменные для GUI
window_GLFW = None   # Окно GLFW
impl = None          # Рендерер ImGui
dark_mode = True     # Темная тема интерфейса
target_angle = 0.0   # Угол установленный пользователем
rotation_delta = 5.0 # Начальный шаг изменения угла