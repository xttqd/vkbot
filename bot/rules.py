import logging
from vkbottle.bot import Message
from vkbottle.dispatch.rules import ABCRule
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .form_handler import FormHandler

logger = logging.getLogger(__name__)


class IsFillingFormRule(ABCRule):
    def __init__(self, form_handler: "FormHandler"):
        self.form_handler = form_handler

    async def check(self, message: Message) -> bool:
        is_filling = message.from_id in self.form_handler.user_forms
        logger.debug(
            f"Checking IsFillingFormRule for user {message.from_id}: {is_filling}"
        )
        return is_filling
