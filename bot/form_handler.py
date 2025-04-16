import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from . import config
from .db_handler import DatabaseHandler

logger = logging.getLogger(__name__)


class FormHandler:
    """
    Класс для управления процессом заполнения формы пользователями.
    Отслеживает состояние заполнения формы для каждого пользователя,
    сохраняет ответы и создает заявки по завершении.
    """

    def __init__(self, form_fields: List[str], db_handler: DatabaseHandler):
        """
        Инициализация обработчика формы.

        Args:
            form_fields: Список названий полей формы, которые нужно заполнить
            db_handler: Экземпляр DatabaseHandler для работы с БД
        """
        self.form_fields = form_fields
        self.user_forms: Dict[int, Dict] = {}
        self.user_tickets: Dict[int, List[str]] = {}
        self.user_states: Dict[int, Dict] = {}
        self.db_handler = db_handler

    def start_form(self, user_id: int) -> str:
        """
        Инициализация новой формы для пользователя.
        Создает пустую форму и возвращает первый вопрос.

        Args:
            user_id: ID пользователя ВКонтакте

        Returns:
            str: Текст первого вопроса формы
        """
        self.user_forms[user_id] = {
            "current_field": 0,
            "data": {field: "" for field in self.form_fields},
            "started_at": datetime.now().isoformat(),
        }
        logger.info(f"Starting form for user {user_id}")
        return self.get_current_question(user_id)

    def get_current_question(self, user_id: int) -> str:
        """
        Получение текущего вопроса для пользователя.

        Args:
            user_id: ID пользователя ВКонтакте

        Returns:
            str: Текст вопроса или сообщение о статусе формы
        """
        if user_id not in self.user_forms:
            logger.warning(
                f"get_current_question called for user {user_id} without active form."
            )
            return "Пожалуйста, сначала начните заполнение формы."

        form = self.user_forms[user_id]
        current_field_idx = form["current_field"]

        if current_field_idx >= len(self.form_fields):
            logger.debug(f"Form complete for user {user_id}, asking to submit.")
            return config.FORM_ALL_FIELDS_COMPLETE_MESSAGE

        question = f"Пожалуйста, укажите: {self.form_fields[current_field_idx]}"
        logger.debug(f"Asking question for user {user_id}: '{question}'")
        return question

    def validate_field(self, field_name: str, value: str) -> Tuple[bool, str]:
        """
        Валидация ответа пользователя в зависимости от типа поля.

        Args:
            field_name: Название поля для валидации
            value: Введенное пользователем значение

        Returns:
            tuple: (bool, str) - результат валидации (успех/неуспех)
                   и сообщение об ошибке (если есть)
        """
        value = value.strip()
        if not value:
            return False, config.ERROR_FIELD_EMPTY

        field_lower = field_name.lower()
        error_msg = ""

        if "имя" in field_lower and len(value) < 2:
            error_msg = config.ERROR_NAME_TOO_SHORT
        elif ("почта" in field_lower or "email" in field_lower) and not re.match(
            r"^[\w\\.-]+@[\w\\.-]+\\.\\w+$", value
        ):
            error_msg = config.ERROR_INVALID_EMAIL
        elif "телефон" in field_lower:
            cleaned_phone = re.sub(r"\\D", "", value)
            if not (10 <= len(cleaned_phone) <= 15):
                error_msg = config.ERROR_INVALID_PHONE
        elif ("компани" in field_lower or "организац" in field_lower) and len(
            value
        ) < 3:
            error_msg = config.ERROR_COMPANY_NAME_TOO_SHORT
        elif "описание" in field_lower and len(value) < 10:
            error_msg = config.ERROR_DESCRIPTION_TOO_SHORT

        if error_msg:
            logger.debug(
                f"Validation failed for field '{field_name}' with value "
                f"'{value}': {error_msg}"
            )
            return False, error_msg

        logger.debug(
            f"Validation succeeded for field '{field_name}' with value '{value}'"
        )
        return True, ""

    def process_answer(self, user_id: int, answer: str) -> str:
        """
        Обработка ответа пользователя и переход к следующему вопросу.

        Args:
            user_id: ID пользователя ВКонтакте
            answer: Текст ответа пользователя

        Returns:
            str: Текст следующего вопроса или сообщение о завершении формы
        """
        if user_id not in self.user_forms:
            logger.warning(
                f"process_answer called for user {user_id} without active form."
            )
            return "Пожалуйста, сначала начните заполнение формы."

        form = self.user_forms[user_id]
        current_field_idx = form["current_field"]

        if current_field_idx >= len(self.form_fields):
            logger.debug(
                f"Form already complete for user {user_id} when "
                f"process_answer was called."
            )
            return config.FORM_ALL_FIELDS_COMPLETE_MESSAGE

        current_field = self.form_fields[current_field_idx]
        is_valid, error_message = self.validate_field(current_field, answer)

        if not is_valid:
            return f"{error_message}\n\n{self.get_current_question(user_id)}"

        form["data"][current_field] = answer.strip()

        form["current_field"] += 1
        logger.info(
            f"Processed answer for field '{current_field}' for user "
            f"{user_id}. Moving to field {form['current_field']}."
        )

        return self.get_current_question(user_id)

    def cancel_form(self, user_id: int) -> None:
        """
        Отмена процесса заполнения формы.
        Удаляет все данные текущей формы пользователя.

        Args:
            user_id: ID пользователя ВКонтакте
        """
        if user_id in self.user_forms:
            del self.user_forms[user_id]
            logger.info(f"Form cancelled and cleared for user {user_id}")
        else:
            logger.debug(
                f"cancel_form called for user {user_id} but no active form found."
            )

    def is_form_complete(self, user_id: int) -> bool:
        """
        Проверка, заполнены ли все поля формы.

        Args:
            user_id: ID пользователя ВКонтакте

        Returns:
            bool: True, если форма полностью заполнена, иначе False
        """
        if user_id not in self.user_forms:
            return False

        form = self.user_forms[user_id]
        return form["current_field"] >= len(self.form_fields)

    async def create_ticket(self, user_id: int) -> Optional[str]:
        """
        Асинхронное создание заявки в БД после завершения формы.

        Args:
            user_id: ID пользователя ВКонтакте

        Returns:
            str или None: Идентификатор созданной заявки или None,
                          если не удалось создать заявку
        """
        if not self.is_form_complete(user_id):
            logger.warning(
                f"create_ticket called for user {user_id} but form is not complete."
            )
            return None

        form_data = self.user_forms[user_id]["data"]
        ticket_id = f"{user_id}_{int(datetime.now().timestamp())}"

        success = await self.db_handler.create_ticket(ticket_id, user_id, form_data)

        if success:
            logger.info(
                f"Ticket {ticket_id} successfully created in DB for user "
                f"{user_id}. Clearing form data."
            )
            del self.user_forms[user_id]
            return ticket_id
        else:
            logger.error(
                f"Failed to create ticket {ticket_id} in DB for user {user_id}."
            )
            return None

    async def delete_ticket(self, user_id: int, ticket_id: str) -> bool:
        """
        Асинхронное удаление заявки пользователя из БД и кеша.

        Args:
            user_id: ID пользователя ВКонтакте
            ticket_id: Идентификатор заявки для удаления

        Returns:
            bool: True если заявка успешно удалена, False в случае ошибки
        """
        logger.info(f"Attempting to delete ticket {ticket_id} for user {user_id}")

        user_id_int = int(user_id)
        ticket_id_str = str(ticket_id)

        success = await self.db_handler.delete_ticket(ticket_id_str, user_id_int)
        logger.info(f"DB deletion result for ticket {ticket_id}: {success}")

        if success and user_id_int in self.user_tickets:
            if ticket_id_str in self.user_tickets[user_id_int]:
                try:
                    self.user_tickets[user_id_int].remove(ticket_id_str)
                    logger.debug(
                        f"Removed ticket {ticket_id} from user_tickets cache "
                        f"for user {user_id}"
                    )
                except ValueError:
                    logger.warning(
                        f"Ticket {ticket_id} was already removed from "
                        f"user_tickets cache for user {user_id}"
                    )
            if not self.user_tickets[user_id_int]:
                del self.user_tickets[user_id_int]
                logger.debug(f"Cleared empty user_tickets cache for user {user_id}")

        return success

    def set_user_state(self, user_id: int, key: str, value: Any):
        """Устанавливает состояние для пользователя."""
        if user_id not in self.user_states:
            self.user_states[user_id] = {}
        self.user_states[user_id][key] = value
        logger.debug(f"Set state for user {user_id}: {key}={value}")

    def get_user_state(self, user_id: int, key: str, default: Any = None) -> Any:
        """Получает состояние пользователя."""
        return self.user_states.get(user_id, {}).get(key, default)

    def clear_user_state(self, user_id: int, key: Optional[str] = None):
        """Очищает конкретное состояние или все состояния пользователя."""
        if user_id in self.user_states:
            if key:
                if key in self.user_states[user_id]:
                    del self.user_states[user_id][key]
                    logger.debug(f"Cleared state '{key}' for user {user_id}")
                if not self.user_states[user_id]:
                    del self.user_states[user_id]
                    logger.debug(f"Cleared all states for user {user_id}")
            else:
                del self.user_states[user_id]
                logger.debug(f"Cleared all states for user {user_id}")
