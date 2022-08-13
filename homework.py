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

load_dotenv()


def init_logger() -> logging.Logger:
    """Инициализация логгера."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    return logger


logger = init_logger()


def send_message(bot: Bot, message: str) -> None:
    """Отправка сообщения об изменении статуса проверки."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение {message}')
    except Exception as error:
        logger.error(
            f'Сбой в работе программы: бот не смог отправить сообщение!{error}'
        )


def get_api_answer(current_timestamp: time) -> dict:
    """Запрос на сервер Яндекс практикум."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        logger.info(f'Отправлен запрос {ENDPOINT}')
    except Exception as error:
        logger.error(
            f'Сбой! Сервер не доступен! {error}.'
        )
        raise ServerError(
            f'Сбой! Сервер не доступен! {error}.'
        )
    if homework_statuses.status_code != HTTPStatus.OK:
        logger.error(
            f'Сбой! Код ответа: {homework_statuses.status_code}.!'
        )
        raise HTTPStatusError(
            f'Сбой! Код ответа: {homework_statuses.status_code}.!'
        )
    logger.info('Код ответа на запрос: HTTPStatus.OK')
    try:
        return homework_statuses.json()
    except Exception as error:
        logger.error(
            f'Сбой! Данные получены не в формате json! {error}.'
        )
        raise ServerError(
            f'Сбой! Данные получены не в формате json! {error}.'
        )


def check_response(response: dict) -> list:
    """Проверка ответа Яндекс практикум."""
    if not isinstance(response, dict):
        logger.error(
            'Сбой в работе программы! Ответ передан не в формате dict'
        )
        raise TypeError('Ответ передан не в формате dict')
    if 'homeworks' not in response:
        logger.error(
            'Сбой в работе программы! В словаре отсутвует ключ homeworks'
        )
        raise CheckApiAnswerError('В словаре отсутвует ключ homeworks')
    if 'current_date' not in response:
        logger.error(
            'Сбой в работе программы! В словаре отсутвует ключ current_date'
        )
        raise CheckApiAnswerError('В словаре отсутвует ключ current_date')
    if not isinstance(response['homeworks'], list):
        logger.error(
            'Сбой в работе программы! Домашние работы пришли не в виде списка'
        )
        raise CheckApiAnswerError('Домашние работы пришли не в виде списка')
    if len(response['homeworks']) == 0:
        logger.debug('В ответе отсутствуют новые статусы')
    logger.info('Полученные от сервера данные корректны')
    return response['homeworks']


def parse_status(homework: dict) -> str:
    """Извлечение данных из ответа Яндекс Практикума."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    if homework_status is None:
        logger.error(
            'Сбой в работе программы. Домашней работе не присвоен статус'
        )
        raise ParseError('Домашней работе не присвоен статус')
    if homework_name is None:
        logger.error(
            'Сбой в работе программы. Домашней работе не присвоено название'
        )
        raise KeyError('Домашней работе не присвоено название')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        logger.error(
            f'Сбой в работе программы. {error} '
            'Домашней работе присвоен неизвестный статус'
        )
        raise KeyError(
            f'Домашней работе присвоен неизвестный статус. {error}'
        )


def check_tokens() -> bool:
    """Проверка доступности всех токенов для возможности работы ассистента."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logger.info('Проверка переменных окружения пршла успешно')
        return True
    logger.critical(
        'Сбой в работе программы: переменные окружения недоступны!'
    )
    return False


def main() -> None:
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
