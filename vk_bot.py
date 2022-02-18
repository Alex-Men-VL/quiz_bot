import logging
import random

from environs import Env
from telegram import Bot
from vk_api import VkApi
from vk_api.longpoll import VkEventType, VkLongPoll

import static_text
from bot_utils import (
    build_vk_menu,
    check_answer
)
from redis_db import redis_data, update_user_data, save_quiz_questions_in_bd, get_current_quiz
from tg_logs_handler import TelegramLogsHandler

logger = logging.getLogger(__file__)

env = Env()
env.read_env()


def handle_message(event, bot, states_functions):
    user_id = event.user_id
    if not redis_data.exists(user_id, 'state'):
        state = 'START'
        update_user_data(user_id, state=state)
    else:
        state = redis_data.hget(user_id, 'state')

    if event.text == 'Мой счет':
        send_score(event, bot)
        return

    state_handler = states_functions[state]
    next_state = state_handler(event, bot)
    update_user_data(user_id, state=next_state)


def send_start_message(event, bot):
    user_id = event.user_id
    bot.messages.send(
        user_id=user_id,
        message=static_text.vk_start_message,
        keyboard=build_vk_menu(static_text.vk_menu_buttons, n_cols=2),
        random_id=random.randint(1, 1000)
    )
    return 'QUESTION'


def handle_new_question_request(event, bot):
    if event.text != 'Новый вопрос':
        handle_unregistered_message(event, bot)
        return 'QUESTION'

    user_id = event.user_id
    quiz_question, quiz_answer = get_current_quiz(user_id)
    update_user_data(user_id, current_answer=quiz_answer)
    bot.messages.send(
        user_id=user_id,
        message=quiz_question,
        random_id=random.randint(1, 1000)
    )
    return 'ANSWER'


def handle_solution_attempt(event, bot):
    user_id = event.user_id
    answer = event.text
    if answer == 'Сдаться':
        send_quiz_answer(event, bot)
        return 'QUESTION'
    elif answer == 'Новый вопрос':
        handle_unregistered_message(event, bot)
        return 'ANSWER'

    if check_answer(user_id, answer):
        bot.messages.send(
            user_id=user_id,
            message=static_text.correct_answer_message,
            random_id=random.randint(1, 1000)
        )
        update_user_data(user_id, increase_question_number=True, increase_current_score=True)
        return 'QUESTION'
    else:
        bot.messages.send(
            user_id=user_id,
            message=static_text.wrong_answer_message,
            random_id=random.randint(1, 1000)
        )
        return 'ANSWER'


def send_quiz_answer(event, bot):
    user_id = event.user_id
    quiz_answer = redis_data.hget(user_id, 'current_answer')

    message = static_text.quiz_answer_message.format(quiz_answer=quiz_answer)
    bot.messages.send(
        user_id=user_id,
        message=message,
        random_id=random.randint(1, 1000)
    )
    update_user_data(user_id, increase_question_number=True)


def send_score(event, bot):
    user_id = event.user_id
    score = redis_data.hget(user_id, 'current_score')
    answers_number = int(redis_data.hget(user_id, 'question_number')) - 1
    message = static_text.total_score_message.format(score=score, answers_number=answers_number)
    bot.messages.send(
        user_id=user_id,
        message=message,
        random_id=random.randint(1, 1000)
    )


def handle_unregistered_message(event, bot):
    user_id = event.user_id
    bot.messages.send(
        user_id=user_id,
        message=static_text.unregistered_message,
        random_id=random.randint(1, 1000)
    )


def main():
    logging.basicConfig(level=logging.INFO)

    tg_dev_token = env.str('TELEGRAM_DEV_BOT_TOKEN')
    tg_dev_chat_id = env.str('TG_DEV_CHAT_ID')
    vk_token = env.str('VK_BOT_TOKEN')

    dev_bot = Bot(token=tg_dev_token)
    logs_handler = TelegramLogsHandler(dev_bot, tg_dev_chat_id)
    logger.addHandler(logs_handler)
    logger.info('VK bot is running')

    states_functions = {
        'START': send_start_message,
        'QUESTION': handle_new_question_request,
        'ANSWER': handle_solution_attempt,
    }

    if not redis_data.exists('questions'):
        save_quiz_questions_in_bd()

    try:
        vk_session = VkApi(token=vk_token)
        longpoll = VkLongPoll(vk_session)
        bot = vk_session.get_api()

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                handle_message(event, bot, states_functions)
    except Exception as err:
        logger.error(err)


if __name__ == '__main__':
    main()
