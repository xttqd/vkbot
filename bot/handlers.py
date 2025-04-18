import json
import logging
from vkbottle.bot import Bot, Message
from vkbottle.dispatch.rules.base import PeerRule, PayloadRule
from . import config
from .form_handler import FormHandler
from .db_handler import DatabaseHandler
from typing import Dict, Optional, Any, NoReturn, List, TYPE_CHECKING
from . import keyboards
from datetime import datetime
from .rules import IsFillingFormRule

if TYPE_CHECKING:
    from vkbottle.dispatch.rules.abc import Rule

logger = logging.getLogger(__name__)


class BotHandlers:
    bot: Bot
    form_handler: FormHandler
    db_handler: DatabaseHandler
    ignore_notification_chat_rule: "Rule"
    from_users_or_other_chats_rule: "Rule"

    def __init__(
        self, bot: Bot, form_handler: FormHandler, db_handler: DatabaseHandler
    ) -> None:
        self.bot = bot
        self.form_handler = form_handler
        self.db_handler = db_handler

        self.ignore_notification_chat_rule = PeerRule(from_chat=True) & PeerRule(
            [config.NOTIFICATION_CHAT_ID] if config.NOTIFICATION_CHAT_ID else []
        )
        self.from_users_or_other_chats_rule = ~self.ignore_notification_chat_rule

        self.is_filling_form_rule = IsFillingFormRule(self.form_handler)

    async def start_handler(self, message: Message) -> None:
        logger.info(f"Start command received from user {message.from_id}")
        await message.answer(
            config.WELCOME_MESSAGE, keyboard=keyboards.get_start_keyboard()
        )

    async def form_start_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        logger.info(f"Start form command received from user {user_id}")

        if user_id in self.form_handler.user_forms:
            question: str = self.form_handler.get_current_question(user_id)
            await message.answer(
                f"Вы уже заполняете форму.\n\n{question}",
                keyboard=keyboards.get_form_keyboard(),
            )
            return

        question = self.form_handler.start_form(user_id)
        await message.answer(
            f"{config.FORM_START_MESSAGE}\n\n{question}",
            keyboard=keyboards.get_form_keyboard(),
        )

    async def cancel_form_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        logger.info(f"Cancel form command received from user {user_id}")
        self.form_handler.cancel_form(user_id)
        self.form_handler.clear_user_state(user_id)
        await message.answer(
            config.CANCEL_MESSAGE, keyboard=keyboards.get_start_keyboard()
        )

    async def submit_form_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        logger.info(f"Submit form command received from user {user_id}")
        if not self.form_handler.is_form_complete(user_id):
            await message.answer(
                "Форма еще не заполнена. Пожалуйста, ответьте на все вопросы.",
                keyboard=keyboards.get_form_keyboard(),
            )
            return

        form_data: Optional[Dict[str, str]] = None
        if user_id in self.form_handler.user_forms:
            form_data = self.form_handler.user_forms[user_id]["data"]

        ticket_id: Optional[str] = await self.form_handler.create_ticket(user_id)

        if ticket_id:
            logger.info(
                f"Form submitted successfully by user {user_id}, ticket ID: {ticket_id}"
            )
            await message.answer(
                f"Ваша заявка №{ticket_id} успешно создана!",
                keyboard=keyboards.get_start_keyboard(),
            )
            if form_data:
                await self.notify_admins_about_new_ticket(ticket_id, user_id, form_data)
            else:
                logger.warning(
                    f"Could not retrieve form_data for notification for ticket {ticket_id}"
                )
        else:
            error_msg = "Не удалось сохранить заявку из-за ошибки. Попробуйте нажать 'Отправить' еще раз."
            keyboard = keyboards.get_submit_keyboard()

            logger.error(
                f"Failed to submit form for user {user_id}. DB error occurred but form state retained."
            )
            await message.answer(error_msg, keyboard=keyboard)

    async def list_tickets_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        logger.info(f"List tickets command received from user {user_id}")
        tickets: List[Dict[str, Any]] = await self.db_handler.get_all_tickets(user_id)

        if not tickets:
            await message.answer(
                "У вас пока нет заявок. Хотите создать новую?",
                keyboard=keyboards.get_start_keyboard(),
            )
            return

        self.form_handler.user_tickets[user_id] = [t["ticket_id"] for t in tickets]

        tickets_text: str = "Ваши заявки:\n\n"
        for i, ticket in enumerate(tickets, 1):
            try:
                created_at: datetime = datetime.fromisoformat(ticket["created_at"])
                created_at_str: str = created_at.strftime("%Y-%m-%d")
                tickets_text += (
                    f"{i}. Заявка №{ticket['ticket_id']} от {created_at_str}\n"
                )
            except (TypeError, ValueError, KeyError) as e:
                logger.error(
                    f"Error formatting ticket data for list: {ticket}. Error: {e}"
                )
                tickets_text += f"{i}. Ошибка отображения заявки ID: {ticket.get('ticket_id', 'N/A')}\n"
        tickets_text += "\nНажмите на кнопку с номером заявки для просмотра деталей."

        await message.answer(
            tickets_text, keyboard=keyboards.get_ticket_list_keyboard(tickets)
        )

    async def view_ticket_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        try:
            payload: Dict[str, Any] = json.loads(message.payload or {})
            ticket_id: Optional[str] = payload.get("ticket_id")
        except json.JSONDecodeError:
            logger.warning(
                f"Invalid JSON payload for view_ticket from user {user_id}: {message.payload}"
            )
            ticket_id = None

        logger.info(
            f"View ticket command received for ticket {ticket_id} from user {user_id}"
        )

        if not ticket_id:
            logger.warning(
                f"View ticket command from user {user_id} without valid ticket_id in payload."
            )
            await message.answer(
                "Ошибка: Не удалось определить ID заявки.",
                keyboard=keyboards.get_start_keyboard(),
            )
            return

        await self.show_ticket_details(message, ticket_id)

    async def prompt_ticket_deletion(self, message: Message, ticket_id: str) -> None:
        user_id: int = message.from_id
        logger.info(
            f"Prompting deletion for ticket {ticket_id} requested by user {user_id}"
        )

        if not ticket_id:
            logger.warning(
                f"prompt_ticket_deletion called without ticket_id for user {user_id}."
            )
            await message.answer(
                "Ошибка: Не удалось определить ID заявки для удаления.",
                keyboard=keyboards.get_start_keyboard(),
            )
            return

        ticket: Optional[Dict[str, Any]] = await self.db_handler.get_ticket(ticket_id)
        if not ticket or ticket["user_id"] != user_id:
            logger.warning(
                f"User {user_id} tried prompt_ticket_deletion for "
                f"invalid/unauthorized ticket {ticket_id}"
            )
            await message.answer(
                config.ERROR_TICKET_NOT_FOUND,
                keyboard=keyboards.get_start_keyboard(),
            )
            self.form_handler.clear_user_state(user_id, "ticket_to_delete")
            return

        self.form_handler.set_user_state(user_id, "ticket_to_delete", ticket_id)

        await message.answer(
            f"Вы уверены, что хотите удалить заявку {ticket_id}? "
            f"Это действие нельзя отменить.",
            keyboard=keyboards.get_delete_confirm_keyboard(ticket_id),
        )

    async def delete_ticket_prompt_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        try:
            payload: Dict[str, Any] = json.loads(message.payload or {})
            ticket_id: Optional[str] = payload.get("ticket_id")
        except json.JSONDecodeError:
            logger.warning(
                f"Invalid JSON payload for delete_prompt from user {user_id}: {message.payload}"
            )
            ticket_id = None

        if not ticket_id:
            logger.warning(
                f"Delete prompt command from user {user_id} without ticket_id."
            )
            last_viewed = self.form_handler.get_user_state(
                user_id, "last_viewed_ticket"
            )
            if last_viewed:
                logger.info(
                    f"Attempting delete prompt for last viewed ticket: {last_viewed}"
                )
                await self.prompt_ticket_deletion(message, last_viewed)
            else:
                await message.answer(
                    "Не удалось определить, какую заявку удалить. Пожалуйста, выберите ее из списка.",
                    keyboard=keyboards.get_start_keyboard(),
                )
            return

        await self.prompt_ticket_deletion(message, ticket_id)

    async def delete_ticket_confirm_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        payload_ticket_id: Optional[str] = None

        if message.payload:
            try:
                payload: Dict[str, Any] = json.loads(message.payload)
                payload_ticket_id = payload.get("ticket_id")
            except json.JSONDecodeError:
                logger.error(
                    f"Invalid payload format for delete confirm from "
                    f"user {user_id}: {message.payload}"
                )
                payload_ticket_id = None

        trigger_id = payload_ticket_id

        ticket_id_from_state: Optional[str] = self.form_handler.get_user_state(
            user_id, "ticket_to_delete"
        )
        logger.info(
            f"Confirm delete. Trigger ID: {trigger_id}, State ID: {ticket_id_from_state}, User: {user_id}"
        )

        if not ticket_id_from_state or (
            trigger_id and trigger_id != ticket_id_from_state
        ):
            logger.warning(
                f"Delete confirm mismatch or missing state. Trigger: {trigger_id}, State: {ticket_id_from_state}, User: {user_id}"
            )
            await message.answer(
                config.ERROR_DELETE_PENDING_NOT_FOUND,
                keyboard=keyboards.get_start_keyboard(),
            )
            self.form_handler.clear_user_state(user_id, "ticket_to_delete")
            return

        ticket_id_to_delete: str = ticket_id_from_state
        success: bool = await self.form_handler.delete_ticket(
            user_id, ticket_id_to_delete
        )

        self.form_handler.clear_user_state(user_id, "ticket_to_delete")

        if success:
            await message.answer(
                f"Заявка {ticket_id_to_delete} успешно удалена.",
                keyboard=keyboards.get_start_keyboard(),
            )
            await self.notify_admins_about_deleted_ticket(ticket_id_to_delete, user_id)
        else:
            await message.answer(
                config.ERROR_TICKET_DELETION,
                keyboard=keyboards.get_start_keyboard(),
            )

    async def cancel_action_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        logger.info(f"Cancel action command received from user {user_id}")
        self.form_handler.clear_user_state(user_id, "ticket_to_delete")
        await message.answer(
            "Действие отменено.", keyboard=keyboards.get_start_keyboard()
        )

    async def form_message_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        answer: str = message.text
        logger.debug(f"Form message received from user {user_id}: '{answer[:50]}...'")

        processed_result: str = await self.form_handler.process_answer(user_id, answer)

        if processed_result == "validation_error":
            error_msg: Optional[str] = self.form_handler.get_validation_error(user_id)
            current_question: str = self.form_handler.get_current_question(user_id)
            response_msg = f"{error_msg or 'Ошибка валидации.'}\n\n{current_question}"
            await message.answer(response_msg, keyboard=keyboards.get_form_keyboard())
        elif processed_result == "next_question":
            next_question: str = self.form_handler.get_current_question(user_id)
            await message.answer(next_question, keyboard=keyboards.get_form_keyboard())
        elif processed_result == "form_complete":
            await message.answer(
                config.FORM_ALL_FIELDS_COMPLETE_MESSAGE,
                keyboard=keyboards.get_submit_keyboard(),
            )
        elif processed_result == "not_filling":
            logger.debug(
                f"User {user_id} sent text but is not filling form. Routing to default handler."
            )
            await self.default_handler(message)
        else:
            logger.error(
                f"Unexpected state '{processed_result}' after processing answer for user {user_id}."
            )
            self.form_handler.cancel_form(user_id)
            await message.answer(
                config.ERROR_GENERIC, keyboard=keyboards.get_start_keyboard()
            )

    async def _handle_numeric_input(self, message: Message) -> bool:
        user_id: int = message.from_id
        text: str = message.text.strip()
        if text.isdigit():
            try:
                ticket_index: int = int(text) - 1
                user_tickets: Optional[List[str]] = self.form_handler.user_tickets.get(
                    user_id
                )
                if user_tickets and 0 <= ticket_index < len(user_tickets):
                    ticket_id: str = user_tickets[ticket_index]
                    logger.info(
                        f"User {user_id} entered number {text}, interpreted as ticket index {ticket_index}, mapping to ticket ID {ticket_id}"
                    )
                    await self.show_ticket_details(message, ticket_id)
                    return True
                else:
                    logger.info(
                        f"User {user_id} entered number {text}, but it's out of range for their ticket list or list is empty/missing."
                    )
            except ValueError:
                logger.warning(
                    f"Could not parse '{text}' as integer for user {user_id} despite isdigit() being true."
                )
            except Exception as e:
                logger.error(f"Error in _handle_numeric_input for user {user_id}: {e}")
        return False

    async def _handle_delete_command(self, message: Message) -> bool:
        user_id: int = message.from_id
        text: str = message.text.strip().lower()
        ticket_to_delete: Optional[str] = self.form_handler.get_user_state(
            user_id, "ticket_to_delete"
        )

        if not ticket_to_delete:
            return False

        if text in config.CONFIRM_DELETE_PHRASES:
            logger.info(
                f"User {user_id} confirmed deletion for ticket {ticket_to_delete} via text: '{text}'"
            )
            await self.delete_ticket_confirm_handler(message)
            return True
        elif text in config.CANCEL_PHRASES:
            logger.info(
                f"User {user_id} canceled deletion for ticket {ticket_to_delete} via text: '{text}'"
            )
            await self.cancel_action_handler(message)
            return True

        return False

    async def delete_request_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        logger.info(f"Delete request command received from user {user_id}")
        await self.list_tickets_handler(message)

    async def default_handler(self, message: Message) -> None:
        user_id: int = message.from_id
        text: str = message.text.strip()
        logger.info(
            f"Default handler received message from user {user_id}: '{text[:50]}...'"
        )

        if user_id in self.form_handler.user_forms:
            logger.debug(
                f"User {user_id} is filling form, ignoring default handler logic."
            )
            await self.form_message_handler(message)
            return

        if user_id in self.form_handler.user_tickets:
            if await self._handle_numeric_input(message):
                return

        if self.form_handler.get_user_state(user_id, "ticket_to_delete"):
            if await self._handle_delete_command(message):
                return

        last_viewed: Optional[str] = self.form_handler.get_user_state(
            user_id, "last_viewed_ticket"
        )
        if last_viewed and text.lower() == "удалить заявку":
            logger.info(
                f"User {user_id} sent 'Удалить заявку' text for last viewed ticket {last_viewed}. Prompting deletion."
            )
            await self.prompt_ticket_deletion(message, last_viewed)
            return

        logger.info(
            f"Message '{text[:50]}...' from user {user_id} did not match any known command or pattern."
        )
        await message.answer(
            config.UNKNOWN_COMMAND_MESSAGE, keyboard=keyboards.get_start_keyboard()
        )

    async def show_ticket_details(self, message: Message, ticket_id: str) -> None:
        user_id: int = message.from_id
        logger.debug(
            f"Attempting to show details for ticket {ticket_id} for user {user_id}"
        )

        ticket: Optional[Dict[str, Any]] = await self.db_handler.get_ticket(ticket_id)

        if not ticket or ticket.get("user_id") != user_id:
            logger.warning(
                f"User {user_id} failed to view ticket {ticket_id} "
                f"via show_ticket_details (not found or unauthorized)."
            )
            await message.answer(
                config.ERROR_TICKET_NOT_FOUND,
                keyboard=keyboards.get_start_keyboard(),
            )
            return

        form_data: Dict[str, Any] = ticket.get("form_data", {})
        ticket_info: str = f"Информация о заявке {ticket_id}:\n\n"
        for field, value in form_data.items():
            ticket_info += f"{field}: {value}\n"

        try:
            created_at_dt: datetime = datetime.fromisoformat(ticket["created_at"])
            ticket_info += (
                f"\nДата создания: {created_at_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
        except (TypeError, ValueError, KeyError) as e:
            logger.error(
                f"Error parsing created_at from ticket data: {ticket}. Error: {e}"
            )
            ticket_info += "\nДата создания: Ошибка отображения\n"

        self.form_handler.set_user_state(user_id, "last_viewed_ticket", ticket_id)

        await message.answer(
            ticket_info,
            keyboard=keyboards.get_ticket_detail_keyboard(ticket_id),
        )

    def register_handlers(self) -> None:
        logger.info("Registering handlers...")

        self.bot.on.message(
            self.from_users_or_other_chats_rule,
            PayloadRule({"command": "start_form"}),
        )(self.form_start_handler)
        self.bot.on.message(
            self.from_users_or_other_chats_rule,
            PayloadRule({"command": "cancel_form"}),
        )(self.cancel_form_handler)
        self.bot.on.message(
            self.from_users_or_other_chats_rule,
            PayloadRule({"command": "submit_form"}),
        )(self.submit_form_handler)
        self.bot.on.message(
            self.from_users_or_other_chats_rule,
            PayloadRule({"command": "list_tickets"}),
        )(self.list_tickets_handler)
        self.bot.on.message(
            self.from_users_or_other_chats_rule,
            PayloadRule({"command": "view_ticket"}),
        )(self.view_ticket_handler)
        self.bot.on.message(
            self.from_users_or_other_chats_rule,
            PayloadRule({"command": "delete_ticket_prompt"}),
        )(self.delete_ticket_prompt_handler)
        self.bot.on.message(
            self.from_users_or_other_chats_rule,
            PayloadRule({"command": "delete_ticket_confirm"}),
        )(self.delete_ticket_confirm_handler)
        self.bot.on.message(
            self.from_users_or_other_chats_rule,
            PayloadRule({"command": "cancel_action"}),
        )(self.cancel_action_handler)

        self.bot.on.message(
            self.from_users_or_other_chats_rule,
            text=["Начать", "start", "/start"],
        )(self.start_handler)

        self.bot.on.message(
            self.is_filling_form_rule,
            self.from_users_or_other_chats_rule,
            ~PayloadRule({"command": "cancel_form"}),
        )(self.form_message_handler)

        self.bot.on.message(
            ~self.is_filling_form_rule,
            self.from_users_or_other_chats_rule,
        )(self.default_handler)

        async def ignore_chat_handler(message: Message) -> NoReturn:
            logger.debug(f"Ignoring message in notification chat {message.peer_id}")

        self.bot.on.message(self.ignore_notification_chat_rule)(ignore_chat_handler)

        self.bot.on.message(
            PayloadRule({"command": "delete_request"}),
            self.from_users_or_other_chats_rule,
        )(self.delete_request_handler)

        logger.info("Handlers registered.")

    async def notify_admins_about_new_ticket(
        self, ticket_id: str, user_id: int, form_data: Dict[str, str]
    ) -> None:
        if not config.NOTIFICATION_CHAT_ID:
            logger.warning(
                "notify_admins_about_new_ticket: NOTIFICATION_CHAT_ID not configured."
            )
            return
        try:
            form_summary: str = "\n".join([f"> {k}: {v}" for k, v in form_data.items()])
            user_link: str = f"vk.com/id{user_id}"
            message_text: str = config.NEW_TICKET_NOTIFICATION_TEMPLATE.format(
                ticket_id=ticket_id,
                user_id=user_id,
                user_link=user_link,
                form_summary=form_summary,
            )
            await self.bot.api.messages.send(
                peer_id=config.NOTIFICATION_CHAT_ID,
                message=message_text,
                random_id=0,
            )
            logger.info(
                f"New ticket notification sent to chat "
                f"{config.NOTIFICATION_CHAT_ID} for ticket {ticket_id}"
            )
        except Exception as e:
            logger.error(
                f"Error sending new ticket notification to chat "
                f"{config.NOTIFICATION_CHAT_ID} for ticket "
                f"{ticket_id}: {e}"
            )

    async def notify_admins_about_deleted_ticket(
        self, ticket_id: str, user_id: int
    ) -> None:
        if not config.NOTIFICATION_CHAT_ID:
            logger.warning(
                "notify_admins_about_deleted_ticket: "
                "NOTIFICATION_CHAT_ID not configured."
            )
            return
        try:
            user_link: str = f"vk.com/id{user_id}"
            message_text: str = config.TICKET_DELETED_NOTIFICATION_TEMPLATE.format(
                ticket_id=ticket_id, user_id=user_id, user_link=user_link
            )
            await self.bot.api.messages.send(
                peer_id=config.NOTIFICATION_CHAT_ID,
                message=message_text,
                random_id=0,
            )
            logger.info(
                f"Deletion notification sent to chat "
                f"{config.NOTIFICATION_CHAT_ID} for ticket {ticket_id}"
            )
        except Exception as e:
            logger.error(
                f"Error sending deletion notification to chat "
                f"{config.NOTIFICATION_CHAT_ID} for ticket "
                f"{ticket_id}: {e}"
            )
