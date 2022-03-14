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


def handle_new_user(user, redis_data):
    mapping = {
        'answers_number': '0',
        'current_answer': '',
        'current_score': '0',
        'state': ''
    }
    redis_data.hset(user, mapping=mapping)


def get_quiz(redis_data):
    quiz_question = redis_data.hrandfield('questions')
    quiz_answer = redis_data.hget('questions', quiz_question)
    quiz = {
        'question': quiz_question,
        'answer': quiz_answer
    }
    return quiz


def check_answer(user_answer, correct_answer):
    formatted_correct_answer = correct_answer.split('.')[0].split('(')[0]
    return user_answer in formatted_correct_answer.strip()
