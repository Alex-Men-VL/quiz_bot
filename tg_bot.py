import logging
from enum import Enum

from environs import Env
from telegram import ReplyKeyboardMarkup, Bot
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)

import bot_message_texts
from redis_db import (
    get_quiz,
    redis_connection,
    check_answer,
    handle_new_user
)
from tg_logs_handler import TelegramLogsHandler

logger = logging.getLogger(__file__)


class Conversation(Enum):
    QUESTION = 1
    ANSWER = 2


def get_user(func):
    def wrapper(update, context):
        network = 'tg'
        chat_id = update.message.chat_id
        user = f'{network}_{chat_id}'
        context.user_data['user'] = user
        return func(update, context)
    return wrapper


def handle_start_message(update, context):
    user = context.user_data.get('user')

    redis_data = context.bot_data.get('redis_data')
    if not redis_data.exists(user):
        handle_new_user(user, redis_data)

    user_first_name = update.effective_user.first_name
    buttons = [['Новый вопрос', 'Сдаться'], ['Мой счет']]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    update.message.reply_text(
        bot_message_texts.tg_start_message.format(first_name=user_first_name),
        reply_markup=reply_markup
    )
    return Conversation.QUESTION


def handle_cancel_message(update, context):
    update.message.reply_text(bot_message_texts.cancel_message)
    return ConversationHandler.END


def handle_new_question_request(update, context):
    user = context.user_data.get('user')
    redis_data = context.bot_data.get('redis_data')

    quiz = get_quiz(redis_data)
    redis_data.hset(user, 'current_answer', quiz.get('answer'))

    update.message.reply_text(quiz.get('question'))
    return Conversation.ANSWER


def handle_solution_attempt(update, context):
    user_answer = update.message.text
    user = context.user_data.get('user')
    redis_data = context.bot_data.get('redis_data')

    correct_answer = redis_data.hget(user, 'current_answer')
    if check_answer(user_answer, correct_answer):
        update.message.reply_text(bot_message_texts.correct_answer_message)
        redis_data.hincrby(user, 'current_score', 1)
        redis_data.hincrby(user, 'answers_number', 1)
        return Conversation.QUESTION
    else:
        update.message.reply_text(bot_message_texts.wrong_answer_message)


def handle_question_request_during_answer(update, context):
    message = bot_message_texts.question_request_during_answer_message
    update.message.reply_text(message)
    return Conversation.ANSWER


def send_quiz_answer(update, context):
    user = context.user_data.get('user')
    redis_data = context.bot_data.get('redis_data')
    redis_data.hincrby(user, 'answers_number', 1)

    quiz_answer = redis_data.hget(user, 'current_answer')
    message = bot_message_texts.quiz_answer_message.format(
        quiz_answer=quiz_answer
    )
    update.message.reply_text(message)
    return Conversation.QUESTION


def send_score(update, context):
    user = context.user_data.get('user')
    redis_data = context.bot_data.get('redis_data')

    score = redis_data.hget(user, 'current_score')
    answers_number = redis_data.hget(user, 'answers_number')
    message = bot_message_texts.total_score_message.format(
        score=score,
        answers_number=answers_number
    )
    update.message.reply_text(message)


def handle_unregistered_message(update, context):
    update.message.reply_text(bot_message_texts.unregistered_message)


def main():
    env = Env()
    env.read_env()

    logging.basicConfig(level=logging.INFO)

    tg_token = env.str('TELEGRAM_BOT_TOKEN')
    tg_dev_token = env.str('TELEGRAM_DEV_BOT_TOKEN')
    tg_dev_chat_id = env.str('TG_DEV_CHAT_ID')

    dev_bot = Bot(token=tg_dev_token)
    logs_handler = TelegramLogsHandler(dev_bot, tg_dev_chat_id)
    logger.addHandler(logs_handler)

    redis_uri = env.str('REDIS_URL')
    redis_port = env.str('REDIS_PORT')
    redis_password = env.str('REDIS_PASSWORD')

    redis_data = redis_connection(redis_uri, redis_port, redis_password)

    if not redis_data.exists('questions'):
        logger.error('There are no questions to the quizzes in the database. '
                     'Telegram bot is not running.')
        return
    else:
        logger.info('Telegram bot is running.')

    updater = Updater(token=tg_token, use_context=True)
    updater.dispatcher.bot_data.update({'redis_data': redis_data})

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', get_user(handle_start_message)),
            MessageHandler(Filters.regex('^(Новый вопрос)$')
                           & ~Filters.command,
                           get_user(handle_new_question_request))
        ],
        states={
            Conversation.QUESTION: [
                MessageHandler(Filters.regex('^(Новый вопрос)$')
                               & ~Filters.command,
                               get_user(handle_new_question_request)),
                MessageHandler(Filters.text
                               & ~Filters.command
                               & ~Filters.regex('^(Мой счет)$'),
                               handle_unregistered_message)
            ],
            Conversation.ANSWER: [
                MessageHandler(Filters.regex('^(Сдаться)$')
                               & ~Filters.command,
                               get_user(send_quiz_answer)),
                MessageHandler(Filters.text
                               & ~Filters.command
                               & ~Filters.regex('^(Новый вопрос)$')
                               & ~Filters.regex('^(Мой счет)$'),
                               get_user(handle_solution_attempt)),
                MessageHandler(Filters.regex('^(Новый вопрос)$'),
                               handle_question_request_during_answer)

            ],
        },
        fallbacks=[
            CommandHandler('cancel', handle_cancel_message)
        ]
    )
    updater.dispatcher.add_handler(conv_handler)
    updater.dispatcher.add_handler(
        MessageHandler(Filters.regex('^(Мой счет)$'), get_user(send_score))
    )
    updater.dispatcher.add_handler(
        MessageHandler(Filters.text
                       & ~Filters.command
                       & ~Filters.regex('^(Новый вопрос)$'),
                       handle_unregistered_message)
    )

    try:
        updater.start_polling()
        updater.idle()
    except Exception as err:
        logger.error(err)


if __name__ == '__main__':
    main()
