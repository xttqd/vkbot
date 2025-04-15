from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from . import config
from .form_handler import FormHandler
from .db_handler import DatabaseHandler
import random
from .handlers import BotHandlers

# ========================================================
# ИНИЦИАЛИЗАЦИЯ БОТА И ОБРАБОТЧИКОВ
# ========================================================

# Инициализация бота с токеном из конфигурационного файла
bot = Bot(token=config.VK_TOKEN)

# Инициализация обработчика формы и базы данных
form_handler = FormHandler(config.FORM_FIELDS)
db_handler = DatabaseHandler()

# Инициализация обработчиков команд
bot_handlers = BotHandlers(bot, form_handler, db_handler)

# ========================================================
# ФУНКЦИИ ДЛЯ СОЗДАНИЯ КЛАВИАТУР
# ========================================================

def get_start_keyboard():
    """
    Создает стартовую клавиатуру с кнопками для начала заполнения формы и просмотра заявок
    """
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("Заполнить заявку"), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("Мои заявки"), color=KeyboardButtonColor.SECONDARY)
    return keyboard

def get_form_keyboard():
    """
    Создает клавиатуру для процесса заполнения формы с кнопкой отмены
    """
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("Отмена"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard

def get_submit_keyboard():
    """
    Создает клавиатуру для отправки заполненной формы с кнопками отправки и отмены
    """
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("Отправить"), color=KeyboardButtonColor.POSITIVE)
    keyboard.add(Text("Отмена"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard

def get_ticket_detail_keyboard(ticket_id: str):
    """
    Создает клавиатуру для просмотра деталей заявки с кнопками возврата и удаления
    
    Args:
        ticket_id: Идентификатор заявки для передачи в команду удаления
    """
    print(f"Создаем клавиатуру для заявки: {ticket_id}")
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("Мои заявки"), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("Удалить заявку"), color=KeyboardButtonColor.NEGATIVE)
    keyboard.row()
    keyboard.add(Text("Заполнить заявку"), color=KeyboardButtonColor.PRIMARY)
    return keyboard

# ========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАЗРАБОТКИ
# ========================================================

def generate_random_form_data():
    """
    Генерирует случайные данные для заполнения формы при тестировании
    """
    # Генерация случайного имени
    names = ["Иван", "Петр", "Алексей", "Ольга", "Мария", "Елена", "Андрей"]
    random_name = random.choice(names)
    
    # Генерация случайного email
    domains = ["mail.ru", "gmail.com", "yandex.ru", "example.com"]
    random_email = f"{random_name.lower()}{random.randint(1, 999)}@{random.choice(domains)}"
    
    # Генерация случайного телефона
    random_phone = f"+7{random.randint(9000000000, 9999999999)}"
    
    # Генерация случайного названия компании
    company_prefixes = ["ООО", "АО", "ИП", "ПАО"]
    company_names = ["Техноцентр", "Инфосистемы", "Датацентр", "Прогресс", "Мегасофт"]
    random_company = f"{random.choice(company_prefixes)} {random.choice(company_names)}"
    
    # Выбор случайного типа проекта
    project_types = ["Сайт", "CRM-система", "Мобильное приложение", "Корпоративный портал"]
    random_project_type = random.choice(project_types)
    
    # Генерация случайного описания
    descriptions = [
        "Нужен современный адаптивный сайт для нашей компании.",
        "Требуется система учета клиентов с интеграцией с 1С.",
        "Ищем разработчиков для создания мобильного приложения.",
        "Необходимо разработать корпоративный портал с авторизацией."
    ]
    random_description = random.choice(descriptions)
    
    # Создаем словарь с данными формы
    form_data = {
        config.FORM_FIELDS[0]: random_name,                  # Имя
        config.FORM_FIELDS[1]: random_email,                 # Email
        config.FORM_FIELDS[2]: random_phone,                 # Телефон
        config.FORM_FIELDS[3]: random_company,               # Название компании
        config.FORM_FIELDS[4]: random_project_type,          # Тип проекта
        config.FORM_FIELDS[5]: random_description,           # Описание
        config.FORM_FIELDS[6]: "Тестовая заявка. Автоматически сгенерирована." # Дополнительная информация
    }
    
    return form_data

# ========================================================
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ========================================================

bot_handlers.register_handlers()

# ========================================================
# ЗАПУСК БОТА
# ========================================================

if __name__ == "__main__":
    print("Bot is starting...")
    bot.run_forever()