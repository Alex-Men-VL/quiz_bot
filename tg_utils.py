import json

from environs import Env

from redis_db import redis_data

env = Env()
env.read_env()


def check_answer(chat_id, answer):
    current_answer = redis_data.hget(chat_id, 'current_answer').split('.')[0].split('(')[0].strip()
    return answer.lower() in current_answer.lower()


def build_menu(buttons, n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


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


def update_user_data(chat_id, increase_question_number=False, current_answer=None, increase_current_score=False):
    if not redis_data.exists(chat_id):
        redis_data.hset(chat_id,
                        mapping={
                            'question_number': '1',
                            'current_answer': '',
                            'current_score': '0'
                        })
    if increase_question_number:
        redis_data.hincrby(chat_id, 'question_number', 1)
    if increase_current_score:
        redis_data.hincrby(chat_id, 'current_score', 1)
    if current_answer:
        redis_data.hset(chat_id, 'current_answer', current_answer)
