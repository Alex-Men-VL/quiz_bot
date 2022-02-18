import argparse
import json
import logging
import os

logger = logging.getLogger(__file__)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Upload questions to the dictionary')
    parser.add_argument('--path', '-p',
                        help='Enter the path to the folder with the questions',
                        type=str,
                        default='quiz-questions')
    return parser.parse_args()


def upload_questions(quiz_folder):
    quiz_questions = {}
    for file_name in os.listdir(quiz_folder):
        file_path = os.path.join(quiz_folder, file_name)
        if os.path.isfile(file_path) and os.path.splitext(file_name)[-1] == '.txt':
            with open(file_path, 'r', encoding='KOI8-R') as quiz_file:
                quizzes = quiz_file.read()
            quizzes = [quiz for quiz in quizzes.split('\n\n\n')]
            for quiz in quizzes:
                quiz_description = quiz.split('\n\n')
                try:
                    quiz_question = list(filter(lambda part: part.startswith('Вопрос'), quiz_description))[0]
                    quiz_question_text = '\n'.join(quiz_question.split('\n')[1:])

                    quiz_answer = list(filter(lambda part: part.startswith('Ответ'), quiz_description))[0]
                    quiz_answer_text = '\n'.join(quiz_answer.split('\n')[1:])

                    quiz_questions[quiz_question_text] = quiz_answer_text
                except IndexError:
                    pass
    if quiz_questions:
        with open('quiz_questions.json', 'w') as json_file:
            json_file.write(json.dumps(
                quiz_questions,
                ensure_ascii=False,
                indent=4,
            ))
        logger.info('The JSON file with the questions is written')
    else:
        logger.error('The JSON file with the questions is not recorded. The folder may be empty.')


def main():
    logging.basicConfig(level=logging.INFO)

    args = parse_arguments()
    quiz_folder = args.path
    if os.path.isdir(quiz_folder):
        upload_questions(quiz_folder)
    else:
        logger.error('The path of the folder with questions is not entered correctly.')


if __name__ == '__main__':
    main()
