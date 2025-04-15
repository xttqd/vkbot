from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
# Используем относительный импорт для config, так как он в том же пакете
from . import config 
# Используем относительные импорты для модулей в том же пакете
from .form_handler import FormHandler 
from .db_handler import DatabaseHandler
from datetime import datetime
from typing import Dict

# Импорт из новых модулей
from . import keyboards
from . import utils

class BotHandlers:
    def __init__(self, bot: Bot, form_handler: FormHandler, db_handler: DatabaseHandler):
        self.bot = bot
        self.form_handler = form_handler
        self.db_handler = db_handler

    async def start_handler(self, message: Message):
        """
        Обработчик стартовых команд, отправляет приветственное сообщение и стартовую клавиатуру
        """
        await message.answer(
            config.WELCOME_MESSAGE,
            keyboard=keyboards.get_start_keyboard()
        )

    async def form_start_handler(self, message: Message):
        """
        Обработчик команды начала заполнения формы
        Проверяет, не заполняет ли пользователь уже форму, чтобы избежать сброса прогресса
        """
        user_id = message.from_id

        # Проверяем, не заполняет ли пользователь уже форму
        if user_id in self.form_handler.user_forms and \
           isinstance(self.form_handler.user_forms[user_id], dict) and \
           'current_field' in self.form_handler.user_forms[user_id]:
            # Если пользователь уже заполняет форму, передаем управление обработчику сообщений
            # Это предотвращает сброс прогресса заполнения при вводе "да" в ответах
            return await self.message_handler(message)

        # Начинаем новую форму и получаем первый вопрос
        question = self.form_handler.start_form(user_id)

        await message.answer(
            f"{config.FORM_START_MESSAGE}\n\n{question}",
            keyboard=keyboards.get_form_keyboard()
        )

    async def cancel_handler(self, message: Message):
        """
        Обработчик команды отмены заполнения формы или отмены удаления
        """
        user_id = message.from_id

        # Проверяем, есть ли ожидание удаления заявки
        if 'delete_pending' in self.form_handler.user_forms and user_id in self.form_handler.user_forms['delete_pending']:
            # Если есть, удаляем его и сообщаем о отмене удаления
            del self.form_handler.user_forms['delete_pending'][user_id]
            print(f"cancel_handler: Отменено удаление заявки пользователем {user_id}")
            await message.answer(
                "Удаление заявки отменено.",
                keyboard=keyboards.get_start_keyboard()
            )
            return

        # Иначе обрабатываем как отмену заполнения формы
        self.form_handler.cancel_form(user_id)

        await message.answer(
            config.CANCEL_MESSAGE,
            keyboard=keyboards.get_start_keyboard()
        )

    async def submit_handler(self, message: Message):
        """
        Обработчик команды отправки заполненной формы
        Проверяет завершение заполнения и создает заявку в базе данных
        """
        user_id = message.from_id

        # Если пользователь не заполнял форму, игнорируем команду "отправить"
        if user_id not in self.form_handler.user_forms or not isinstance(self.form_handler.user_forms[user_id], dict):
            await message.answer(
                """Сначала нужно заполнить форму. Нажмите "Заполнить заявку", чтобы начать.""",
                keyboard=keyboards.get_start_keyboard()
            )
            return

        # Проверяем, полностью ли заполнена форма
        if self.form_handler.is_form_complete(user_id):
            # Получаем данные формы ПЕРЕД тем как create_ticket их удалит
            form_data = self.form_handler.user_forms[user_id]["data"]
            
            # Создаем заявку и получаем её идентификатор
            ticket_id = self.form_handler.create_ticket(user_id)
            if ticket_id:
                # Отправляем уведомление администраторам
                await self.notify_admins_about_new_ticket(ticket_id, user_id, form_data)
                
                # Отправляем подтверждение пользователю
                await message.answer(
                    f"{config.FORM_COMPLETE_MESSAGE}\nИдентификатор вашей заявки: {ticket_id}",
                    keyboard=keyboards.get_start_keyboard()
                )
            else:
                # Сообщаем об ошибке, если не удалось создать заявку
                await message.answer(
                    "Произошла ошибка при создании заявки. Пожалуйста, попробуйте снова или свяжитесь с администратором.",
                    keyboard=keyboards.get_start_keyboard()
                )
        else:
            # Если форма не заполнена полностью, запрашиваем оставшиеся поля
            question = self.form_handler.get_current_question(user_id)
            await message.answer(
                f"Форма еще не заполнена полностью. {question}",
                keyboard=keyboards.get_form_keyboard()
            )

    async def tickets_handler(self, message: Message):
        """
        Обработчик команды просмотра списка заявок пользователя
        Отображает список заявок с возможностью выбора для просмотра деталей
        """
        user_id = message.from_id

        # Получаем все заявки пользователя из базы данных
        tickets = self.db_handler.get_all_tickets(user_id)

        # Если у пользователя нет заявок, предлагаем создать новую
        if not tickets:
            await message.answer(
                "У вас пока нет заявок. Хотите создать новую?",
                keyboard=keyboards.get_start_keyboard()
            )
            return

        # Сохраняем список заявок пользователя в памяти для быстрого доступа
        # Это нужно для выбора заявки по номеру в списке
        self.form_handler.user_tickets[user_id] = [ticket['ticket_id'] for ticket in tickets]

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

    async def ticket_info_handler(self, message: Message):
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
            if user_id in self.form_handler.user_tickets and 0 < index <= len(self.form_handler.user_tickets[user_id]):
                # Получаем полный ID заявки по индексу
                ticket_id = self.form_handler.user_tickets[user_id][index-1]
                print(f"ticket_info_handler: Получен ID заявки по индексу {index}: {ticket_id}")
            else:
                # Если индекс некорректный, предлагаем посмотреть список заявок
                await message.answer(
                    "Некорректный номер заявки. Пожалуйста, используйте команду 'Мои заявки' для просмотра списка.",
                    keyboard=keyboards.get_start_keyboard()
                )
                return
        else:
            # Если это не индекс, считаем что это полный ID заявки
            ticket_id = message_text
            print(f"ticket_info_handler: Использован полный ID заявки: {ticket_id}")

        # Получаем информацию о заявке из базы данных
        ticket = self.db_handler.get_ticket(ticket_id)

        # Проверяем, найдена ли заявка и принадлежит ли она этому пользователю
        if not ticket:
            print(f"ticket_info_handler: Заявка не найдена: {ticket_id}")
            await message.answer(
                "Заявка не найдена или у вас нет доступа к ней.",
                keyboard=keyboards.get_start_keyboard()
            )
            return

        ticket_user_id = ticket['user_id']
        print(f"ticket_info_handler: Заявка принадлежит пользователю: {ticket_user_id}, запрашивает: {user_id}")

        if ticket_user_id != user_id:
            print(f"ticket_info_handler: Отказано в доступе к заявке: {ticket_id}")
            await message.answer(
                "Заявка не найдена или у вас нет доступа к ней.",
                keyboard=keyboards.get_start_keyboard()
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
        if 'last_viewed_ticket' not in self.form_handler.user_forms:
            self.form_handler.user_forms['last_viewed_ticket'] = {}
        self.form_handler.user_forms['last_viewed_ticket'][user_id] = ticket_id
        print(f"ticket_info_handler: Сохранен ID последней просмотренной заявки: {ticket_id}")

        print(f"ticket_info_handler: Показываем информацию о заявке: {ticket_id}")
        await message.answer(
            ticket_info,
            keyboard=keyboards.get_ticket_detail_keyboard(ticket_id)
        )

    async def delete_ticket_handler(self, message: Message):
        """
        Обработчик команды удаления заявки
        Запрашивает подтверждение перед удалением заявки
        """
        user_id = message.from_id
        print(f"delete_ticket_handler: Получена команда удаления от пользователя {user_id}")

        # Проверяем, есть ли информация о последней просмотренной заявке
        if 'last_viewed_ticket' not in self.form_handler.user_forms or \
           user_id not in self.form_handler.user_forms['last_viewed_ticket']:
            print(f"delete_ticket_handler: Нет информации о последней просмотренной заявке для user_id={user_id}")
            await message.answer(
                "Пожалуйста, сначала выберите заявку, которую хотите удалить, в разделе 'Мои заявки'.",
                keyboard=keyboards.get_start_keyboard()
            )
            return

        ticket_id = self.form_handler.user_forms['last_viewed_ticket'][user_id]
        print(f"delete_ticket_handler: Найдена последняя просмотренная заявка: {ticket_id}")

        # Проверяем, существует ли заявка и принадлежит ли она пользователю
        ticket = self.db_handler.get_ticket(ticket_id)
        if not ticket:
            print(f"delete_ticket_handler: Заявка не найдена: {ticket_id}")
            await message.answer(
                "Заявка не найдена или у вас нет прав на её удаление.",
                keyboard=keyboards.get_start_keyboard()
            )
            # Очищаем информацию о последней просмотренной заявке
            if user_id in self.form_handler.user_forms.get('last_viewed_ticket', {}):
                 del self.form_handler.user_forms['last_viewed_ticket'][user_id]
            return

        ticket_user_id = ticket['user_id']
        print(f"delete_ticket_handler: Заявка {ticket_id} принадлежит пользователю: {ticket_user_id}, запрашивает: {user_id}")

        if ticket_user_id != user_id:
            print(f"delete_ticket_handler: Отказано в доступе к заявке: {ticket_id}")
            await message.answer(
                "Заявка не найдена или у вас нет прав на её удаление.",
                keyboard=keyboards.get_start_keyboard()
            )
            # Очищаем информацию о последней просмотренной заявке
            if user_id in self.form_handler.user_forms.get('last_viewed_ticket', {}):
                 del self.form_handler.user_forms['last_viewed_ticket'][user_id]
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
        if 'delete_pending' not in self.form_handler.user_forms:
            self.form_handler.user_forms['delete_pending'] = {}
        self.form_handler.user_forms['delete_pending'][user_id] = ticket_id
        print(f"delete_ticket_handler: Заявка {ticket_id} отмечена для удаления пользователем {user_id}")

    async def confirm_delete_handler(self, message: Message):
        """
        Обработчик подтверждения удаления заявки
        Удаляет заявку после получения подтверждения от пользователя
        """
        user_id = message.from_id

        # Получаем ID заявки из временного хранилища
        if 'delete_pending' not in self.form_handler.user_forms or user_id not in self.form_handler.user_forms['delete_pending']:
            print(f"confirm_delete_handler: Нет ожидающих удаления заявок для пользователя {user_id}")
            await message.answer(
                "Не найдено заявок, ожидающих удаления. Возможно, время ожидания истекло.",
                keyboard=keyboards.get_start_keyboard()
            )
            return

        ticket_id = self.form_handler.user_forms['delete_pending'][user_id]
        print(f"confirm_delete_handler: Получена команда подтверждения удаления заявки: {ticket_id}")

        # Дополнительная проверка прав пользователя перед удалением
        ticket = self.db_handler.get_ticket(ticket_id)
        if not ticket or ticket['user_id'] != user_id:
            print(f"confirm_delete_handler: Заявка не найдена или нет прав доступа: {ticket_id}")
            await message.answer(
                "Заявка не найдена или у вас нет прав на её удаление.",
                keyboard=keyboards.get_start_keyboard()
            )
            # Очищаем временное хранилище
            if user_id in self.form_handler.user_forms.get('delete_pending', {}):
                del self.form_handler.user_forms['delete_pending'][user_id]
            return

        # Удаляем заявку
        print(f"confirm_delete_handler: Выполняем удаление заявки: {ticket_id}")
        success = self.form_handler.delete_ticket(user_id, ticket_id)
        print(f"confirm_delete_handler: Результат удаления: {success}")

        # Очищаем временное хранилище
        if user_id in self.form_handler.user_forms.get('delete_pending', {}):
            del self.form_handler.user_forms['delete_pending'][user_id]

        if success:
            await message.answer(
                f"Заявка {ticket_id} успешно удалена.",
                keyboard=keyboards.get_start_keyboard()
            )
            # Отправляем уведомление администраторам ПОСЛЕ успешного удаления
            await self.notify_admins_about_deleted_ticket(ticket_id, user_id)
        else:
            await message.answer(
                "Не удалось удалить заявку. Возможно, она была уже удалена или у вас нет прав на её удаление.",
                keyboard=keyboards.get_start_keyboard()
            )

    async def dev_create_random_ticket(self, message: Message):
        """
        Команда разработчика для быстрого создания тестовой заявки
        """
        user_id = message.from_id

        # Генерируем случайные данные для формы
        form_data = utils.generate_random_form_data()

        # Создаем ID заявки: ID пользователя + временная метка
        ticket_id = f"{user_id}_{int(datetime.now().timestamp())}"

        # Сохраняем заявку в базу данных
        success = self.db_handler.create_ticket(ticket_id, user_id, form_data)

        if success:
            # Формируем сообщение с информацией о созданной заявке
            ticket_info = f"Создана тестовая заявка {ticket_id}:\n\n"
            for field, value in form_data.items():
                ticket_info += f"{field}: {value}\n"

            await message.answer(
                ticket_info,
                keyboard=keyboards.get_start_keyboard()
            )
        else:
            await message.answer(
                "Ошибка при создании тестовой заявки.",
                keyboard=keyboards.get_start_keyboard()
            )

    async def message_handler(self, message: Message):
        """
        Обработчик всех остальных сообщений
        Обрабатывает ответы на вопросы формы и другие текстовые сообщения
        """
        user_id = message.from_id
        message_text = message.text.strip() if message.text else ""

        # Проверка на команду удаления заявки
        if message_text == "Удалить заявку":
            await self.delete_ticket_handler(message)
            return

        # Проверка на команду подтверждения удаления
        if message_text == "Подтвердить удаление":
            await self.confirm_delete_handler(message)
            return

        # ВАЖНО: Сначала проверяем, заполняет ли пользователь форму,
        # это имеет наивысший приоритет, чтобы избежать сброса формы при вводе команд
        if user_id in self.form_handler.user_forms and \
           isinstance(self.form_handler.user_forms[user_id], dict) and \
           'current_field' in self.form_handler.user_forms[user_id]:
            # Обрабатываем ответ на текущий вопрос формы
            next_question = self.form_handler.process_answer(user_id, message.text)

            # Проверяем, завершена ли форма после этого ответа
            if self.form_handler.is_form_complete(user_id):
                # Если форма заполнена, предлагаем отправить её
                await message.answer(
                    next_question,
                    keyboard=keyboards.get_submit_keyboard()
                )
            else:
                # Если форма не заполнена, продолжаем задавать вопросы
                await message.answer(
                    next_question,
                    keyboard=keyboards.get_form_keyboard()
                )
            return

        # Проверяем, похоже ли сообщение на ID заявки или индекс в списке
        # Добавляем проверку, что текст вообще есть, чтобы не обрабатывать пустые сообщения или стикеры
        if message_text and (message_text.isdigit() or ("_" in message_text and all(part.isdigit() for part in message_text.split('_')))):
            # Проверить, есть ли у пользователя сохраненные заявки (даже если список пуст)
            if user_id in self.form_handler.user_tickets:
                # Перенаправим обработку в ticket_info_handler
                await self.ticket_info_handler(message)
                return

        # Если не заполняет форму и не запрашивает заявку, показываем приветственное сообщение
        await message.answer(
            """Неизвестная команда. Используйте клавиатуру или команды:
- Заполнить заявку
- Мои заявки
Нажмите "Начать", если вы потерялись.""",
            keyboard=keyboards.get_start_keyboard()
        )

    def register_handlers(self):
        self.bot.on.message(text=["Начать", "start", "/start"])(self.start_handler)
        self.bot.on.message(text=["Заполнить заявку"])(self.form_start_handler)
        self.bot.on.message(text=["Отмена"])(self.cancel_handler)
        self.bot.on.message(text=["Отправить"])(self.submit_handler)
        self.bot.on.message(text=["Мои заявки"])(self.tickets_handler)
        self.bot.on.message(text=[r"^\d+_\d+$", r"^\d+$"])(self.ticket_info_handler)
        self.bot.on.message(text=["Удалить заявку"])(self.delete_ticket_handler)
        self.bot.on.message(text=["Подтвердить удаление"])(self.confirm_delete_handler)
        self.bot.on.message(text=["dev/create_random_ticket", "dev/test_ticket"])(self.dev_create_random_ticket)
        self.bot.on.message()(self.message_handler) # Default handler for other messages 

    # ========================================================
    # УВЕДОМЛЕНИЕ АДМИНИСТРАТОРОВ
    # ========================================================
    async def notify_admins_about_new_ticket(self, ticket_id: str, user_id: int, form_data: Dict):
        """
        Отправляет уведомление о новой заявке администраторам, указанным в config.ADMIN_IDS.
        """
        if not config.ADMIN_IDS:
            print("notify_admins_about_new_ticket: Admin IDs not configured, skipping notification.")
            return

        try:
            # Формируем краткое содержание заявки
            form_summary = ""
            for field, value in form_data.items():
                form_summary += f"> {field}: {value}\n"
            form_summary = form_summary.strip()

            # Создаем ссылку на пользователя
            user_link = f"vk.com/id{user_id}"

            # Форматируем сообщение по шаблону из конфига
            message_text = config.NEW_TICKET_NOTIFICATION_TEMPLATE.format(
                ticket_id=ticket_id,
                user_id=user_id,
                user_link=user_link,
                form_summary=form_summary
            )
            # Дополнительно можно добавить форматирование для конкретных полей, если нужно
            # message_text = message_text.format(**form_data)

            # Отправляем сообщение каждому админу
            for admin_id in config.ADMIN_IDS:
                await self.bot.api.messages.send(
                    peer_id=admin_id,
                    message=message_text,
                    random_id=0 # random_id нужен для предотвращения дублирования сообщений
                )
                print(f"notify_admins_about_new_ticket: Notification sent to admin {admin_id} for ticket {ticket_id}")

        except Exception as e:
            print(f"Error sending notification to admins for ticket {ticket_id}: {e}") 

    async def notify_admins_about_deleted_ticket(self, ticket_id: str, user_id: int):
        """
        Отправляет уведомление об удалении заявки администраторам.
        """
        if not config.ADMIN_IDS:
            print("notify_admins_about_deleted_ticket: Admin IDs not configured, skipping notification.")
            return

        try:
            # Создаем ссылку на пользователя
            user_link = f"vk.com/id{user_id}"

            # Форматируем сообщение по шаблону из конфига
            message_text = config.TICKET_DELETED_NOTIFICATION_TEMPLATE.format(
                ticket_id=ticket_id,
                user_id=user_id,
                user_link=user_link
            )

            # Отправляем сообщение каждому админу
            for admin_id in config.ADMIN_IDS:
                await self.bot.api.messages.send(
                    peer_id=admin_id,
                    message=message_text,
                    random_id=0
                )
                print(f"notify_admins_about_deleted_ticket: Deletion notification sent to admin {admin_id} for ticket {ticket_id}")

        except Exception as e:
            print(f"Error sending deletion notification to admins for ticket {ticket_id}: {e}") 