import serial                                 # работа с COM-портами
import serial.tools.list_ports                # Помогает найти все доступные COM-порты
import time
from shared_state import *


# Функции для работы с Arduino
def update_available_ports():
    """
    Ф-я обновления списка доступных COM-портов на пк.
    """
    global available_ports
    available_ports = [port.device for port in serial.tools.list_ports.comports()] # получение списка доступных COM-портов

    global is_connected, running

def connect_arduino():
    global serial_conn, is_connected, data_flow, running

    if not selected_port: # Если порт не выбран, то подключение невозможно
        return False

    try:
        with serial_lock: # Блокировка для безопасного доступа
            if serial_conn and serial_conn.is_open: # Существует и открыт ли порт?
                serial_conn.close()

            # Создаем соединение с указанным портом и скоростью
            serial_conn = serial.Serial(selected_port, baud_rate, timeout=1)
            time.sleep(2)   # Ожидаем инициализации Arduino (так как на загрузку надо 1-2сек, иначе мотор сойдёт с ума)
            is_connected = True # Подключение есть

            # Создаем фоновый поток для постоянного чтения данных от Arduino
            running = True # Приложение запущено
            data_flow = threading.Thread(target=read_arduino_resp, daemon=True) # Ф-я, которая будет выполняться в потоке/поток завершается при закрытии
            data_flow.start() # Запускаем поток
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
    """
    Ф-я отправки команд arduino
    """
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


def read_arduino_resp():
    """
    Ф-я чтения ответов от Arduino
    """
    global response_buffer, current_angle, is_connected

    while running and is_connected:  # Работаем пока приложение запущено и подключено к Arduino
        try:
            with serial_lock:
                if serial_conn and serial_conn.in_waiting: # Проверяем что буфер не пустой и объект подключения существует
                    # Читаем строку до '/n' и удаляем лишние символы
                    line = serial_conn.readline().decode('utf-8').strip()
                    if line:
                        response_buffer = line
                        # Обрабатываем угол из ответа Arduino
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