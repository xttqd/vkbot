from vkbottle import Keyboard, KeyboardButtonColor, Text
import logging

logger = logging.getLogger(__name__)


def get_start_keyboard() -> str:
    """Создает стартовую клавиатуру."""
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
    """Создает клавиатуру для процесса заполнения формы."""
    keyboard = Keyboard(inline=False)
    keyboard.add(
        Text("Отмена", payload={"command": "cancel_form"}),
        color=KeyboardButtonColor.NEGATIVE,
    )
    return keyboard.get_json()


def get_submit_keyboard() -> str:
    """Создает клавиатуру для отправки заполненной формы."""
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


def get_ticket_list_keyboard(tickets: list) -> str:
    """Создает клавиатуру для списка заявок с кнопками выбора (по номеру)."""
    keyboard = Keyboard(inline=False)
    max_buttons = 5
    for i, ticket in enumerate(tickets[:max_buttons], 1):
        button_text = str(i)
        keyboard.add(
            Text(
                button_text,
                payload={"command": "view_ticket", "ticket_id": ticket["ticket_id"]},
            ),
            color=KeyboardButtonColor.SECONDARY,
        )
        if len(tickets[:max_buttons]) > 1 and i < len(tickets[:max_buttons]):
            keyboard.row()

    keyboard.row()
    keyboard.add(
        Text("Заполнить заявку", payload={"command": "start_form"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    return keyboard.get_json()


def get_ticket_detail_keyboard(ticket_id: str) -> str:
    """Создает клавиатуру для просмотра деталей заявки."""
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
    """Создает клавиатуру для подтверждения удаления заявки."""
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
