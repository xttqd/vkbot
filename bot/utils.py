import random
# Используем относительный импорт для config, так как он в том же пакете
from . import config

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