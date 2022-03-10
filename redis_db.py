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


def get_current_user(user_id, redis_data, network):
    user = f'{network}_{user_id}'
    if not redis_data.exists(user):
        mapping = {
            'current_answer': '',
            'current_score': '0'
        }
        if network == 'vk':
            mapping.update({'state': ''})
        redis_data.hset(user, mapping=mapping)
    return user


def get_quiz(redis_data):
    quiz_question = redis_data.randomkey()
    while not quiz_question.startswith('Question:'):
        quiz_question = redis_data.randomkey()
    quiz_answer = redis_data.get(quiz_question)
    quiz_question = quiz_question.replace('Question:', '')
    quiz = {
        'question': quiz_question,
        'answer': quiz_answer
    }
    return quiz
