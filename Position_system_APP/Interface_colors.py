import imgui                      # для создания простых GUI


def set_dark_theme():
    style = imgui.get_style()
    colors = style.colors

    imgui.style_colors_dark() # Базовая темная тема

    # Дополнительные настройки цветов различных элементов интерфейса
    colors[imgui.COLOR_WINDOW_BACKGROUND] = (0.08, 0.08, 0.08, 1.00)
    colors[imgui.COLOR_FRAME_BACKGROUND] = (0.20, 0.20, 0.20, 0.54)
    colors[imgui.COLOR_BUTTON] = (0.4, 0.4, 0.4, 0.9)