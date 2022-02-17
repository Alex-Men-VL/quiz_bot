import logging
import pprint
from enum import Enum

from telegram import ReplyKeyboardMarkup, Bot
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters, ConversationHandler
)

import static_text
from tg_logs_handler import TelegramLogsHandler
from tg_utils import (
    redis_data,
    env,
    check_answer,
    build_menu,
    get_quiz_questions,
    update_user_data
)

logger = logging.getLogger(__file__)


class Conversation(Enum):
    QUESTION = 1
    ANSWER = 2


def handle_start_message(update, _):
    chat_id = update.message.chat_id
    update_user_data(chat_id)

    user = update.effective_user
    buttons = build_menu(static_text.menu_buttons, n_cols=2)
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    update.message.reply_text(static_text.start_message.format(first_name=user.first_name), reply_markup=reply_markup)

    return Conversation.QUESTION


def handle_cancel_message(update, _):
    update.message.reply_text(static_text.cancel_message)
    return ConversationHandler.END


def handle_new_question_request(update, context):
    chat_id = update.message.chat_id

    question_number = redis_data.hget(chat_id, 'question_number')
    quiz = redis_data.hget('questions', question_number)
    quiz_question, quiz_answer = quiz.split('__')
    update_user_data(chat_id, current_answer=quiz_answer)

    update.message.reply_text(quiz_question)
    return Conversation.ANSWER


def handle_solution_attempt(update, _):
    answer = update.message.text
    chat_id = update.message.chat_id
    if check_answer(chat_id, answer):
        update.message.reply_text(static_text.correct_answer_message)
        update_user_data(chat_id, increase_question_number=True, increase_current_score=True)
        return Conversation.QUESTION
    else:
        update.message.reply_text(static_text.wrong_answer_message)


def send_quiz_answer(update, _):
    chat_id = update.message.chat_id
    quiz_answer = redis_data.hget(chat_id, 'current_answer')

    message = static_text.quiz_answer_message.format(quiz_answer=quiz_answer)
    update.message.reply_text(message)
    update_user_data(chat_id, increase_question_number=True)
    return Conversation.QUESTION


def send_score(update, _):
    chat_id = update.message.chat_id
    score = redis_data.hget(chat_id, 'current_score')
    answers_number = int(redis_data.hget(chat_id, 'question_number')) - 1
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
        quiz_questions = get_quiz_questions()
        redis_data.hset('questions', mapping=quiz_questions)

    try:
        updater.start_polling()
        updater.idle()
    except Exception as err:
        logger.error(err)


if __name__ == '__main__':
    main()
