import re
import logging
import uuid
from typing import Dict, List, Optional, Tuple, Any, TypedDict
from datetime import datetime
from . import config
from .db_handler import DatabaseHandler

logger = logging.getLogger(__name__)


class UserFormData(TypedDict):
    current_field: int
    data: Dict[str, str]
    started_at: str
    validation_error: Optional[str]


class FormHandler:
    form_fields_config: List[Dict[str, Any]]
    form_fields: List[str]
    user_forms: Dict[int, UserFormData]
    user_tickets: Dict[int, List[str]]
    user_states: Dict[int, Dict[str, Any]]
    db_handler: DatabaseHandler

    def __init__(
        self, form_fields_config: List[Dict[str, Any]], db_handler: DatabaseHandler
    ):
        self.form_fields_config = form_fields_config
        self.form_fields = [field["name"] for field in form_fields_config]
        self.user_forms = {}
        self.user_tickets = {}
        self.user_states = {}
        self.db_handler = db_handler

    def start_form(self, user_id: int) -> str:
        self.user_forms[user_id] = {
            "current_field": 0,
            "data": {field: "" for field in self.form_fields},
            "started_at": datetime.now().isoformat(),
            "validation_error": None,
        }
        logger.info(f"Starting form for user {user_id}")
        return self.get_current_question(user_id)

    def get_current_question(self, user_id: int) -> str:
        if user_id not in self.user_forms:
            logger.warning(
                f"get_current_question called for user {user_id} without active form."
            )
            return "Пожалуйста, сначала начните заполнение формы."

        form: UserFormData = self.user_forms[user_id]
        current_field_idx: int = form["current_field"]

        if current_field_idx >= len(self.form_fields):
            logger.debug(f"Form complete for user {user_id}, asking to submit.")
            return config.FORM_ALL_FIELDS_COMPLETE_MESSAGE

        question: str = f"Пожалуйста, укажите: {self.form_fields[current_field_idx]}"
        logger.debug(f"Asking question for user {user_id}: '{question}'")
        return question

    def validate_field(self, field_name: str, value: str) -> Tuple[bool, str]:
        value = value.strip()
        if not value:
            field_config = next(
                (f for f in self.form_fields_config if f["name"] == field_name), None
            )
            if field_config and field_config.get("validation") is None:
                logger.debug(
                    f"Validation skipped for optional field '{field_name}' with empty value."
                )
                return True, ""
            else:
                return False, config.ERROR_FIELD_EMPTY

        field_config = next(
            (f for f in self.form_fields_config if f["name"] == field_name), None
        )

        if not field_config or not field_config.get("validation"):
            logger.debug(
                f"Validation succeeded (no specific rules) for field '{field_name}'"
            )
            return True, ""

        rules: Dict[str, Any] = field_config["validation"]
        validation_type: Optional[str] = rules.get("type")
        error_msg: str = rules.get("error", "Недопустимое значение.")

        is_valid = True

        try:
            if validation_type == "min_length":
                min_len: Optional[int] = rules.get("value")
                if min_len is None or not isinstance(min_len, int):
                    logger.error(
                        f"Invalid config for min_length on '{field_name}': missing or invalid 'value'."
                    )
                    is_valid = False
                    error_msg = "Ошибка конфигурации валидации."
                elif len(value) < min_len:
                    is_valid = False

            elif validation_type == "regex":
                pattern: Optional[str] = rules.get("pattern")
                if not pattern or not isinstance(pattern, str):
                    logger.error(
                        f"Invalid config for regex on '{field_name}': missing or invalid 'pattern'."
                    )
                    is_valid = False
                    error_msg = "Ошибка конфигурации валидации."
                elif not re.match(pattern, value):
                    is_valid = False

            elif validation_type == "phone":
                cleaned_phone = re.sub(r"\D", "", value)
                if not (len(re.sub(r"\D", "", cleaned_phone)) >= 10):
                    is_valid = False

            else:
                logger.warning(
                    f"Unknown or no validation type specified ('{validation_type}') for field '{field_name}' - treating as valid."
                )
                is_valid = True

        except Exception as e:
            logger.error(
                f"Exception during validation for field '{field_name}' with type '{validation_type}': {e}"
            )
            is_valid = False
            error_msg = "Произошла внутренняя ошибка при проверке поля."

        if not is_valid:
            logger.debug(
                f"Validation failed for field '{field_name}' with value "
                f"'{value}': {error_msg}"
            )
            return False, error_msg
        else:
            logger.debug(
                f"Validation succeeded for field '{field_name}' with value '{value}'"
            )
            return True, ""

    def get_validation_error(self, user_id: int) -> Optional[str]:
        return self.user_forms[user_id].get("validation_error")

    async def process_answer(self, user_id: int, answer: str) -> str:
        if user_id not in self.user_forms:
            logger.warning(
                f"process_answer called for user {user_id} without active form."
            )
            return "not_filling"

        form: UserFormData = self.user_forms[user_id]
        current_field_idx: int = form["current_field"]

        form["validation_error"] = None

        if current_field_idx >= len(self.form_fields):
            logger.debug(
                f"Form already complete for user {user_id} when "
                f"process_answer was called."
            )
            return "form_complete"

        current_field: str = self.form_fields[current_field_idx]
        is_valid, error_message = self.validate_field(current_field, answer)

        if not is_valid:
            form["validation_error"] = error_message
            return "validation_error"

        form["data"][current_field] = answer.strip()

        form["current_field"] += 1
        logger.info(
            f"Processed answer for field '{current_field}' for user "
            f"{user_id}. Moving to field index {form['current_field']}."
        )

        if form["current_field"] >= len(self.form_fields):
            return "form_complete"
        else:
            return "next_question"

    def cancel_form(self, user_id: int) -> None:
        if user_id in self.user_forms:
            del self.user_forms[user_id]
            logger.info(f"Form cancelled and cleared for user {user_id}")
        else:
            logger.debug(
                f"cancel_form called for user {user_id} but no active form found."
            )

    def is_form_complete(self, user_id: int) -> bool:
        if user_id not in self.user_forms:
            return False

        form: UserFormData = self.user_forms[user_id]
        return form["current_field"] >= len(self.form_fields)

    async def create_ticket(self, user_id: int) -> Optional[str]:
        if not self.is_form_complete(user_id):
            logger.warning(
                f"Attempted to create ticket for user {user_id} but form is not complete."
            )
            return None

        form_data: Dict[str, str] = self.user_forms[user_id]["data"]

        ticket_id: str = str(uuid.uuid4())[:8]

        success: bool = await self.db_handler.create_ticket(
            ticket_id=ticket_id, user_id=user_id, form_data=form_data
        )

        if success:
            logger.info(f"Ticket {ticket_id} created in DB for user {user_id}.")
            self.cancel_form(user_id)
            return ticket_id
        else:
            logger.error(
                f"Failed to create ticket in DB for user {user_id} after form completion."
            )
            return None

    async def delete_ticket(self, user_id: int, ticket_id: str) -> bool:
        logger.info(f"Attempting to delete ticket {ticket_id} for user {user_id}")

        success: bool = await self.db_handler.delete_ticket(ticket_id, user_id)
        logger.info(f"DB deletion result for ticket {ticket_id}: {success}")

        if success and user_id in self.user_tickets:
            if ticket_id in self.user_tickets[user_id]:
                try:
                    self.user_tickets[user_id].remove(ticket_id)
                    logger.debug(
                        f"Removed ticket {ticket_id} from user_tickets cache "
                        f"for user {user_id}"
                    )
                except ValueError:
                    logger.warning(
                        f"Ticket {ticket_id} was already removed from "
                        f"user_tickets cache for user {user_id}"
                    )
            if not self.user_tickets[user_id]:
                del self.user_tickets[user_id]
                logger.debug(f"Cleared empty user_tickets cache for user {user_id}")

        return success

    def set_user_state(self, user_id: int, key: str, value: Any) -> None:
        if user_id not in self.user_states:
            self.user_states[user_id] = {}
        self.user_states[user_id][key] = value
        logger.debug(f"Set state for user {user_id}: {key} = {value}")

    def get_user_state(self, user_id: int, key: str, default: Any = None) -> Any:
        return self.user_states.get(user_id, {}).get(key, default)

    def clear_user_state(self, user_id: int, key: Optional[str] = None) -> None:
        if user_id in self.user_states:
            if key:
                if key in self.user_states[user_id]:
                    del self.user_states[user_id][key]
                    logger.debug(f"Cleared state key '{key}' for user {user_id}")
            else:
                del self.user_states[user_id]
                logger.debug(f"Cleared all states for user {user_id}")
