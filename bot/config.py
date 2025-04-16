import logging
import os
from dotenv import load_dotenv

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

FORM_FIELDS = [
    "Ваше имя",
    "Электронная почта",
    "Номер телефона",
    "Название компании",
    "Сайт/CRM-система/Мобильное приложение/Другое",
    "Краткое описание",
    "Дополнительная информация",
]

WELCOME_MESSAGE = (
    "Добро пожаловать! Я могу помочь вам создать заявку на заказ сайта или IT-продукта."
)

FORM_START_MESSAGE = (
    "Отлично! Давайте начнем заполнение формы. Я буду задавать вопросы по одному."
)

FORM_COMPLETE_MESSAGE = (
    "Спасибо! Ваша заявка создана. Мы свяжемся с вами в ближайшее время."
)

CANCEL_MESSAGE = """Заполнение формы отменено. Нажмите "Заполнить заявку" в любое время, чтобы начать снова."""

FORM_ALL_FIELDS_COMPLETE_MESSAGE = (
    """На все вопросы получены ответы. Нажмите "Отправить", чтобы создать заявку."""
)

ERROR_FIELD_EMPTY = "Поле не может быть пустым. Пожалуйста, укажите значение."
ERROR_NAME_TOO_SHORT = "Имя должно содержать минимум 2 символа."
ERROR_INVALID_EMAIL = "Неверный формат электронной почты. Пример: example@mail.ru"
ERROR_INVALID_PHONE = "Неверный формат номера телефона. Укажите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX"
ERROR_COMPANY_NAME_TOO_SHORT = "Название компании должно содержать минимум 3 символа."
ERROR_DESCRIPTION_TOO_SHORT = "Описание должно содержать минимум 10 символов."

ERROR_TICKET_NOT_FOUND = "Заявка не найдена или у вас нет доступа к ней."
ERROR_TICKET_CREATION = "Произошла ошибка при создании заявки. Пожалуйста, попробуйте снова или свяжитесь с администратором."
ERROR_TICKET_DELETION = "Не удалось удалить заявку. Возможно, она была уже удалена или у вас нет прав на её удаление."
ERROR_DELETE_PENDING_NOT_FOUND = (
    "Не найдено заявок, ожидающих удаления. Возможно, время ожидания истекло."
)

UNKNOWN_COMMAND_MESSAGE = """Неизвестная команда. Используйте кнопки клавиатуры или введите /start для начала."""

NEW_TICKET_NOTIFICATION_TEMPLATE = "🔔 Новая заявка! 🔔\n\nID заявки: {ticket_id}\nОт пользователя: {user_link}\n\n{form_summary}"
TICKET_DELETED_NOTIFICATION_TEMPLATE = "🗑️ Заявка удалена пользователем 🗑️\n\nID заявки: {ticket_id}\nПользователь: {user_link}"
