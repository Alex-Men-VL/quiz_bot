from environs import Env
from vk_api.keyboard import VkKeyboard

from redis_db import redis_data

env = Env()
env.read_env()


def check_answer(chat_id, answer):
    current_answer = redis_data.hget(chat_id, 'current_answer').split('.')[0].split('(')[0].strip()
    return answer.lower() in current_answer.lower()


def build_tg_menu(buttons, n_cols,
                  header_buttons=None,
                  footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


def build_vk_menu(buttons, n_cols):
    keyboard = VkKeyboard()

    for number, button in enumerate(buttons, start=1):
        keyboard.add_button(button, color=buttons[button])
        if number % n_cols == 0:
            keyboard.add_line()
    return keyboard.get_keyboard()
