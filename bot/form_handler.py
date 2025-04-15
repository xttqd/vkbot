from typing import Dict, List, Optional, Tuple
from datetime import datetime
# Используем относительный импорт для config, так как он в том же пакете
from . import config 
from vkbottle.bot import Message
from .db_handler import DatabaseHandler

# ========================================================
# КЛАСС ОБРАБОТЧИКА ФОРМЫ
# ========================================================

class FormHandler:
    """
    Класс для управления процессом заполнения формы пользователями.
    Отслеживает состояние заполнения формы для каждого пользователя, сохраняет ответы
    и создает заявки по завершении.
    """
    
    def __init__(self, form_fields: List[str]):
        """
        Инициализация обработчика формы.
        
        Args:
            form_fields: Список названий полей формы, которые нужно заполнить
        """
        self.form_fields = form_fields
        # Словарь для хранения текущих форм пользователей:
        # - ключ: ID пользователя ВКонтакте
        # - значение: словарь с данными формы (текущее поле, собранные данные, дата начала)
        self.user_forms: Dict[int, Dict] = {}
        
        # Словарь для хранения идентификаторов заявок пользователей:
        # - ключ: ID пользователя ВКонтакте
        # - значение: список идентификаторов заявок этого пользователя
        self.user_tickets: Dict[int, List[str]] = {}
        
        # Создаем экземпляр обработчика базы данных для сохранения заявок
        self.db_handler = DatabaseHandler()
    
    # ========================================================
    # МЕТОДЫ УПРАВЛЕНИЯ ФОРМОЙ
    # ========================================================
    
    def start_form(self, user_id: int) -> str:
        """
        Инициализация новой формы для пользователя.
        Создает пустую форму и возвращает первый вопрос.
        
        Args:
            user_id: ID пользователя ВКонтакте
            
        Returns:
            str: Текст первого вопроса формы
        """
        # Создаем структуру данных для формы пользователя
        self.user_forms[user_id] = {
            "current_field": 0,  # Индекс текущего заполняемого поля
            "data": {field: "" for field in self.form_fields},  # Словарь для хранения ответов
            "started_at": datetime.now().isoformat()  # Дата и время начала заполнения
        }
        # Возвращаем первый вопрос
        return self.get_current_question(user_id)
    
    def get_current_question(self, user_id: int) -> str:
        """
        Получение текущего вопроса для пользователя.
        
        Args:
            user_id: ID пользователя ВКонтакте
            
        Returns:
            str: Текст вопроса или сообщение о статусе формы
        """
        # Проверяем, начал ли пользователь заполнение формы
        if user_id not in self.user_forms:
            return "Пожалуйста, сначала начните заполнение формы."
        
        form = self.user_forms[user_id]
        current_field_idx = form["current_field"]
        
        # Проверяем, достигнут ли конец формы
        if current_field_idx >= len(self.form_fields):
            return """На все вопросы получены ответы. Нажмите "Отправить", чтобы создать заявку."""
        
        # Возвращаем текущий вопрос
        return f"Пожалуйста, укажите: {self.form_fields[current_field_idx]}"
    
    def validate_field(self, field_name: str, value: str) -> Tuple[bool, str]:
        """
        Валидация ответа пользователя в зависимости от типа поля.
        
        Args:
            field_name: Название поля для валидации
            value: Введенное пользователем значение
            
        Returns:
            tuple: (bool, str) - результат валидации (успех/неуспех) и сообщение об ошибке (если есть)
        """
        if not value.strip():
            return False, "Поле не может быть пустым. Пожалуйста, укажите значение."
            
        if "имя" in field_name.lower():
            if len(value) < 2:
                return False, "Имя должно содержать минимум 2 символа."
            
        elif "почта" in field_name.lower() or "email" in field_name.lower():
            import re
            # Проверка формата email
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value):
                return False, "Неверный формат электронной почты. Пример: example@mail.ru"
            
        elif "телефон" in field_name.lower():
            import re
            # Удаляем все нецифровые символы для проверки
            cleaned_phone = re.sub(r'\D', '', value)
            # Проверяем, что после удаления нецифровых символов осталось 10-15 цифр
            if not (10 <= len(cleaned_phone) <= 15):
                return False, "Неверный формат номера телефона. Укажите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX"
            
        elif "компани" in field_name.lower() or "организац" in field_name.lower():
            if len(value) < 3:
                return False, "Название компании должно содержать минимум 3 символа."
            
        elif "описание" in field_name.lower():
            if len(value) < 10:
                return False, "Описание должно содержать минимум 10 символов."
                
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
        # Проверяем, начал ли пользователь заполнение формы
        if user_id not in self.user_forms:
            return "Пожалуйста, сначала начните заполнение формы."
        
        form = self.user_forms[user_id]
        current_field_idx = form["current_field"]
        
        # Проверяем, не заполнены ли уже все поля
        if current_field_idx >= len(self.form_fields):
            return """На все вопросы получены ответы. Нажмите "Отправить", чтобы создать заявку."""
        
        # Получаем текущее поле и проводим валидацию
        current_field = self.form_fields[current_field_idx]
        is_valid, error_message = self.validate_field(current_field, answer)
        
        if not is_valid:
            # Если валидация не пройдена, возвращаем сообщение об ошибке
            return f"{error_message}\n\nПожалуйста, укажите: {current_field}"
        
        # Сохраняем ответ пользователя в соответствующее поле
        form["data"][current_field] = answer
        
        # Переходим к следующему полю
        form["current_field"] += 1
        
        # Возвращаем следующий вопрос или сообщение о завершении
        if form["current_field"] >= len(self.form_fields):
            return """На все вопросы получены ответы. Нажмите "Отправить", чтобы создать заявку."""
        else:
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
    
    def is_form_complete(self, user_id: int) -> bool:
        """
        Проверка, заполнены ли все поля формы.
        
        Args:
            user_id: ID пользователя ВКонтакте
            
        Returns:
            bool: True, если форма полностью заполнена, иначе False
        """
        # Проверяем, есть ли форма у пользователя
        if user_id not in self.user_forms:
            return False
        
        form = self.user_forms[user_id]
        # Если индекс текущего поля >= количеству полей, значит форма заполнена
        return form["current_field"] >= len(self.form_fields)
    
    # ========================================================
    # МЕТОДЫ СОЗДАНИЯ ЗАЯВОК
    # ========================================================
    
    def create_ticket(self, user_id: int) -> Optional[str]:
        """
        Создание заявки из заполненной формы и сохранение в базу данных.
        
        Args:
            user_id: ID пользователя ВКонтакте
            
        Returns:
            str или None: Идентификатор созданной заявки или None, если не удалось создать заявку
        """
        # Проверяем, заполнена ли форма полностью
        if not self.is_form_complete(user_id):
            return None
        
        # Получаем собранные данные формы
        form_data = self.user_forms[user_id]["data"]
        # Формируем уникальный идентификатор заявки: ID пользователя + временная метка
        ticket_id = f"{user_id}_{int(datetime.now().timestamp())}"
        
        # Сохраняем заявку в базу данных через обработчик БД
        success = self.db_handler.create_ticket(ticket_id, user_id, form_data)
        
        if success:
            # Если заявка успешно создана, очищаем данные формы
            del self.user_forms[user_id]
            return ticket_id
        else:
            # Если произошла ошибка при сохранении, возвращаем None
            return None
    
    def delete_ticket(self, user_id: int, ticket_id: str) -> bool:
        """
        Удаление заявки пользователя.
        
        Args:
            user_id: ID пользователя ВКонтакте
            ticket_id: Идентификатор заявки для удаления
            
        Returns:
            bool: True если заявка успешно удалена, False в случае ошибки
        """
        print(f"FormHandler.delete_ticket: user_id={user_id} (тип: {type(user_id)}), ticket_id={ticket_id} (тип: {type(ticket_id)})")
        
        # Убеждаемся в правильных типах данных
        user_id_int = int(user_id)
        ticket_id_str = str(ticket_id)
        
        # Проверяем, существует ли заявка и удаляем ее
        success = self.db_handler.delete_ticket(ticket_id_str, user_id_int)
        print(f"FormHandler.delete_ticket: Результат удаления: {success}")
        
        # Если заявка успешно удалена и у нас хранится список заявок пользователя в памяти
        if success and user_id_int in self.user_tickets:
            # Удаляем заявку из списка заявок пользователя в памяти
            if ticket_id_str in self.user_tickets[user_id_int]:
                self.user_tickets[user_id_int].remove(ticket_id_str)
                print(f"FormHandler.delete_ticket: Заявка удалена из кэша пользователя")
        
        return success