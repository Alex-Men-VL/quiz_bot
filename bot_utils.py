import json

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


def get_quiz_questions():
    with open('quiz_questions.json', 'r') as json_file:
        quiz_questions = json_file.read()
    decode_quiz_questions = json.loads(quiz_questions)
    numbered_questions = {}
    for number, question in enumerate(decode_quiz_questions, start=1):
        numbered_questions.update(
            {
                str(number): f'{question}__{decode_quiz_questions[question]}'
            }
        )
    return numbered_questions


def get_current_quiz(user_id):
    question_number = redis_data.hget(user_id, 'question_number')
    quiz = redis_data.hget('questions', question_number)
    quiz_question, quiz_answer = quiz.split('__')
    return quiz_question, quiz_answer
