import logging
import random

from environs import Env
from telegram import Bot
from vk_api import VkApi
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll

import bot_message_texts
from bot_utils import (
    check_answer
)
from redis_db import (
    get_current_quiz,
    redis_connection,
    get_current_user
)
from tg_logs_handler import TelegramLogsHandler

logger = logging.getLogger(__file__)


def handle_message(event, bot, states_functions, redis_data):
    user_id = event.user_id
    user = get_current_user(user_id, redis_data, network='vk')
    if not redis_data.hget(user, 'state'):
        state = 'START'
        redis_data.hset(user, 'state', state)
    else:
        state = redis_data.hget(user, 'state')

    if event.text == 'Мой счет':
        send_score(event, bot, user, redis_data)
        return

    state_handler = states_functions[state]
    next_state = state_handler(event, bot, user, redis_data)
    redis_data.hset(user, 'state', next_state)


def build_start_menu(n_cols=2):
    buttons = {
        'Новый вопрос': VkKeyboardColor.PRIMARY,
        'Сдаться': VkKeyboardColor.NEGATIVE,
        'Мой счет': VkKeyboardColor.SECONDARY,
    }

    keyboard = VkKeyboard()

    for number, button in enumerate(buttons, start=1):
        keyboard.add_button(button, color=buttons[button])
        if number % n_cols == 0:
            keyboard.add_line()
    return keyboard.get_keyboard()


def send_start_message(event, bot, user, redis_data):
    user_id = event.user_id
    bot.messages.send(
        user_id=user_id,
        message=bot_message_texts.vk_start_message,
        keyboard=build_start_menu(),
        random_id=random.randint(1, 1000)
    )
    return 'QUESTION'


def handle_new_question_request(event, bot, user, redis_data):
    if event.text != 'Новый вопрос':
        handle_unregistered_message(event, bot)
        return 'QUESTION'

    user_id = event.user_id
    quiz_question, quiz_answer = get_current_quiz(user, redis_data)
    redis_data.hset(user, 'current_answer', quiz_answer)
    bot.messages.send(
        user_id=user_id,
        message=quiz_question,
        random_id=random.randint(1, 1000)
    )
    return 'ANSWER'


def handle_solution_attempt(event, bot, user, redis_data):
    user_id = event.user_id
    answer = event.text
    if answer == 'Сдаться':
        send_quiz_answer(event, bot, user, redis_data)
        return 'QUESTION'
    elif answer == 'Новый вопрос':
        handle_unregistered_message(event, bot)
        return 'ANSWER'

    if check_answer(user, answer, redis_data):
        bot.messages.send(
            user_id=user_id,
            message=bot_message_texts.correct_answer_message,
            random_id=random.randint(1, 1000)
        )
        redis_data.hincrby(user, 'current_score', 1)
        return 'QUESTION'
    else:
        bot.messages.send(
            user_id=user_id,
            message=bot_message_texts.wrong_answer_message,
            random_id=random.randint(1, 1000)
        )
        return 'ANSWER'


def send_quiz_answer(event, bot, user, redis_data):
    user_id = event.user_id
    quiz_answer = redis_data.hget(user, 'current_answer')

    message = bot_message_texts.quiz_answer_message.format(quiz_answer=quiz_answer)
    bot.messages.send(
        user_id=user_id,
        message=message,
        random_id=random.randint(1, 1000)
    )


def send_score(event, bot, user, redis_data):
    user_id = event.user_id
    score = redis_data.hget(user, 'current_score')
    answers_number = int(redis_data.hget(user, 'question_number')) - 1
    message = bot_message_texts.total_score_message.format(score=score, answers_number=answers_number)
    bot.messages.send(
        user_id=user_id,
        message=message,
        random_id=random.randint(1, 1000)
    )


def handle_unregistered_message(event, bot):
    user_id = event.user_id
    bot.messages.send(
        user_id=user_id,
        message=bot_message_texts.unregistered_message,
        random_id=random.randint(1, 1000)
    )


def main():
    env = Env()
    env.read_env()

    logging.basicConfig(level=logging.INFO)

    tg_dev_token = env.str('TELEGRAM_DEV_BOT_TOKEN')
    tg_dev_chat_id = env.str('TG_DEV_CHAT_ID')
    vk_token = env.str('VK_BOT_TOKEN')

    dev_bot = Bot(token=tg_dev_token)
    logs_handler = TelegramLogsHandler(dev_bot, tg_dev_chat_id)
    logger.addHandler(logs_handler)
    logger.info('VK bot is running')

    redis_uri = env.str('REDIS_URL')
    redis_port = env.str('REDIS_PORT')
    redis_password = env.str('REDIS_PASSWORD')

    redis_data = redis_connection(redis_uri, redis_port, redis_password)

    states_functions = {
        'START': send_start_message,
        'QUESTION': handle_new_question_request,
        'ANSWER': handle_solution_attempt,
    }

    try:
        vk_session = VkApi(token=vk_token)
        longpoll = VkLongPoll(vk_session)
        bot = vk_session.get_api()

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                handle_message(event, bot, states_functions, redis_data)
    except Exception as err:
        logger.error(err)


if __name__ == '__main__':
    main()
