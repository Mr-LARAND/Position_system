"""
!!! Работа данного приложения описана ниже:

При запуске инициализируется графический интерфейс (GLFW + ImGui)
Пользователь выбирает COM-порт и нажимает "Connectж
Устанавливается соединение с Arduino и запускается поток для чтения ответов

Пользователь может:
Установить угол (например: 45°)
Делать шаги от установленного угла (например: +12° или -2°)
Сбросить положение в 0°
Программа отображает текущий угол и ответы от Arduino
При закрытии окна соединение корректно закрывается

Особенности реализации:
Многопоточность: Чтение из последовательного порта выполняется в отдельном потоке, чтобы не блокировать интерфейс
Блокировки: Используется serial_lock для безопасного доступа к порту из разных потоков
Темная тема: Интерфейс имеет приятный глазу, темный стиль
Кросс-платформенность: Работает на Windows, Linux и macOS

Требования к микроконтроллеру
На стороне микроконтроллера существует по, которое:
Понимает команды вида "N" (установить угол N°)
Понимает команды вида "+N" (повернуть на +N°) и "-N" (повернуть на -N°)
Отправляет обратно сообщения о текущем угле, например: "Угол установлен: N"
"""





import serial                                    # работа с COM-портами
import serial.tools.list_ports                   # Помогает найти все доступные COM-порты
import threading                                 # Нужен для многопоточности позволяет выполнять несколько задач одновременно
import time
import imgui                                     # для создания простых GUI
import glfw                                      # создаёт окно и обрабатывает ввод для OpenGL
import OpenGL.GL as gl                           # библиотека для 3D-графики
from imgui.integrations.glfw import GlfwRenderer # Позволяет ImGui рисовать интерфейс  в окне, созданном через GLFW.


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
window = None        # Окно GLFW
impl = None          # Рендерер ImGui
dark_mode = True     # Темная тема интерфейса
target_angle = 0.0   # Угол установленный пользователем
rotation_delta = 5.0 # Начальный шаг изменения угла


# Функции для работы с Arduino
def update_available_ports():
    """
    Ф-я обновления списка доступных COM-портов на пк.
    """
    global available_ports
    available_ports = [port.device for port in serial.tools.list_ports.comports()] # получение списка доступных COM-портов

    global is_connected, running

def connect_arduino():
    global serial_conn, is_connected, data_flow, running # глобализируем т.к. будем использовать во многих ф-ях

    if not selected_port: # Если порт не выбран, то подключение невозможно
        return False

    try:
        with serial_lock: # Блокировка для безопасного доступа
            if serial_conn and serial_conn.is_open: # Существует и открыт ли порт?
                serial_conn.close()

            # Создаем соединение с указанным портом и скоростью
            serial_conn = serial.Serial(selected_port, baud_rate, timeout=1)
            time.sleep(2)   # Ожидаем инициализации Arduino (т.к. на загрузку надо 1-2сек, иначе мотор сойдёт с ума)
            is_connected = True # Подключение есть

            # Создаем фоновый поток для постоянного чтения данных от Arduino
            running = True # Приложение запущено
            data_flow = threading.Thread(target=read_Arduino_resp, daemon=True) # Ф-я, которая будет выполняться в потоке/поток завершается при закрытии
            data_flow.start()
            return True
    except Exception as e:
        print(f"Connection error: {e}")
        return False


def disconnect_arduino():
    global is_connected, running

    with serial_lock:
        if serial_conn and serial_conn.is_open:
            serial_conn.close()
        is_connected = False
        running = False # Останавливаем поток чтения
        if data_flow:
            data_flow.join() # Ожидаем завершения потока


def send_command(command):
    global is_connected

    if not is_connected or not serial_conn:
        return False
    try:
        with serial_lock:
            # Отправляем команду с переводом строки
            serial_conn.write(f"{command}\n".encode('utf-8'))
            return True
    except Exception as e:
        print(f"Send error: {e}")
        is_connected = False
        return False


def set_angle(angle):
    """
    Ф-я отправления числового значения угла
    """
    return send_command(str(angle))


def rotate_by(delta):
    """
    Ф-я вращения угла
    """
    prefix = "+" if delta >= 0 else "-" # Определяем направление вращения
    return send_command(f"{prefix}{abs(delta)}") # Отправляем команду "+x" или "-x"


def read_Arduino_resp():
    """
    Ф-я чтения ответов от Arduino
    """
    global response_buffer, current_angle, is_connected

    while running and is_connected:  # Работаем пока приложение запущено и подключено к Arduino
        try:
            with serial_lock:
                if serial_conn and serial_conn.in_waiting:
                    # Читаем строку и удаляем лишние символы
                    line = serial_conn.readline().decode('utf-8').strip()
                    if line:
                        response_buffer = line
                        # Парсим угол из ответа Arduino
                        if "Угол установлен:" in line or "Новый угол:" in line:
                            try:
                                current_angle = float(line.split(":")[1].strip())
                            except (IndexError, ValueError):
                                pass
        except Exception as e:
            print(f"Receive error: {e}")
            is_connected = False
            break
        time.sleep(0.01)  # Небольшая задержка для уменьшения нагрузки на CPU


# Функции для GUI
def init_glfw():
    global window

    if not glfw.init():  # Инициализация GLFW
        return False

    # Создаем окно 800x600 с заголовком
    window = glfw.create_window(800, 600, "Arduino Stepper Controller", None, None)
    if not window:
        glfw.terminate()
        return False

    glfw.make_context_current(window)
    glfw.swap_interval(1)  # Включаем вертикальную синхронизацию
    return True


def init_imgui():
    global impl

    imgui.create_context() # Создаем контекст ImGui
    impl = GlfwRenderer(window) # Создаем рендерер для GLFW

    if dark_mode:
        set_dark_theme() # Устанавливаем темную тему


def set_dark_theme():
    style = imgui.get_style()
    colors = style.colors

    imgui.style_colors_dark() # Базовая темная тема

    # Дополнительные настройки цветов различных элементов интерфейса
    colors[imgui.COLOR_WINDOW_BACKGROUND] = (0.08, 0.08, 0.08, 1.00)
    colors[imgui.COLOR_FRAME_BACKGROUND] = (0.20, 0.20, 0.20, 0.54)
    colors[imgui.COLOR_BUTTON] = (0.31, 0.31, 0.31, 0.54)


def render_gui():
    global selected_port, target_angle, rotation_delta

    imgui.new_frame() # Начинаем новый кадр

    # Устанавливаем главное окно на весь экран
    io = imgui.get_io()
    imgui.set_next_window_size(io.display_size.x, io.display_size.y)
    imgui.set_next_window_position(0, 0)

    # Создаем главное окно без лишних элементов
    imgui.begin("Main",
                flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE |
                      imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_COLLAPSE)

    # Разделитель для лучшей организации
    imgui.text("Connection Settings")
    imgui.separator()

    # Статус подключения
    imgui.text("Status:")
    imgui.same_line()
    if is_connected:
        imgui.text_colored("Connected", 0.0, 1.0, 0.0)
    else:
        imgui.text_colored("Disconnected", 1.0, 0.0, 0.0)

    # Выпадающий список COM-портов
    update_available_ports()
    if imgui.begin_combo("COM Port", selected_port):
        for port in available_ports:
            is_selected = (selected_port == port)
            if imgui.selectable(port, is_selected)[0]:
                selected_port = port
            if is_selected:
                imgui.set_item_default_focus()
        imgui.end_combo()

    imgui.same_line()
    if imgui.button("Refresh Ports"):
        update_available_ports()

    # Кнопки подключения/отключения
    if not is_connected:
        if imgui.button("Connect"):
            connect_arduino()
    else:
        if imgui.button("Disconnect"):
            disconnect_arduino()

    imgui.separator()

    # Отображение текущего угла
    imgui.text(f"Current Angle: {current_angle:.1f}°")

    # Поле ввода целевого угла
    _, target_angle = imgui.input_float("Target Angle", target_angle, step=1.0, step_fast=10.0, format="%.1f")
    if imgui.button("Set Angle"):
        set_angle(target_angle)

    imgui.same_line()
    if imgui.button("Go to 0°"):
        set_angle(0)

    imgui.separator()

    # Относительное вращение
    imgui.text("Relative Rotation:")
    _, rotation_delta = imgui.input_float("Delta Angle", rotation_delta, step=1.0, step_fast=10.0, format="%.1f")

    if imgui.button("Rotate +"):
        rotate_by(rotation_delta)

    imgui.same_line()
    if imgui.button("Rotate -"):
        rotate_by(-rotation_delta)

    imgui.separator()

    # Вывод ответов от Arduino
    imgui.text("Arduino Response:")
    imgui.text(response_buffer)

    imgui.end() # Завершаем окно

    # Рендеринг
    imgui.render()
    gl.glClearColor(0.1, 0.1, 0.1, 1)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    impl.render(imgui.get_draw_data())
    glfw.swap_buffers(window)


def run_app():
    if not init_glfw():
        return

    init_imgui()  # Инициализация ImGui

    # Главный цикл приложения
    while not glfw.window_should_close(window):
        glfw.poll_events()  # Обработка событий
        impl.process_inputs() # Обработка ввода ImGui
        render_gui() # Отрисовка интерфейса

    # Завершение работы
    disconnect_arduino()
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    run_app()