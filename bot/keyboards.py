from vkbottle import Keyboard, KeyboardButtonColor, Text
import logging
from typing import List, Dict, Any
from . import config

logger = logging.getLogger(__name__)


def get_start_keyboard() -> str:
    keyboard = Keyboard(inline=False)
    keyboard.add(
        Text("Заполнить заявку", payload={"command": "start_form"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    keyboard.add(
        Text("Мои заявки", payload={"command": "list_tickets"}),
        color=KeyboardButtonColor.SECONDARY,
    )
    return keyboard.get_json()


def get_form_keyboard() -> str:
    keyboard = Keyboard(inline=False)
    keyboard.add(
        Text("Отмена", payload={"command": "cancel_form"}),
        color=KeyboardButtonColor.NEGATIVE,
    )
    return keyboard.get_json()


def get_submit_keyboard() -> str:
    keyboard = Keyboard(inline=False)
    keyboard.add(
        Text("Отправить", payload={"command": "submit_form"}),
        color=KeyboardButtonColor.POSITIVE,
    )
    keyboard.add(
        Text("Отмена", payload={"command": "cancel_form"}),
        color=KeyboardButtonColor.NEGATIVE,
    )
    return keyboard.get_json()


def get_ticket_list_keyboard(tickets: List[Dict[str, Any]]) -> str:
    keyboard = Keyboard(inline=False)
    displayed_tickets = tickets[: config.MAX_TICKET_LIST_BUTTONS]

    for i, ticket in enumerate(displayed_tickets, 1):
        ticket_id = ticket.get("ticket_id")
        if not ticket_id:
            logger.warning(
                f"Ticket ID missing for ticket at index {i - 1} in list: {ticket}"
            )
            continue

        button_text = str(i)
        keyboard.add(
            Text(
                button_text,
                payload={"command": "view_ticket", "ticket_id": str(ticket_id)},
            ),
            color=KeyboardButtonColor.SECONDARY,
        )
        if keyboard.buttons and i < len(displayed_tickets):
            keyboard.row()

    if keyboard.buttons:
        keyboard.row()

    keyboard.add(
        Text("Заполнить заявку", payload={"command": "start_form"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    return keyboard.get_json()


def get_ticket_detail_keyboard(ticket_id: str) -> str:
    logger.debug(f"Creating detail keyboard for ticket: {ticket_id}")
    keyboard = Keyboard(inline=False)
    keyboard.add(
        Text(
            "Удалить заявку",
            payload={"command": "delete_ticket_prompt", "ticket_id": ticket_id},
        ),
        color=KeyboardButtonColor.NEGATIVE,
    )
    keyboard.row()
    keyboard.add(
        Text("Мои заявки", payload={"command": "list_tickets"}),
        color=KeyboardButtonColor.SECONDARY,
    )
    keyboard.add(
        Text("Заполнить заявку", payload={"command": "start_form"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    return keyboard.get_json()


def get_delete_confirm_keyboard(ticket_id: str) -> str:
    keyboard = Keyboard(inline=False)
    keyboard.add(
        Text(
            "Подтвердить удаление",
            payload={"command": "delete_ticket_confirm", "ticket_id": ticket_id},
        ),
        color=KeyboardButtonColor.NEGATIVE,
    )
    keyboard.add(
        Text("Отмена", payload={"command": "cancel_action"}),
        color=KeyboardButtonColor.SECONDARY,
    )
    return keyboard.get_json()
