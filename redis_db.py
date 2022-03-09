import json

import redis


def redis_connection(redis_uri, redis_port, redis_password):
    connection = redis.Redis(
        host=redis_uri,
        port=redis_port,
        password=redis_password,
        decode_responses=True,
    )
    if connection.ping():
        return connection


def save_quiz_questions_in_bd(redis_data):
    with open('quiz_questions.json', 'r') as json_file:
        quiz_questions = json_file.read()
    decode_quiz_questions = json.loads(quiz_questions)
    for number, question in enumerate(decode_quiz_questions, start=1):
        mapping = {
            'question': question,
            'answer': decode_quiz_questions[question]
        }
        redis_data.hset(f'question_{number}', mapping=mapping)
    redis_data.set('questions', 'True')


def update_user_data(user, redis_data, increase_question_number=False,
                     current_answer=None, increase_current_score=False,
                     state=None):
    if not redis_data.exists(user):
        mapping = {
            'question_number': '1',
            'current_answer': '',
            'current_score': '0'
        }
        if state:
            mapping.update({'state': state})  # If the user uses a VK bot

        redis_data.hset(user, mapping=mapping)
        return

    if increase_question_number:
        redis_data.hincrby(user, 'question_number', 1)
    if increase_current_score:
        redis_data.hincrby(user, 'current_score', 1)
    if current_answer:
        redis_data.hset(user, 'current_answer', current_answer)
    if state:
        redis_data.hset(user, 'state', state)


def get_current_quiz(user, redis_data):
    question_number = redis_data.hget(user, 'question_number')
    quiz_question = redis_data.hget(f'question_{question_number}', 'question')
    quiz_answer = redis_data.hget(f'question_{question_number}', 'answer')
    return quiz_question, quiz_answer
