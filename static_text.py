from vk_api.keyboard import VkKeyboardColor

tg_start_message = '''Привет, {first_name}! Я бот для викторин.
Нажми «Новый вопрос» для начала викторины.
/cancel - для отмены.
'''
vk_start_message = '''Приветствуем тебя в нашей викторине!
Нажми «Новый вопрос» для начала викторины.'''
correct_answer_message = 'Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос».'
wrong_answer_message = 'Неправильно… Попробуешь ещё раз?'
quiz_answer_message = '''Правильный ответ: {quiz_answer}
Чтобы продолжить, нажми «Новый вопрос».
'''
unregistered_message = '''Я вас не понимаю.
Чтобы получить новый вопрос, нажми «Новый вопрос».
Если вы уже получили новый вопрос, то попробуйте ответить на него или нажми «Сдаться», чтобы узнать правильный ответ.
'''
total_score_message = 'Ваш текущий счет: {score} из {answers_number}'
cancel_message = 'Вы завершили опрос. Чтобы продолжить, нажми «Новый вопрос».'

tg_menu_buttons = [
    'Новый вопрос',
    'Сдаться',
    'Мой счет'
]

vk_menu_buttons = {
    'Новый вопрос': VkKeyboardColor.PRIMARY,
    'Сдаться': VkKeyboardColor.NEGATIVE,
    'Мой счет': VkKeyboardColor.SECONDARY,
}
