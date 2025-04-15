import json
import logging
from vkbottle.bot import Bot, Message
from vkbottle.dispatch.rules import ABCRule
from vkbottle.dispatch.rules.base import PeerRule, PayloadRule
from . import config 
from .form_handler import FormHandler 
from .db_handler import DatabaseHandler
from typing import Dict, Optional
from . import keyboards

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, bot: Bot, form_handler: FormHandler, db_handler: DatabaseHandler):
        self.bot = bot
        self.form_handler = form_handler
        self.db_handler = db_handler
        
        self.ignore_notification_chat_rule = (
            PeerRule(from_chat=True) & 
            PeerRule([config.NOTIFICATION_CHAT_ID] if config.NOTIFICATION_CHAT_ID else []) 
        )
        self.from_users_or_other_chats_rule = ~self.ignore_notification_chat_rule

    async def start_handler(self, message: Message):
        """ Обработчик стартовой команды / кнопки Начать """
        logger.info(f"Start command received from user {message.from_id}")
        await message.answer(
            config.WELCOME_MESSAGE,
            keyboard=keyboards.get_start_keyboard()
        )

    async def form_start_handler(self, message: Message):
        """ Обработчик команды начала заполнения формы """
        user_id = message.from_id
        logger.info(f"Start form command received from user {user_id}")

        if user_id in self.form_handler.user_forms:
            question = self.form_handler.get_current_question(user_id)
            await message.answer(
                f"Вы уже заполняете форму.\n\n{question}",
                keyboard=keyboards.get_form_keyboard()
            )
            return

        question = self.form_handler.start_form(user_id)
        await message.answer(
            f"{config.FORM_START_MESSAGE}\n\n{question}",
            keyboard=keyboards.get_form_keyboard()
        )

    async def cancel_form_handler(self, message: Message):
        """ Обработчик команды отмены заполнения формы """
        user_id = message.from_id
        logger.info(f"Cancel form command received from user {user_id}")
        self.form_handler.cancel_form(user_id)
        self.form_handler.clear_user_state(user_id)
        await message.answer(
            config.CANCEL_MESSAGE,
            keyboard=keyboards.get_start_keyboard()
        )

    async def submit_form_handler(self, message: Message):
        """ Обработчик команды отправки заполненной формы """
        user_id = message.from_id
        logger.info(f"Submit form command received from user {user_id}")

        if not self.form_handler.is_form_complete(user_id):
            logger.warning(f"User {user_id} tried to submit an incomplete form.")
            question = self.form_handler.get_current_question(user_id)
            await message.answer(
                f"Форма еще не заполнена полностью.\n\n{question}",
                keyboard=keyboards.get_form_keyboard()
            )
            return

        form_data = self.form_handler.user_forms.get(user_id, {}).get("data", {})
        ticket_id = self.form_handler.create_ticket(user_id)
        
        if ticket_id and form_data:
            await self.notify_admins_about_new_ticket(ticket_id, user_id, form_data)
            await message.answer(
                f"{config.FORM_COMPLETE_MESSAGE}\nИдентификатор вашей заявки: {ticket_id}",
                keyboard=keyboards.get_start_keyboard()
            )
        else:
            logger.error(f"Failed to create ticket or get form_data for user {user_id} on submit.")
            await message.answer(
                config.ERROR_TICKET_CREATION,
                keyboard=keyboards.get_start_keyboard()
            )
            
    async def list_tickets_handler(self, message: Message):
        """ Обработчик команды просмотра списка заявок """
        user_id = message.from_id
        logger.info(f"List tickets command received from user {user_id}")
        tickets = self.db_handler.get_all_tickets(user_id)

        if not tickets:
            await message.answer(
                "У вас пока нет заявок. Хотите создать новую?",
                keyboard=keyboards.get_start_keyboard()
            )
            return

        self.form_handler.user_tickets[user_id] = [t['ticket_id'] for t in tickets]

        tickets_text = "Ваши заявки:\n\n"
        for i, ticket in enumerate(tickets, 1):
            created_at_str = ticket['created_at'].split('T')[0]
            tickets_text += f"{i}. Заявка №{ticket['ticket_id']} от {created_at_str}\n"
        tickets_text += "\nНажмите на кнопку с номером заявки для просмотра деталей."

        await message.answer(
            tickets_text,
            keyboard=keyboards.get_ticket_list_keyboard(tickets)
        )

    async def view_ticket_handler(self, message: Message):
        """ Обработчик просмотра деталей конкретной заявки (по payload) """
        user_id = message.from_id
        payload = json.loads(message.payload)
        ticket_id = payload.get("ticket_id")
        logger.info(f"View ticket command received for ticket {ticket_id} from user {user_id}")

        if not ticket_id:
             logger.warning(f"View ticket command from user {user_id} without ticket_id in payload.")
             await message.answer("Ошибка: Не удалось определить ID заявки.", keyboard=keyboards.get_start_keyboard())
             return

        ticket = self.db_handler.get_ticket(ticket_id)

        if not ticket or ticket['user_id'] != user_id:
            logger.warning(f"User {user_id} tried to view unauthorized or non-existent ticket {ticket_id}")
            await message.answer(config.ERROR_TICKET_NOT_FOUND, keyboard=keyboards.get_start_keyboard())
            return

        form_data = ticket['form_data']
        ticket_info = f"Информация о заявке {ticket_id}:\n\n"
        for field, value in form_data.items():
            ticket_info += f"{field}: {value}\n"
        ticket_info += f"\nДата создания: {ticket['created_at'].replace('T', ' ')}\n"

        self.form_handler.set_user_state(user_id, 'last_viewed_ticket', ticket_id)

        await message.answer(
            ticket_info,
            keyboard=keyboards.get_ticket_detail_keyboard(ticket_id)
        )

    async def prompt_ticket_deletion(self, message: Message, ticket_id: str):
        """ Вспомогательный метод: проверяет заявку и запрашивает подтверждение удаления."""
        user_id = message.from_id
        logger.info(f"Prompting deletion for ticket {ticket_id} requested by user {user_id}")

        if not ticket_id:
            logger.warning(f"prompt_ticket_deletion called without ticket_id for user {user_id}.")
            await message.answer("Ошибка: Не удалось определить ID заявки для удаления.", keyboard=keyboards.get_start_keyboard())
            return

        ticket = self.db_handler.get_ticket(ticket_id)
        if not ticket or ticket['user_id'] != user_id:
            logger.warning(f"User {user_id} tried prompt_ticket_deletion for invalid ticket {ticket_id}")
            await message.answer(config.ERROR_TICKET_NOT_FOUND, keyboard=keyboards.get_start_keyboard())
            self.form_handler.clear_user_state(user_id, 'ticket_to_delete')
            return

        self.form_handler.set_user_state(user_id, 'ticket_to_delete', ticket_id)

        await message.answer(
            f"Вы уверены, что хотите удалить заявку {ticket_id}? Это действие нельзя отменить.",
            keyboard=keyboards.get_delete_confirm_keyboard(ticket_id)
        )

    async def delete_ticket_prompt_handler(self, message: Message):
        """ Запрашивает подтверждение удаления заявки (срабатывает от кнопки). """
        payload = json.loads(message.payload)
        ticket_id = payload.get("ticket_id")
        await self.delete_ticket_confirm_handler(message, ticket_id)
        
    async def delete_ticket_confirm_handler(self, message: Message, ticket_id_from_trigger: Optional[str] = None):
        """ 
        Обрабатывает подтверждение удаления заявки.
        Может вызываться от кнопки (с payload -> ticket_id_from_trigger) 
        или от текста (без payload -> ticket_id_from_trigger is None).
        """
        user_id = message.from_id

        if message.payload:
             try:
                 payload = json.loads(message.payload)
                 ticket_id_from_trigger = payload.get("ticket_id")
             except json.JSONDecodeError:
                 logger.error(f"Invalid payload format for delete confirm from user {user_id}: {message.payload}")
                 ticket_id_from_trigger = None

        ticket_id_from_state = self.form_handler.get_user_state(user_id, 'ticket_to_delete')
        logger.info(f"Confirm delete triggered for ticket {ticket_id_from_trigger} (state: {ticket_id_from_state}) by user {user_id}")

        if not ticket_id_from_state or (ticket_id_from_trigger and ticket_id_from_trigger != ticket_id_from_state):
            logger.warning(f"Delete confirm mismatch or missing state for user {user_id}. Trigger: {ticket_id_from_trigger}, State: {ticket_id_from_state}")
            await message.answer(config.ERROR_DELETE_PENDING_NOT_FOUND, keyboard=keyboards.get_start_keyboard())
            self.form_handler.clear_user_state(user_id, 'ticket_to_delete')
            return

        ticket_id = ticket_id_from_state
        success = self.form_handler.delete_ticket(user_id, ticket_id)
        self.form_handler.clear_user_state(user_id, 'ticket_to_delete')

        if success:
            await message.answer(f"Заявка {ticket_id} успешно удалена.", keyboard=keyboards.get_start_keyboard())
            await self.notify_admins_about_deleted_ticket(ticket_id, user_id)
        else:
            await message.answer(config.ERROR_TICKET_DELETION, keyboard=keyboards.get_start_keyboard())

    async def cancel_action_handler(self, message: Message):
        """ Обработчик кнопки "Отмена" в различных контекстах (например, отмена удаления) """
        user_id = message.from_id
        logger.info(f"Cancel action command received from user {user_id}")
        self.form_handler.clear_user_state(user_id)
        await message.answer("Действие отменено.", keyboard=keyboards.get_start_keyboard())

    async def form_message_handler(self, message: Message):
        """ Обрабатывает текстовые ответы пользователя во время заполнения формы """
        user_id = message.from_id
        if user_id not in self.form_handler.user_forms:
            logger.debug(f"Text message '{message.text}' from user {user_id} received, but not filling form. Ignoring.")
            await self.default_handler(message)
            return

        logger.info(f"Processing form answer '{message.text}' from user {user_id}")
        next_question_or_status = self.form_handler.process_answer(user_id, message.text)
        
        if self.form_handler.is_form_complete(user_id):
            keyboard = keyboards.get_submit_keyboard()
        else:
            keyboard = keyboards.get_form_keyboard()
            
        await message.answer(next_question_or_status, keyboard=keyboard)
        
    async def default_handler(self, message: Message):
        """
        Обработчик для сообщений, не попавших под другие правила.
        Пытается обработать сообщение как индекс заявки, "Удалить заявку" или "Подтвердить удаление".
        """
        user_id = message.from_id
        message_text = message.text.strip()
        logger.info(f"Default handler caught message '{message_text}' from user {user_id}")
        message_text_lower = message_text.lower()

        if message_text_lower == "удалить заявку":
            last_viewed_ticket = self.form_handler.get_user_state(user_id, 'last_viewed_ticket')
            if last_viewed_ticket:
                logger.info(f"Interpreting text 'Удалить заявку', prompting deletion for last viewed ticket {last_viewed_ticket}")
                await self.prompt_ticket_deletion(message, last_viewed_ticket)
                return
            else:
                logger.warning(f"User {user_id} sent 'Удалить заявку' text but no last viewed ticket found in state.")
                await message.answer("Пожалуйста, сначала выберите заявку для удаления из списка 'Мои заявки'.", keyboard=keyboards.get_start_keyboard())
            return

        elif message_text_lower == "подтвердить удаление":
            ticket_to_delete = self.form_handler.get_user_state(user_id, 'ticket_to_delete')
            if ticket_to_delete:
                logger.info(f"Interpreting text 'Подтвердить удаление', confirming deletion for ticket {ticket_to_delete}")
                await self.delete_ticket_confirm_handler(message, ticket_to_delete)
                return
            else:
                logger.warning(f"User {user_id} sent 'Подтвердить удаление' text but no ticket_to_delete found in state.")
                await self.delete_ticket_confirm_handler(message, None)
                return

        elif message_text.isdigit() and user_id in self.form_handler.user_tickets:
            try:
                index = int(message_text) - 1
                cached_tickets = self.form_handler.user_tickets[user_id]
                if 0 <= index < len(cached_tickets):
                    ticket_id = cached_tickets[index]
                    logger.info(f"Interpreting message as index {index+1}, viewing ticket {ticket_id}")
                    await self.show_ticket_details(message, ticket_id)
                    return
                else:
                    logger.warning(f"User {user_id} entered invalid ticket index: {index+1}")
            except ValueError:
                 logger.error(f"ValueError converting message text '{message_text}' to int for user {user_id}")
            except Exception as e:
                 logger.error(f"Error processing message as ticket index for user {user_id}: {e}")
        
        await message.answer(
            config.UNKNOWN_COMMAND_MESSAGE,
            keyboard=keyboards.get_start_keyboard()
        )

    async def show_ticket_details(self, message: Message, ticket_id: str):
        """ Вспомогательный метод для отображения деталей заявки """
        user_id = message.from_id
        ticket = self.db_handler.get_ticket(ticket_id)

        if not ticket or ticket['user_id'] != user_id:
            logger.warning(f"User {user_id} failed to view ticket {ticket_id} via show_ticket_details (not found or unauthorized).")
            await message.answer(config.ERROR_TICKET_NOT_FOUND, keyboard=keyboards.get_start_keyboard())
            return

        form_data = ticket['form_data']
        ticket_info = f"Информация о заявке {ticket_id}:\n\n"
        for field, value in form_data.items():
            ticket_info += f"{field}: {value}\n"
        ticket_info += f"\nДата создания: {ticket['created_at'].replace('T', ' ')}\n"
        
        self.form_handler.set_user_state(user_id, 'last_viewed_ticket', ticket_id)

        await message.answer(
            ticket_info,
            keyboard=keyboards.get_ticket_detail_keyboard(ticket_id)
        )

    def register_handlers(self):
        logger.info("Registering handlers...")
        
        self.bot.on.message(self.from_users_or_other_chats_rule, PayloadRule({"command": "start_form"}))(self.form_start_handler)
        self.bot.on.message(self.from_users_or_other_chats_rule, PayloadRule({"command": "cancel_form"}))(self.cancel_form_handler)
        self.bot.on.message(self.from_users_or_other_chats_rule, PayloadRule({"command": "submit_form"}))(self.submit_form_handler)
        self.bot.on.message(self.from_users_or_other_chats_rule, PayloadRule({"command": "list_tickets"}))(self.list_tickets_handler)
        self.bot.on.message(self.from_users_or_other_chats_rule, PayloadRule({"command": "view_ticket"}))(self.view_ticket_handler)
        self.bot.on.message(self.from_users_or_other_chats_rule, PayloadRule({"command": "delete_ticket_prompt"}))(self.delete_ticket_prompt_handler)
        self.bot.on.message(self.from_users_or_other_chats_rule, PayloadRule({"command": "delete_ticket_confirm"}))(self.delete_ticket_confirm_handler)
        self.bot.on.message(self.from_users_or_other_chats_rule, PayloadRule({"command": "cancel_action"}))(self.cancel_action_handler)
        
        self.bot.on.message(self.from_users_or_other_chats_rule, text=["Начать", "start", "/start"])(self.start_handler)
        
        class IsFillingFormRule(ABCRule):
            def __init__(self, form_handler: FormHandler):
                 self.form_handler = form_handler

            async def check(self, message: Message) -> bool:
                return message.from_id in self.form_handler.user_forms

        self.bot.on.message(self.from_users_or_other_chats_rule, IsFillingFormRule(self.form_handler))(self.form_message_handler)

        self.bot.on.message(self.from_users_or_other_chats_rule)(self.default_handler)
        
        async def ignore_chat_handler(message: Message): 
            logger.debug(f"Ignoring message in notification chat {message.peer_id}")
        self.bot.on.message(self.ignore_notification_chat_rule)(ignore_chat_handler)
        
        logger.info("Handlers registered.")

    async def notify_admins_about_new_ticket(self, ticket_id: str, user_id: int, form_data: Dict):
        if not config.NOTIFICATION_CHAT_ID:
            logger.warning("notify_admins_about_new_ticket: NOTIFICATION_CHAT_ID not configured.")
            return
        try:
            form_summary = "\n".join([f"> {k}: {v}" for k, v in form_data.items()])
            user_link = f"vk.com/id{user_id}"
            message_text = config.NEW_TICKET_NOTIFICATION_TEMPLATE.format(
                ticket_id=ticket_id, user_id=user_id, user_link=user_link, form_summary=form_summary
            )
            await self.bot.api.messages.send(
                peer_id=config.NOTIFICATION_CHAT_ID, message=message_text, random_id=0
            )
            logger.info(f"New ticket notification sent to chat {config.NOTIFICATION_CHAT_ID} for ticket {ticket_id}")
        except Exception as e:
            logger.error(f"Error sending new ticket notification to chat {config.NOTIFICATION_CHAT_ID} for ticket {ticket_id}: {e}")

    async def notify_admins_about_deleted_ticket(self, ticket_id: str, user_id: int):
        if not config.NOTIFICATION_CHAT_ID:
            logger.warning("notify_admins_about_deleted_ticket: NOTIFICATION_CHAT_ID not configured.")
            return
        try:
            user_link = f"vk.com/id{user_id}"
            message_text = config.TICKET_DELETED_NOTIFICATION_TEMPLATE.format(
                ticket_id=ticket_id, user_id=user_id, user_link=user_link
            )
            await self.bot.api.messages.send(
                peer_id=config.NOTIFICATION_CHAT_ID, message=message_text, random_id=0
            )
            logger.info(f"Deletion notification sent to chat {config.NOTIFICATION_CHAT_ID} for ticket {ticket_id}")
        except Exception as e:
            logger.error(f"Error sending deletion notification to chat {config.NOTIFICATION_CHAT_ID} for ticket {ticket_id}: {e}") 