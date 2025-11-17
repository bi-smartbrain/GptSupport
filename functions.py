import os
from dotenv import load_dotenv
from closeio_api import Client
import gspread
from gspread.utils import rowcol_to_a1
from env_loader import SECRETS_PATH
import re
import g4f
import json
from datetime import datetime, timedelta


SERVICE_ACCOUNT_FILE = os.path.join(SECRETS_PATH, 'service_account.json')
gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)

api_key = os.getenv('CLOSE_API_KEY_MARY')
api = Client(api_key)


def get_leads_from_smartview(smartview, skip=0):
    """
    Возвращает список лидов из смарта
    :param api: Апи клиент
    :param smartview: название смарта
    :param skip: сколько лидов пропустить (по умолчанию 0)
    :return: список лидов
    """

    params = {
        "query": f'(in:"{smartview}") ',
        "_skip": skip,
        "_limit": 100
    }

    leads = []
    while True:
        resp = api.get('lead', params=params)
        leads.extend(resp['data'])
        if resp['has_more']:
            params['_skip'] += params['_limit']
            print(f'{len(leads)} лидов получено')
        else:
            print(f'Всего {len(leads)} лидов получено')
            return leads


def get_last_incoming_email(lead):
    """
    Возвращает словарь с информацией по последнему входящему письму в лиде
    :param api: апи клиент
    :param lead: лид
    :return: Словарь data с данными о последнем вх.письме
    """
    params = {
        'lead_id': lead['id'],
        '_type': 'Email',

    }

    resp = api.get('activity', params=params)
    activities = resp['data']

    for activity in activities:
        if activity['status'] == 'inbox' and activity['envelope']['is_autoreply'] == False:
            data = activity
            # print(f"Последнее живое входящее письмо для {lead['id']} получено")
            return data
        else:
            continue
    # print(f'Нет живых входящих писем в лиде {lead["id"]}')

    return None


def get_sheet_range(spread, incom_sheet, incom_range):
    """
    Получает из гугл таблицы диапазон
    """

    sh = gc.open(spread)
    data = sh.worksheet(incom_sheet).get(incom_range)
    return data


def add_report_to_sheet(spread, sheet, report):
    """
    Добавляет на лист данные отчета без удаления уже существующих там записей
    :param spread: гугл таблица (название)
    :param sheet: название листа
    :param report: отчет в виде списка списков
    :return: None
    """
    sh = gc.open(spread)
    worksheet = sh.worksheet(sheet)

    # Получить размеры отчета (количество строк и столбцов)
    num_rows = len(report)
    num_cols = len(report[0])

    # Получить диапазон для записи данных
    q_rows = len(worksheet.get_all_values())  # узнаем кол-во уже заполненных на листе строк

    start_cell = rowcol_to_a1(q_rows + 1, 1)
    end_cell = rowcol_to_a1(q_rows + num_rows, num_cols)

    # Записать значения в диапазон
    cell_range = f"{start_cell}:{end_cell}"
    worksheet.update(cell_range, report, value_input_option="user_entered")

    print("Отчет добавлен")

def get_context(email, lenght=100):
    if email:
        text = email['body_text'][:lenght].strip()
        subject = email['subject']
        return f"{subject}\n{text}"
    else:
        return "нет письма"


def parse_api_response(response):
    # Удаляем начальные и конечные пробелы и символы ```json
    cleaned_response = response.strip().strip("```json").strip()

    # Загружаем строку в формате JSON в словарь
    response_dict = json.loads(cleaned_response)

    return response_dict



def hide_numbers(text: str) -> str:
    result = ""
    for char in text:
        if char.isdigit():
            result += "#"
        else:
            result += char
    return result


def hide_emails(text):
    # Регулярное выражение для поиска email-адресов
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    # Функция для замены каждого найденного email на '###@###'
    def replace(match):
        return '###@###'

    # Замена всех email-адресов в тексте
    modified_text = re.sub(email_pattern, replace, text)

    return modified_text


def plus_3_hours(iso_time: str):
    dt_time = datetime.fromisoformat(iso_time)
    dt_time = dt_time + timedelta(hours=3)
    return dt_time.isoformat()


def should_send_notification(last_notification_time, skip_weekends=True, skip_off_hours=True):
    # Проверяем, прошло ли более одного часа
    current_time = datetime.now()
    time_difference = current_time - last_notification_time

    if time_difference < timedelta(hours=1):
        return False

    # Проверяем, является ли текущий день выходным
    if skip_weekends:
        if current_time.weekday() in (5, 6):  # Суббота: 5, Воскресенье: 6
            return False

    # Проверяем, попадает ли текущее время в нерабочие часы
    if skip_off_hours:
        if current_time.hour < 9 or current_time.hour >= 18:
            return False

    return True


def hide_urls(text):
    pattern = r'(?:(?:https?|ftp)://[-a-zA-Z0-9+&@#/%?=~_|!:,.;]*[-a-zA-Z0-9+&@#/%=~_|]|www\.[-a-zA-Z0-9+&@#/%?=~_|!:,.;]*[-a-zA-Z0-9+&@#/%=~_|])\.[a-z]{2,}'
    result = re.sub(pattern, '####.##', text)
    return result


def ask_gpt(prompt: str) -> str:
    try:
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        return response
    except Exception as e:
        return f"Ошибка: {e}"