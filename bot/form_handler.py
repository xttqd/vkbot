from typing import Dict, List, Optional
import json
import os
from datetime import datetime
from db_handler import DatabaseHandler

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
        
        # Сохраняем ответ пользователя в соответствующее поле
        current_field = self.form_fields[current_field_idx]
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