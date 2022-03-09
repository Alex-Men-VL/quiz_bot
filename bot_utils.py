from environs import Env

env = Env()
env.read_env()


def check_answer(user, answer, redis_data):
    current_answer = redis_data.hget(user, 'current_answer').split('.')[0].split('(')[0].strip()
    return answer.lower() in current_answer.lower()
