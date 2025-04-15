# ========================================================
# КОНФИГУРАЦИЯ БОТА VK
# ========================================================

import os
from dotenv import load_dotenv

# Пытаемся загрузить файл .env из текущей директории или родительской директории
# ВАЖНО: При запуске через 'python -m bot.bot' из родительской папки,
# __file__ будет указывать на bot/config.py, поэтому нужно искать .env
# относительно этой директории или в родительской.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
env_path_in_parent = os.path.join(parent_dir, '.env')

if os.path.exists(env_path_in_parent):
    load_dotenv(env_path_in_parent)
    print(f"Loaded .env from: {env_path_in_parent}")
elif os.path.exists(os.path.join(current_dir, '.env')): # Менее вероятно при запуске через -m
    load_dotenv(os.path.join(current_dir, '.env'))
    print(f"Loaded .env from: {current_dir}")
else:
    print(f"Warning: .env file not found. Looked in {parent_dir} and {current_dir}. Create one from .env.example")

# Токен VK API для доступа к API ВКонтакте
# Используется для авторизации бота и отправки/получения сообщений
# Получить токен можно на https://vk.com/dev/bots_docs
# Хранится в .env файле в формате: VK_TOKEN=your_token_here
VK_TOKEN = os.getenv("VK_TOKEN")

# ID администраторов/менеджеров для отправки уведомлений о новых заявках
# Указываются через запятую в .env файле: ADMIN_IDS=12345,67890
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if ADMIN_IDS_RAW:
    try:
        ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_RAW.split(',') if admin_id.strip()]
    except ValueError:
        print(f"Warning: ADMIN_IDS in .env contains non-integer values: '{ADMIN_IDS_RAW}'. Notifications might not work.")

# Шаблон сообщения для уведомления администраторов о новой заявке
# Можно использовать плейсхолдеры: {ticket_id}, {user_id}, {user_link}, {field_name} (для полей формы)
NEW_TICKET_NOTIFICATION_TEMPLATE = os.getenv(
    "NEW_TICKET_NOTIFICATION_TEMPLATE",
    "🔔 Новая заявка! 🔔\n\nID заявки: {ticket_id}\nОт пользователя: {user_link}\n\n{form_summary}"
)

# Шаблон сообщения для уведомления администраторов об удалении заявки
# Плейсхолдеры: {ticket_id}, {user_id}, {user_link}
TICKET_DELETED_NOTIFICATION_TEMPLATE = os.getenv(
    "TICKET_DELETED_NOTIFICATION_TEMPLATE",
    "🗑️ Заявка удалена пользователем 🗑️\n\nID заявки: {ticket_id}\nПользователь: {user_link}"
)

# Проверка наличия токена
if not VK_TOKEN:
    raise ValueError("VK_TOKEN not found in .env file. Please configure your environment variables.")

# Проверка наличия админов, если шаблон используется
if not ADMIN_IDS and "ADMIN_IDS" in os.environ: # Проверяем, была ли переменная вообще в .env
     print("Warning: ADMIN_IDS is configured in .env but is empty or invalid. Admin notifications will be disabled.")
elif not ADMIN_IDS:
    print("Info: ADMIN_IDS is not configured in .env. Admin notifications will be disabled.")

# ========================================================
# НАСТРОЙКА ФОРМЫ ЗАЯВКИ
# ========================================================

# Список полей, которые будут запрашиваться у пользователя при заполнении формы
# Порядок полей в списке определяет порядок вопросов при заполнении
FORM_FIELDS = [
    "Ваше имя",                                     # Имя контактного лица
    "Электронная почта",                            # Email для связи
    "Номер телефона",                               # Телефон для связи
    "Название компании",                            # Название организации клиента
    "Сайт/CRM-система/Мобильное приложение/Другое", # Тип проекта
    "Краткое описание",                             # Описание проекта
    "Дополнительная информация"                     # Дополнительные требования или пожелания
]

# ========================================================
# ТЕКСТОВЫЕ СООБЩЕНИЯ БОТА
# ========================================================

# Приветственное сообщение при первом контакте с ботом
WELCOME_MESSAGE = "Добро пожаловать! Я могу помочь вам создать заявку на заказ сайта или IT-продукта."

# Сообщение при начале заполнения формы
FORM_START_MESSAGE = "Отлично! Давайте начнем заполнение формы. Я буду задавать вопросы по одному."

# Сообщение при успешном завершении заполнения формы и создании заявки
FORM_COMPLETE_MESSAGE = "Спасибо! Ваша заявка создана. Мы свяжемся с вами в ближайшее время."

# Сообщение при отмене заполнения формы
CANCEL_MESSAGE = """Заполнение формы отменено. Нажмите "Заполнить заявку" в любое время, чтобы начать снова.""" 