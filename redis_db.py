import redis

from environs import Env

env = Env()
env.read_env()


def redis_connection():
    redis_uri = env.str('REDIS_URL')
    redis_port = env.str('REDIS_PORT')
    redis_password = env.str('REDIS_PASSWORD')

    connection = redis.Redis(
        host=redis_uri,
        port=redis_port,
        password=redis_password,
        decode_responses=True,
    )
    if connection.ping():
        return connection
    return None


redis_data = redis_connection()
