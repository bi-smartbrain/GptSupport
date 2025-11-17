from loguru import logger
from notifiers.logging import NotificationHandler
from env_loader import SECRETS_PATH
import os

token = os.getenv("TG_TOKEN")
chat_id_1 = os.getenv("CHAT_ID_1")
chat_id_3 = os.getenv("CHAT_ID_3")

# Параметры для первого чата Андрей
params_chat_1 = {
    "token": token,
    "chat_id": chat_id_1,  # Андрей
}

# Параметры для чата Узкий круг
params_chat_3 = {
    "token": token,
    "chat_id": chat_id_3,  # Узкий круг
}

# Обработчик для чата Андрей с фильтром исключающим SUCCESS
tg_handler_1 = NotificationHandler("telegram", defaults=params_chat_1)

# Обработчик для чата Узкий круг
tg_handler_3 = NotificationHandler("telegram", defaults=params_chat_3)

# Функция-фильтр для исключения SUCCESS сообщений
def filter_success(record):
    return record["level"].name != "SUCCESS"

# Добавляем обработчики к логеру с фильтром для первого чата
logger.add(tg_handler_1, level="DEBUG", filter=filter_success)
logger.add(tg_handler_3, level="SUCCESS")
