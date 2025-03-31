from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
import config
from form_handler import FormHandler
from db_handler import DatabaseHandler

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

# ========================================================
# ОБРАБОТЧИКИ КОМАНД
# ========================================================

@bot.on.message(text=["старт", "start", "привет", "hello", "hi"])
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
    Обработчик команды отмены заполнения формы
    Удаляет данные текущей формы пользователя
    """
    user_id = message.from_id
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
    
    # Проверяем, является ли сообщение индексом заявки или полным ID
    if message_text.isdigit() and "_" not in message_text:
        # Если это число без подчеркивания, считаем его индексом в списке
        index = int(message_text)
        # Проверяем, есть ли сохраненные заявки для пользователя
        if user_id in form_handler.user_tickets and 0 < index <= len(form_handler.user_tickets[user_id]):
            # Получаем полный ID заявки по индексу
            ticket_id = form_handler.user_tickets[user_id][index-1]
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
    
    # Получаем информацию о заявке из базы данных
    ticket = db_handler.get_ticket(ticket_id)
    
    # Проверяем, найдена ли заявка и принадлежит ли она этому пользователю
    if not ticket or int(ticket['user_id']) != user_id:
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
    
    await message.answer(
        ticket_info,
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
    
    # ВАЖНО: Сначала проверяем, заполняет ли пользователь форму,
    # это имеет наивысший приоритет, чтобы избежать сброса формы при вводе команд
    if user_id in form_handler.user_forms:
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
    if message.text and (message.text.strip().isdigit() or "_" in message.text.strip()):
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