import logging
import os
from dotenv import load_dotenv
from typing import Final, Set, Dict, Any, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
env_path_in_parent = os.path.join(parent_dir, ".env")

if os.path.exists(env_path_in_parent):
    load_dotenv(env_path_in_parent)
    logger.info(f"Loaded .env from: {env_path_in_parent}")
elif os.path.exists(os.path.join(current_dir, ".env")):
    load_dotenv(os.path.join(current_dir, ".env"))
    logger.info(f"Loaded .env from: {current_dir}")
else:
    logger.warning(
        f"Warning: .env file not found. Looked in {parent_dir} and {current_dir}. Create one from .env.example"
    )

VK_TOKEN = os.getenv("VK_TOKEN")

NOTIFICATION_CHAT_ID_RAW = os.getenv("NOTIFICATION_CHAT_ID", "")
NOTIFICATION_CHAT_ID = None
if NOTIFICATION_CHAT_ID_RAW:
    try:
        NOTIFICATION_CHAT_ID = int(NOTIFICATION_CHAT_ID_RAW)
        if NOTIFICATION_CHAT_ID < 2000000000:
            logger.warning(
                f"NOTIFICATION_CHAT_ID ({NOTIFICATION_CHAT_ID}) looks like a user ID, not a chat ID. Chat IDs usually start from 2000000000."
            )
    except ValueError:
        logger.warning(
            f"NOTIFICATION_CHAT_ID in .env is not a valid integer: '{NOTIFICATION_CHAT_ID_RAW}'. Notifications will be disabled."
        )

if not VK_TOKEN:
    logger.error("VK_TOKEN not found in .env file!")
    raise ValueError(
        "VK_TOKEN not found in .env file. Please configure your environment variables."
    )

if not NOTIFICATION_CHAT_ID:
    logger.warning(
        "NOTIFICATION_CHAT_ID is not configured or invalid in .env. Admin notifications will be disabled."
    )

ERROR_GENERIC: Final[str] = "Произошла непредвиденная ошибка. Попробуйте еще раз позже."
ERROR_FIELD_EMPTY: Final[str] = (
    "Поле не может быть пустым. Пожалуйста, укажите значение."
)
ERROR_NAME_TOO_SHORT: Final[str] = "Имя должно содержать минимум 2 символа."
ERROR_INVALID_EMAIL: Final[str] = (
    "Неверный формат электронной почты. Пример: example@mail.ru"
)
ERROR_INVALID_PHONE: Final[str] = (
    "Неверный формат номера телефона. Пожалуйста, укажите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX (минимум 10 цифр)."
)
ERROR_COMPANY_NAME_TOO_SHORT: Final[str] = (
    "Название компании должно содержать минимум 3 символа."
)
ERROR_DESCRIPTION_TOO_SHORT: Final[str] = (
    "Описание должно содержать минимум 10 символов."
)

ERROR_TICKET_NOT_FOUND: Final[str] = "Заявка не найдена или у вас нет доступа к ней."
ERROR_TICKET_CREATION: Final[str] = (
    "Произошла ошибка при создании заявки. Пожалуйста, попробуйте снова или свяжитесь с администратором."
)
ERROR_TICKET_DELETION: Final[str] = (
    "Не удалось удалить заявку. Возможно, она была уже удалена или у вас нет прав на её удаление."
)
ERROR_DELETE_PENDING_NOT_FOUND: Final[str] = (
    "Не найдено заявок, ожидающих удаления. Возможно, вы отменили действие или время ожидания истекло."
)

UNKNOWN_COMMAND_MESSAGE: Final[str] = (
    """Неизвестная команда. Используйте кнопки клавиатуры или введите /start для начала."""
)

NEW_TICKET_NOTIFICATION_TEMPLATE: Final[str] = (
    "🔔 Новая заявка! 🔔\n\nID заявки: {ticket_id}\nОт пользователя: {user_link}\n\n{form_summary}"
)
TICKET_DELETED_NOTIFICATION_TEMPLATE: Final[str] = (
    "🗑️ Заявка удалена пользователем 🗑️\n\nID заявки: {ticket_id}\nПользователь: {user_link}"
)

WELCOME_MESSAGE: Final[str] = (
    "Добро пожаловать! Я могу помочь вам создать заявку на заказ сайта или IT-продукта."
)

FORM_START_MESSAGE: Final[str] = (
    "Отлично! Давайте начнем заполнение формы. Я буду задавать вопросы по одному."
)

CANCEL_MESSAGE: Final[str] = (
    """Заполнение формы отменено. Нажмите \"Заполнить заявку\" в любое время, чтобы начать снова."""
)

FORM_ALL_FIELDS_COMPLETE_MESSAGE: Final[str] = (
    """На все вопросы получены ответы. Нажмите \"Отправить\", чтобы создать заявку."""
)

CONFIRM_DELETE_PHRASES: Final[Set[str]] = {
    "удалить",
    "да",
    "да, удалить",
    "подтвердить",
    "подтверждаю",
    "подтвердить удаление",
}
CANCEL_PHRASES: Final[Set[str]] = {"отмена", "нет", "не удалять", "стоп"}

MAX_TICKET_LIST_BUTTONS: Final[int] = 5

FORM_FIELDS_CONFIG: Final[List[Dict[str, Any]]] = [
    {
        "name": "Ваше имя",
        "validation": {
            "type": "min_length",
            "value": 2,
            "error": ERROR_NAME_TOO_SHORT,
        },
    },
    {
        "name": "Электронная почта",
        "validation": {
            "type": "regex",
            "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$",
            "error": ERROR_INVALID_EMAIL,
        },
    },
    {
        "name": "Номер телефона",
        "validation": {"type": "phone", "error": ERROR_INVALID_PHONE},
    },
    {
        "name": "Название компании",
        "validation": {
            "type": "min_length",
            "value": 3,
            "error": ERROR_COMPANY_NAME_TOO_SHORT,
        },
    },
    {
        "name": "Сайт/CRM-система/Мобильное приложение/Другое",
        "validation": None,
    },
    {
        "name": "Краткое описание",
        "validation": {
            "type": "min_length",
            "value": 10,
            "error": ERROR_DESCRIPTION_TOO_SHORT,
        },
    },
    {
        "name": "Дополнительная информация",
        "validation": None,
    },
]
