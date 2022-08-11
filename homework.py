import sys
import os
import logging
import requests
import time

from http import HTTPStatus
from dotenv import load_dotenv
from telegram import Bot

from exceptions import (HTTPStatusError,
                        ServerError,
                        CheckApiAnswerError,
                        ParseError)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения об изменении статуса проверки."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение {message}')
    except Exception as error:
        logger.error(
            f'Сбой в работе программы: бот не смог отправить сообщение!{error}'
        )


def get_api_answer(current_timestamp):
    """Запрос на сервер Яндекс практикум."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    logger.info(f'Отправлен запрос {ENDPOINT}')
    if homework_statuses.status_code == HTTPStatus.OK:
        logger.info('Код ответа на запрос: HTTPStatus.OK')
        return homework_statuses.json()
    elif homework_statuses.status_code:
        logger.error(
            f'Сбой! Код ответа: {homework_statuses.status_code}.!'
        )
        raise HTTPStatusError(
            f'Сбой! Код ответа: {homework_statuses.status_code}.!'
        )
    else:
        logger.error('Сбой в работе программы! Сервер не отвечает!')
        raise ServerError('Сбой в работе программы! Сервер не отвечает!')


def check_response(response):
    """Проверка ответа Яндекс практикум."""
    if not isinstance(response, dict):
        logger.error(
            'Сбой в работе программы! Ответ передан не в формате dict'
        )
        raise TypeError('Ответ передан не в формате dict')
    if 'homeworks' and 'current_date' not in response.keys():
        logger.error(
            'Сбой в работе программы! В ответе отсутсвуют ожидаемые ключи'
        )
        raise CheckApiAnswerError('В ответе отсутсвуют ожидаемые ключи')
    if not isinstance(response['homeworks'], list):
        logger.error(
            'Сбой в работе программы! Домашние работы пришли не в виде списка'
        )
        raise CheckApiAnswerError('Домашние работы пришли не в виде списка')
    logger.info('Полученные от сервера данные корректны')
    return response['homeworks']


def parse_status(homework):
    """Извлечение данных из ответа Яндекс Практикума."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        logger.error(
            'Сбой в работе программы. Домашней работе не присвоен статус'
        )
        raise ParseError('Домашней работе не присвоен статус')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности всех токенов для возможности работы ассистента."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logger.info('Проверка переменных окружения пршла успешно')
        return True
    else:
        logger.critical(
            'Сбой в работе программы: переменные окружения недоступны!'
        )
        return False


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if check_response(response):
                for homework in response['homeworks']:
                    message = parse_status(homework)
                    send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            pass


if __name__ == '__main__':
    main()
