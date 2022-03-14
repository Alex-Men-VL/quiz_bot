import argparse
import logging
import os

from environs import Env

from redis_db import redis_connection

logger = logging.getLogger(__file__)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Upload questions to the dictionary'
    )
    parser.add_argument('--path', '-p',
                        help='Enter the path to the folder with the questions',
                        type=str,
                        default='quiz-questions')
    return parser.parse_args()


def get_formatted_questions(quiz_folder):
    quiz_questions = {}
    for file_name in os.listdir(quiz_folder):
        file_path = os.path.join(quiz_folder, file_name)
        if not (os.path.isfile(file_path) and
                os.path.splitext(file_name)[-1] == '.txt'):
            continue
        with open(file_path, 'r', encoding='KOI8-R') as quiz_file:
            quizzes = quiz_file.read()
        quizzes = [quiz for quiz in quizzes.split('\n\n\n')]
        for quiz in quizzes:
            quiz_description = quiz.split('\n\n')
            try:
                quiz_question = [
                    p for p in quiz_description if p.startswith('Вопрос')
                ][0]
                quiz_question_text = '\n'.join(quiz_question.split('\n')[1:])

                quiz_answer = [
                    p for p in quiz_description if p.startswith('Ответ')
                ][0]
                quiz_answer_text = '\n'.join(quiz_answer.split('\n')[1:])

                quiz_questions[quiz_question_text] = quiz_answer_text
            except IndexError:
                pass
    return quiz_questions


def main():
    env = Env()
    env.read_env()

    logging.basicConfig(level=logging.INFO)

    redis_uri = env.str('REDIS_URL')
    redis_port = env.str('REDIS_PORT')
    redis_password = env.str('REDIS_PASSWORD')

    args = parse_arguments()
    quiz_folder = args.path
    if not os.path.isdir(quiz_folder):
        logger.error(
            'The path of the folder with questions is not entered correctly.'
        )
        return
    quiz_questions = get_formatted_questions(quiz_folder)

    if not quiz_questions:
        logger.error(
            'Questions have not been added. The folder may be empty.'
        )
        return

    redis_data = redis_connection(redis_uri, redis_port, redis_password)
    for question, answer in quiz_questions.items():
        redis_data.hset('questions', key=question, value=answer)
    logger.info('Questions added successfully.')


if __name__ == '__main__':
    main()
