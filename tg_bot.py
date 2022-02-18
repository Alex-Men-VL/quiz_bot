import logging
from enum import Enum

from environs import Env
from telegram import ReplyKeyboardMarkup, Bot
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters, ConversationHandler
)

import static_text
from bot_utils import (
    check_answer,
    build_tg_menu
)
from redis_db import (
    redis_data,
    update_user_data,
    save_quiz_questions_in_bd,
    get_current_quiz
)
from tg_logs_handler import TelegramLogsHandler

env = Env()
env.read_env()

logger = logging.getLogger(__file__)

NETWORK = 'tg'


class Conversation(Enum):
    QUESTION = 1
    ANSWER = 2


def handle_start_message(update, context):
    chat_id = update.message.chat_id
    user = f'{NETWORK}_{chat_id}'
    context.user_data.update(
        {
            'user': user
        }
    )
    update_user_data(user)

    user_first_name = update.effective_user.first_name
    buttons = build_tg_menu(static_text.tg_menu_buttons, n_cols=2)
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    update.message.reply_text(static_text.tg_start_message.format(first_name=user_first_name),
                              reply_markup=reply_markup)

    return Conversation.QUESTION


def handle_cancel_message(update, _):
    update.message.reply_text(static_text.cancel_message)
    return ConversationHandler.END


def handle_new_question_request(update, context):
    user = context.user_data.get('user')

    quiz_question, quiz_answer = get_current_quiz(user)
    update_user_data(user, current_answer=quiz_answer)

    update.message.reply_text(quiz_question)
    return Conversation.ANSWER


def handle_solution_attempt(update, context):
    answer = update.message.text
    user = context.user_data.get('user')
    if check_answer(user, answer):
        update.message.reply_text(static_text.correct_answer_message)
        update_user_data(user, increase_question_number=True, increase_current_score=True)
        return Conversation.QUESTION
    else:
        update.message.reply_text(static_text.wrong_answer_message)


def send_quiz_answer(update, context):
    user = context.user_data.get('user')
    quiz_answer = redis_data.hget(user, 'current_answer')

    message = static_text.quiz_answer_message.format(quiz_answer=quiz_answer)
    update.message.reply_text(message)
    update_user_data(user, increase_question_number=True)
    return Conversation.QUESTION


def send_score(update, context):
    user = context.user_data.get('user')
    score = redis_data.hget(user, 'current_score')
    answers_number = int(redis_data.hget(user, 'question_number')) - 1
    message = static_text.total_score_message.format(score=score, answers_number=answers_number)
    update.message.reply_text(message)


def handle_unregistered_message(update, _):
    update.message.reply_text(static_text.unregistered_message)


def main():
    logging.basicConfig(level=logging.INFO)

    tg_token = env.str('TELEGRAM_BOT_TOKEN')
    tg_dev_token = env.str('TELEGRAM_DEV_BOT_TOKEN')
    tg_dev_chat_id = env.str('TG_DEV_CHAT_ID')

    dev_bot = Bot(token=tg_dev_token)
    logs_handler = TelegramLogsHandler(dev_bot, tg_dev_chat_id)
    logger.addHandler(logs_handler)
    logger.info('Telegram bot is running')

    updater = Updater(token=tg_token, use_context=True)
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', handle_start_message),
            MessageHandler(Filters.regex('^(Новый вопрос)$') & ~Filters.command,
                           handle_new_question_request)
        ],
        states={
            Conversation.QUESTION: [
                MessageHandler(Filters.regex('^(Новый вопрос)$') & ~Filters.command,
                               handle_new_question_request),
                MessageHandler(Filters.text & ~Filters.command & ~Filters.regex('^(Мой счет)$'),
                               handle_unregistered_message)
            ],
            Conversation.ANSWER: [
                MessageHandler(Filters.regex('^(Сдаться)$') & ~Filters.command,
                               send_quiz_answer),
                MessageHandler(Filters.text & ~Filters.command & ~Filters.regex('^(Новый вопрос)$') &
                               ~Filters.regex('^(Мой счет)$'),
                               handle_solution_attempt),
                MessageHandler(Filters.regex('^(Новый вопрос)$'),
                               handle_unregistered_message)

            ],
        },
        fallbacks=[
            CommandHandler('cancel', handle_cancel_message)
        ]
    )
    updater.dispatcher.add_handler(conv_handler)
    updater.dispatcher.add_handler(MessageHandler(Filters.regex('^(Мой счет)$'), send_score))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command & ~Filters.regex('^(Новый вопрос)$'),
                                                  handle_unregistered_message))

    if not redis_data.exists('questions'):
        save_quiz_questions_in_bd()
        logger.info('Questions added to the database')

    try:
        updater.start_polling()
        updater.idle()
    except Exception as err:
        logger.error(err)


if __name__ == '__main__':
    main()
