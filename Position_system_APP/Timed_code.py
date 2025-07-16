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

Особенности реализации
Многопоточность: Чтение из последовательного порта выполняется в отдельном потоке, чтобы не блокировать интерфейс
Блокировки: Используется serial_lock для безопасного доступа к порту из разных потоков
Темная тема: Интерфейс имеет приятный глазу, темный стиль
Кросс-платформенность: Работает на Windows, Linux и macOS

Требования к Arduino
На стороне Arduino существует по, которое:
Понимает команды вида "45" (установить угол 45°)
Понимает команды вида "+5" (повернуть на +5°) и "-10" (повернуть на -10°)
Отправляет обратно сообщения о текущем угле, например: "Угол установлен: 45"
"""





import serial
import serial.tools.list_ports
import threading
import time
import imgui
import glfw
import OpenGL.GL as gl
from imgui.integrations.glfw import GlfwRenderer

# Глобальные переменные
serial_conn = None
current_angle = 0.0
is_connected = False
available_ports = []
selected_port = ""
baud_rate = 9600
response_buffer = ""
running = True
connection_thread = None
serial_lock = threading.Lock()

# Настройки интерфейса
window = None
impl = None
dark_mode = True
target_angle = 0.0
rotation_delta = 5.0


# Функции работы с Arduino
def update_available_ports():
    global available_ports
    available_ports = [port.device for port in serial.tools.list_ports.comports()]


def connect_arduino():
    global serial_conn, is_connected, connection_thread, running
    if not selected_port:
        return False
    try:
        with serial_lock:
            if serial_conn and serial_conn.is_open:
                serial_conn.close()
            serial_conn = serial.Serial(selected_port, baud_rate, timeout=1)
            time.sleep(2)
            is_connected = True
            running = True
            connection_thread = threading.Thread(target=listen_for_responses, daemon=True)
            connection_thread.start()
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
        running = False
        if connection_thread:
            connection_thread.join()


def send_command(command):
    global is_connected
    if not is_connected or not serial_conn:
        return False
    try:
        with serial_lock:
            serial_conn.write(f"{command}\n".encode('utf-8'))
            return True
    except Exception as e:
        print(f"Send error: {e}")
        is_connected = False
        return False


def set_angle(angle):
    return send_command(str(angle))


def rotate_by(delta):
    prefix = "+" if delta >= 0 else "-"
    return send_command(f"{prefix}{abs(delta)}")


def listen_for_responses():
    global response_buffer, current_angle, is_connected
    while running and is_connected:
        try:
            with serial_lock:
                if serial_conn and serial_conn.in_waiting:
                    line = serial_conn.readline().decode('utf-8').strip()
                    if line:
                        response_buffer = line
                        if "Угол установлен:" in line or "Новый угол:" in line:
                            try:
                                current_angle = float(line.split(":")[1].strip())
                            except (IndexError, ValueError):
                                pass
        except Exception as e:
            print(f"Receive error: {e}")
            is_connected = False
            break
        time.sleep(0.01)


# Функции интерфейса
def init_glfw():
    global window
    if not glfw.init():
        return False
    window = glfw.create_window(800, 600, "Arduino Stepper Controller", None, None)
    if not window:
        glfw.terminate()
        return False
    glfw.make_context_current(window)
    glfw.swap_interval(1)
    return True


def init_imgui():
    global impl
    imgui.create_context()
    impl = GlfwRenderer(window)
    if dark_mode:
        set_dark_theme()


def set_dark_theme():
    style = imgui.get_style()
    colors = style.colors
    imgui.style_colors_dark()
    colors[imgui.COLOR_WINDOW_BACKGROUND] = (0.08, 0.08, 0.08, 1.00)
    colors[imgui.COLOR_FRAME_BACKGROUND] = (0.20, 0.20, 0.20, 0.54)
    colors[imgui.COLOR_BUTTON] = (0.31, 0.31, 0.31, 0.54)


def render_gui():
    global selected_port, target_angle, rotation_delta

    imgui.new_frame()

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

    # Выбор порта
    update_available_ports()
    imgui.text("Available COM Ports:")
    if imgui.begin_combo("##ports", selected_port):
        for port in available_ports:
            if imgui.selectable(port)[0]:
                selected_port = port
        imgui.end_combo()

    imgui.same_line()
    if imgui.button("Refresh"):
        update_available_ports()

    # Кнопки подключения
    if not is_connected:
        if imgui.button("Connect", width=100):
            connect_arduino()
    else:
        if imgui.button("Disconnect", width=100):
            disconnect_arduino()

    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # Управление мотором
    imgui.text("Motor Control")
    imgui.separator()

    # Текущий угол
    imgui.text(f"Current Angle: {current_angle:.1f}°")
    imgui.spacing()

    # Абсолютное позиционирование
    imgui.text("Set Absolute Angle:")
    changed, target_angle = imgui.input_float("##target", target_angle, step=1.0, format="%.1f")
    imgui.same_line()
    if imgui.button("Set", width=50):
        set_angle(target_angle)
    imgui.same_line()
    if imgui.button("Zero", width=50):
        set_angle(0)

    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # Относительное вращение
    imgui.text("Relative Rotation:")
    changed, rotation_delta = imgui.input_float("Delta##rotation", rotation_delta, step=1.0, format="%.1f")
    if imgui.button("Rotate +", width=100):
        rotate_by(rotation_delta)
    imgui.same_line()
    if imgui.button("Rotate -", width=100):
        rotate_by(-rotation_delta)

    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # Ответы от Arduino
    imgui.text("Arduino Responses:")
    imgui.text(response_buffer if response_buffer else "No responses yet...")

    imgui.end()

    # Рендеринг
    imgui.render()
    gl.glClearColor(0.1, 0.1, 0.1, 1)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    impl.render(imgui.get_draw_data())
    glfw.swap_buffers(window)


def run_app():
    if not init_glfw():
        return
    init_imgui()
    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()
        render_gui()
    disconnect_arduino()
    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    run_app()