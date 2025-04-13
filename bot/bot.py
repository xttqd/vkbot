from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
import config
from form_handler import FormHandler
from db_handler import DatabaseHandler
import random

# ========================================================
# ИНИЦИАЛИЗАЦИЯ БОТА И ОБРАБОТЧИКОВ
# ========================================================

# Инициализация бота с токеном из конфигурационного файла
bot = Bot(token=config.VK_TOKEN)

# Инициализация обработчика формы с полями из конфигурации и обработчика базы данных
form_handler = FormHandler(config.FORM_FIELDS)
db_handler = DatabaseHandler()

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
# ОБРАБОТЧИКИ КОМАНД
# ========================================================

@bot.on.message(text=["Начать"])
async def start_handler(message: Message):
    """
    Обработчик стартовых команд, отправляет приветственное сообщение и стартовую клавиатуру
    """
    await message.answer(
        config.WELCOME_MESSAGE,
        keyboard=get_start_keyboard()
    )

@bot.on.message(text=["Заполнить заявку"])
async def form_start_handler(message: Message):
    """
    Обработчик команды начала заполнения формы
    Проверяет, не заполняет ли пользователь уже форму, чтобы избежать сброса прогресса
    """
    user_id = message.from_id
    
    # Проверяем, не заполняет ли пользователь уже форму
    if user_id in form_handler.user_forms:
        # Если пользователь уже заполняет форму, передаем управление обработчику сообщений
        # Это предотвращает сброс прогресса заполнения при вводе "да" в ответах
        return await message_handler(message)
    
    # Начинаем новую форму и получаем первый вопрос
    question = form_handler.start_form(user_id)
    
    await message.answer(
        f"{config.FORM_START_MESSAGE}\n\n{question}",
        keyboard=get_form_keyboard()
    )

@bot.on.message(text=["Отмена"])
async def cancel_handler(message: Message):
    """
    Обработчик команды отмены заполнения формы или отмены удаления
    """
    user_id = message.from_id
    
    # Проверяем, есть ли ожидание удаления заявки
    if 'delete_pending' in form_handler.user_forms and user_id in form_handler.user_forms['delete_pending']:
        # Если есть, удаляем его и сообщаем о отмене удаления
        del form_handler.user_forms['delete_pending'][user_id]
        print(f"cancel_handler: Отменено удаление заявки пользователем {user_id}")
        await message.answer(
            "Удаление заявки отменено.",
            keyboard=get_start_keyboard()
        )
        return
    
    # Иначе обрабатываем как отмену заполнения формы
    form_handler.cancel_form(user_id)
    
    await message.answer(
        config.CANCEL_MESSAGE,
        keyboard=get_start_keyboard()
    )

@bot.on.message(text=["Отправить"])
async def submit_handler(message: Message):
    """
    Обработчик команды отправки заполненной формы
    Проверяет завершение заполнения и создает заявку в базе данных
    """
    user_id = message.from_id
    
    # Если пользователь не заполнял форму, игнорируем команду "отправить"
    if user_id not in form_handler.user_forms:
        await message.answer(
            """Сначала нужно заполнить форму. Нажмите "Заполнить заявку", чтобы начать.""",
            keyboard=get_start_keyboard()
        )
        return
    
    # Проверяем, полностью ли заполнена форма
    if form_handler.is_form_complete(user_id):
        # Создаем заявку и получаем её идентификатор
        ticket_id = form_handler.create_ticket(user_id)
        if ticket_id:
            await message.answer(
                f"{config.FORM_COMPLETE_MESSAGE}\nИдентификатор вашей заявки: {ticket_id}",
                keyboard=get_start_keyboard()
            )
    else:
        # Если форма не заполнена полностью, запрашиваем оставшиеся поля
        question = form_handler.get_current_question(user_id)
        await message.answer(
            f"Форма еще не заполнена полностью. {question}",
            keyboard=get_form_keyboard()
        )

@bot.on.message(text=["Мои заявки"])
async def tickets_handler(message: Message):
    """
    Обработчик команды просмотра списка заявок пользователя
    Отображает список заявок с возможностью выбора для просмотра деталей
    """
    user_id = message.from_id
    
    # Получаем все заявки пользователя из базы данных
    tickets = db_handler.get_all_tickets(user_id)
    
    # Если у пользователя нет заявок, предлагаем создать новую
    if not tickets:
        await message.answer(
            "У вас пока нет заявок. Хотите создать новую?",
            keyboard=get_start_keyboard()
        )
        return
    
    # Сохраняем список заявок пользователя в памяти для быстрого доступа
    # Это нужно для выбора заявки по номеру в списке
    form_handler.user_tickets[user_id] = [ticket['ticket_id'] for ticket in tickets]
    
    # Формируем сообщение со списком заявок
    tickets_text = "Ваши заявки:\n\n"
    for i, ticket in enumerate(tickets, 1):
        created_at = ticket['created_at'].split('T')[0]  # Берем только дату
        tickets_text += f"{i}. Заявка №{ticket['ticket_id']} от {created_at}\n"
    
    tickets_text += "\nДля просмотра подробной информации о заявке, напишите ее номер из списка (например, просто цифру 1) или полный идентификатор заявки."
    
    # Создаем клавиатуру с кнопками для выбора заявки
    keyboard = Keyboard(inline=False)
    for i in range(1, min(len(tickets) + 1, 6)):  # Ограничим 5 кнопками
        keyboard.add(Text(str(i)), color=KeyboardButtonColor.SECONDARY)
    
    keyboard.row()
    keyboard.add(Text("Заполнить заявку"), color=KeyboardButtonColor.PRIMARY)
    
    await message.answer(
        tickets_text,
        keyboard=keyboard
    )

@bot.on.message(text=[r"^\d+_\d+$", r"^\d+$"])
async def ticket_info_handler(message: Message):
    """
    Обработчик команды просмотра подробной информации о заявке
    Поддерживает выбор заявки по номеру в списке или по полному идентификатору
    """
    user_id = message.from_id
    message_text = message.text.strip()
    ticket_id = None
    
    print(f"ticket_info_handler: Получен запрос на информацию о заявке: '{message_text}', user_id={user_id}")
    
    # Убедимся, что сообщение не является командой удаления/подтверждения
    if message_text.startswith("Удалить заявку") or message_text.startswith("Подтвердить удаление"):
        print(f"ticket_info_handler: Пропускаем обработку команды: '{message_text}'")
        return
    
    # Проверяем, является ли сообщение индексом заявки или полным ID
    if message_text.isdigit() and "_" not in message_text:
        # Если это число без подчеркивания, считаем его индексом в списке
        index = int(message_text)
        # Проверяем, есть ли сохраненные заявки для пользователя
        if user_id in form_handler.user_tickets and 0 < index <= len(form_handler.user_tickets[user_id]):
            # Получаем полный ID заявки по индексу
            ticket_id = form_handler.user_tickets[user_id][index-1]
            print(f"ticket_info_handler: Получен ID заявки по индексу {index}: {ticket_id}")
        else:
            # Если индекс некорректный, предлагаем посмотреть список заявок
            await message.answer(
                "Некорректный номер заявки. Пожалуйста, используйте команду 'Мои заявки' для просмотра списка.",
                keyboard=get_start_keyboard()
            )
            return
    else:
        # Если это не индекс, считаем что это полный ID заявки
        ticket_id = message_text
        print(f"ticket_info_handler: Использован полный ID заявки: {ticket_id}")
    
    # Получаем информацию о заявке из базы данных
    ticket = db_handler.get_ticket(ticket_id)
    
    # Проверяем, найдена ли заявка и принадлежит ли она этому пользователю
    if not ticket:
        print(f"ticket_info_handler: Заявка не найдена: {ticket_id}")
        await message.answer(
            "Заявка не найдена или у вас нет доступа к ней.",
            keyboard=get_start_keyboard()
        )
        return
    
    ticket_user_id = ticket['user_id']  # Должно быть уже int благодаря изменениям в db_handler
    print(f"ticket_info_handler: Заявка принадлежит пользователю: {ticket_user_id}, запрашивает: {user_id}")
    
    if ticket_user_id != user_id:
        print(f"ticket_info_handler: Отказано в доступе к заявке: {ticket_id}")
        await message.answer(
            "Заявка не найдена или у вас нет доступа к ней.",
            keyboard=get_start_keyboard()
        )
        return
    
    # Формируем сообщение с информацией о заявке
    form_data = ticket['form_data']
    ticket_info = f"Информация о заявке {ticket_id}:\n\n"
    
    # Добавляем все поля формы и их значения
    for field, value in form_data.items():
        ticket_info += f"{field}: {value}\n"
    
    # Добавляем дату создания заявки
    ticket_info += f"\nДата создания: {ticket['created_at'].replace('T', ' ')}\n"
    
    # Сохраняем ID просматриваемой заявки для возможного удаления
    if 'last_viewed_ticket' not in form_handler.user_forms:
        form_handler.user_forms['last_viewed_ticket'] = {}
    form_handler.user_forms['last_viewed_ticket'][user_id] = ticket_id
    print(f"ticket_info_handler: Сохранен ID последней просмотренной заявки: {ticket_id}")
    
    print(f"ticket_info_handler: Показываем информацию о заявке: {ticket_id}")
    await message.answer(
        ticket_info,
        keyboard=get_ticket_detail_keyboard(ticket_id)
    )

@bot.on.message(text=["Удалить заявку"])
async def delete_ticket_handler(message: Message):
    """
    Обработчик команды удаления заявки
    Запрашивает подтверждение перед удалением заявки
    """
    user_id = message.from_id
    print(f"delete_ticket_handler: Получена команда удаления от пользователя {user_id}")
    
    # Если мы пришли из просмотра заявки, то ID заявки находится в истории сообщений
    # Проверяем, есть ли заявки у пользователя
    if user_id not in form_handler.user_tickets or not form_handler.user_tickets[user_id]:
        print(f"delete_ticket_handler: У пользователя нет заявок")
        await message.answer(
            "У вас нет заявок, которые можно удалить.",
            keyboard=get_start_keyboard()
        )
        return
    
    # Получаем последнюю просматриваемую заявку
    # Это возможно сделать из истории или текущего контекста
    # Давайте реализуем временное хранилище для последней просмотренной заявки
    
    # Инициализируем хранилище, если оно еще не существует
    if 'last_viewed_ticket' not in form_handler.user_forms:
        form_handler.user_forms['last_viewed_ticket'] = {}
    
    # Проверяем, есть ли информация о последней просмотренной заявке
    if user_id not in form_handler.user_forms['last_viewed_ticket']:
        print(f"delete_ticket_handler: Нет информации о последней просмотренной заявке")
        await message.answer(
            "Пожалуйста, сначала выберите заявку, которую хотите удалить, в разделе 'Мои заявки'.",
            keyboard=get_start_keyboard()
        )
        return
    
    ticket_id = form_handler.user_forms['last_viewed_ticket'][user_id]
    print(f"delete_ticket_handler: Найдена последняя просмотренная заявка: {ticket_id}")
    
    # Проверяем, существует ли заявка и принадлежит ли она пользователю
    ticket = db_handler.get_ticket(ticket_id)
    if not ticket:
        print(f"delete_ticket_handler: Заявка не найдена: {ticket_id}")
        await message.answer(
            "Заявка не найдена или у вас нет прав на её удаление.",
            keyboard=get_start_keyboard()
        )
        # Очищаем информацию о последней просмотренной заявке
        del form_handler.user_forms['last_viewed_ticket'][user_id]
        return
    
    ticket_user_id = ticket['user_id']
    print(f"delete_ticket_handler: Заявка {ticket_id} принадлежит пользователю: {ticket_user_id}, запрашивает: {user_id}")
    
    if ticket_user_id != user_id:
        print(f"delete_ticket_handler: Отказано в доступе к заявке: {ticket_id}")
        await message.answer(
            "Заявка не найдена или у вас нет прав на её удаление.",
            keyboard=get_start_keyboard()
        )
        # Очищаем информацию о последней просмотренной заявке
        del form_handler.user_forms['last_viewed_ticket'][user_id]
        return
    
    # Создаем клавиатуру для подтверждения удаления
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("Подтвердить удаление"), color=KeyboardButtonColor.NEGATIVE)
    keyboard.add(Text("Отмена"), color=KeyboardButtonColor.SECONDARY)
    
    print(f"delete_ticket_handler: Запрос на подтверждение удаления заявки: {ticket_id}")
    await message.answer(
        f"Вы уверены, что хотите удалить заявку {ticket_id}? Это действие нельзя отменить.",
        keyboard=keyboard
    )
    
    # Сохраняем ID заявки для удаления временно в память
    if 'delete_pending' not in form_handler.user_forms:
        form_handler.user_forms['delete_pending'] = {}
    form_handler.user_forms['delete_pending'][user_id] = ticket_id
    print(f"delete_ticket_handler: Заявка {ticket_id} отмечена для удаления пользователем {user_id}")

@bot.on.message(text=["Подтвердить удаление"])
async def confirm_delete_handler(message: Message):
    """
    Обработчик подтверждения удаления заявки
    Удаляет заявку после получения подтверждения от пользователя
    """
    user_id = message.from_id
    
    # Получаем ID заявки из временного хранилища
    if 'delete_pending' not in form_handler.user_forms or user_id not in form_handler.user_forms['delete_pending']:
        print(f"confirm_delete_handler: Нет ожидающих удаления заявок для пользователя {user_id}")
        await message.answer(
            "Не найдено заявок, ожидающих удаления. Возможно, время ожидания истекло.",
            keyboard=get_start_keyboard()
        )
        return
    
    ticket_id = form_handler.user_forms['delete_pending'][user_id]
    print(f"confirm_delete_handler: Получена команда подтверждения удаления заявки: {ticket_id}")
    
    # Дополнительная проверка прав пользователя перед удалением
    ticket = db_handler.get_ticket(ticket_id)
    if not ticket or ticket['user_id'] != user_id:
        print(f"confirm_delete_handler: Заявка не найдена или нет прав доступа: {ticket_id}")
        await message.answer(
            "Заявка не найдена или у вас нет прав на её удаление.",
            keyboard=get_start_keyboard()
        )
        # Очищаем временное хранилище
        if user_id in form_handler.user_forms['delete_pending']:
            del form_handler.user_forms['delete_pending'][user_id]
        return
    
    # Удаляем заявку
    print(f"confirm_delete_handler: Выполняем удаление заявки: {ticket_id}")
    success = form_handler.delete_ticket(user_id, ticket_id)
    print(f"confirm_delete_handler: Результат удаления: {success}")
    
    # Очищаем временное хранилище
    if user_id in form_handler.user_forms['delete_pending']:
        del form_handler.user_forms['delete_pending'][user_id]
    
    if success:
        await message.answer(
            f"Заявка {ticket_id} успешно удалена.",
            keyboard=get_start_keyboard()
        )
    else:
        await message.answer(
            "Не удалось удалить заявку. Возможно, она была уже удалена или у вас нет прав на её удаление.",
            keyboard=get_start_keyboard()
        )

@bot.on.message(text=["dev/create_random_ticket", "dev/test_ticket"])
async def dev_create_random_ticket(message: Message):
    """
    Команда разработчика для быстрого создания тестовой заявки
    """
    user_id = message.from_id
    
    # Генерируем случайные данные для формы
    form_data = generate_random_form_data()
    
    # Создаем ID заявки: ID пользователя + временная метка
    from datetime import datetime
    ticket_id = f"{user_id}_{int(datetime.now().timestamp())}"
    
    # Сохраняем заявку в базу данных
    success = db_handler.create_ticket(ticket_id, user_id, form_data)
    
    if success:
        # Формируем сообщение с информацией о созданной заявке
        ticket_info = f"Создана тестовая заявка {ticket_id}:\n\n"
        for field, value in form_data.items():
            ticket_info += f"{field}: {value}\n"
        
        await message.answer(
            ticket_info,
            keyboard=get_start_keyboard()
        )
    else:
        await message.answer(
            "Ошибка при создании тестовой заявки.",
            keyboard=get_start_keyboard()
        )

# ========================================================
# ОБРАБОТЧИК ОБЫЧНЫХ СООБЩЕНИЙ
# ========================================================

@bot.on.message()
async def message_handler(message: Message):
    """
    Обработчик всех остальных сообщений
    Обрабатывает ответы на вопросы формы и другие текстовые сообщения
    """
    user_id = message.from_id
    message_text = message.text.strip() if message.text else ""
    
    # Проверка на команду удаления заявки
    if message_text == "Удалить заявку":
        await delete_ticket_handler(message)
        return
    
    # Проверка на команду подтверждения удаления
    if message_text == "Подтвердить удаление":
        await confirm_delete_handler(message)
        return
    
    # ВАЖНО: Сначала проверяем, заполняет ли пользователь форму,
    # это имеет наивысший приоритет, чтобы избежать сброса формы при вводе команд
    if user_id in form_handler.user_forms and isinstance(form_handler.user_forms[user_id], dict) and 'current_field' in form_handler.user_forms[user_id]:
        # Обрабатываем ответ на текущий вопрос формы
        next_question = form_handler.process_answer(user_id, message.text)
        
        # Проверяем, завершена ли форма после этого ответа
        if form_handler.is_form_complete(user_id):
            # Если форма заполнена, предлагаем отправить её
            await message.answer(
                next_question,
                keyboard=get_submit_keyboard()
            )
        else:
            # Если форма не заполнена, продолжаем задавать вопросы
            await message.answer(
                next_question,
                keyboard=get_form_keyboard()
            )
        return
    
    # Проверяем, похоже ли сообщение на ID заявки или индекс в списке
    if message_text and (message_text.isdigit() or "_" in message_text):
        # Проверить, есть ли у пользователя сохраненные заявки
        if user_id in form_handler.user_tickets:
            # Перенаправим обработку в ticket_info_handler
            await ticket_info_handler(message)
            return
    
    # Если не заполняет форму и не запрашивает заявку, показываем приветственное сообщение
    await message.answer(
        """Нажмите "Заполнить заявку", чтобы начать заполнение заявки.""",
        keyboard=get_start_keyboard()
    )

# ========================================================
# ЗАПУСК БОТА
# ========================================================

if __name__ == "__main__":
    bot.run_forever()