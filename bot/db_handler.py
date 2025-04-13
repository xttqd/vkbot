import sqlite3
import json
from datetime import datetime
from typing import Dict, Optional, List, Any
import os

# ========================================================
# КЛАСС ОБРАБОТЧИКА БАЗЫ ДАННЫХ
# ========================================================

class DatabaseHandler:
    """
    Класс для работы с базой данных SQLite.
    Обеспечивает создание, чтение, обновление и удаление заявок.
    """
    
    def __init__(self, db_name: str = "tickets.db"):
        """
        Инициализация обработчика базы данных.
        
        Args:
            db_name: Имя файла базы данных SQLite
        """
        # Определяем путь к базе данных в той же директории, где находится скрипт
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_name)
        
        # Инициализация базы данных (создание таблиц, если их нет)
        self._init_db()
    
    def _init_db(self) -> None:
        """
        Инициализация базы данных и создание таблиц, если они не существуют.
        Создает таблицу tickets для хранения заявок пользователей.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу для тикетов с полями:
        # - ticket_id: уникальный идентификатор заявки (первичный ключ)
        # - user_id: ID пользователя ВКонтакте
        # - created_at: дата и время создания заявки
        # - form_data: данные формы в формате JSON
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            form_data TEXT NOT NULL
        )
        """)
        
        conn.commit()
        conn.close()
    
    # ========================================================
    # ОПЕРАЦИИ С ЗАЯВКАМИ (CRUD)
    # ========================================================
    
    def create_ticket(self, ticket_id: str, user_id: int, form_data: Dict[str, str]) -> bool:
        """
        Создание новой заявки в базе данных.
        
        Args:
            ticket_id: Уникальный идентификатор заявки
            user_id: ID пользователя ВКонтакте
            form_data: Словарь с данными формы
            
        Returns:
            bool: True, если заявка успешно создана, иначе False
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Преобразуем словарь form_data в JSON строку с поддержкой Unicode
            form_data_json = json.dumps(form_data, ensure_ascii=False)
            
            # Добавляем запись в базу данных
            cursor.execute(
                "INSERT INTO tickets (ticket_id, user_id, created_at, form_data) VALUES (?, ?, ?, ?)",
                (ticket_id, user_id, datetime.now().isoformat(), form_data_json)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            # В случае ошибки при создании заявки возвращаем False
            return False
    
    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение заявки по её ID.
        
        Args:
            ticket_id: Идентификатор заявки
            
        Returns:
            Dict или None: Словарь с данными заявки или None, если заявка не найдена
        """
        try:
            print(f"Поиск заявки с ID: {ticket_id}")
            conn = sqlite3.connect(self.db_path)
            # Настраиваем соединение для получения результатов в виде словаря
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Поиск заявки по ID, приводим ID к строке для безопасности
            ticket_id_str = str(ticket_id)
            print(f"Выполняем SQL запрос для поиска заявки: SELECT * FROM tickets WHERE ticket_id = '{ticket_id_str}'")
            cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id_str,))
            ticket_row = cursor.fetchone()
            
            if not ticket_row:
                # Если заявка не найдена, возвращаем None
                print(f"Заявка не найдена: {ticket_id}")
                return None
            
            # Преобразуем строку JSON обратно в словарь Python
            ticket_data = dict(ticket_row)
            ticket_data['form_data'] = json.loads(ticket_data['form_data'])
            
            # Убедимся, что user_id хранится как целое число
            ticket_data['user_id'] = int(ticket_data['user_id'])
            
            conn.close()
            print(f"Заявка найдена: {ticket_id}, user_id={ticket_data['user_id']}")
            return ticket_data
        except Exception as e:
            # В случае ошибки при получении заявки возвращаем None
            print(f"Ошибка при получении заявки: {e}")
            return None
    
    def get_all_tickets(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получение всех заявок или заявок конкретного пользователя.
        
        Args:
            user_id: ID пользователя ВКонтакте (если None, возвращаются все заявки)
            
        Returns:
            List[Dict]: Список словарей с данными заявок
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Если указан user_id, получаем только заявки этого пользователя
            if user_id is not None:
                cursor.execute("SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            else:
                # Иначе получаем все заявки, сортируя по дате создания
                cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
            
            tickets = []
            for row in cursor.fetchall():
                # Для каждой строки результата создаем словарь и преобразуем JSON данные
                ticket_data = dict(row)
                ticket_data['form_data'] = json.loads(ticket_data['form_data'])
                tickets.append(ticket_data)
            
            conn.close()
            return tickets
        except Exception:
            # В случае ошибки возвращаем пустой список
            return []
    
    def update_ticket(self, ticket_id: str, form_data: Dict[str, str]) -> bool:
        """
        Обновление данных заявки.
        
        Args:
            ticket_id: Идентификатор заявки
            form_data: Новые данные формы
            
        Returns:
            bool: True, если заявка успешно обновлена, иначе False
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Преобразуем словарь form_data в JSON строку
            form_data_json = json.dumps(form_data, ensure_ascii=False)
            
            # Обновляем данные формы для указанной заявки
            cursor.execute(
                "UPDATE tickets SET form_data = ? WHERE ticket_id = ?",
                (form_data_json, ticket_id)
            )
            
            if cursor.rowcount == 0:
                # Если ни одна строка не была обновлена, значит заявка не найдена
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            # В случае ошибки при обновлении заявки возвращаем False
            return False
    
    def delete_ticket(self, ticket_id: str, user_id: int) -> bool:
        """
        Удаление заявки из базы данных.
        
        Args:
            ticket_id: Идентификатор заявки для удаления
            user_id: ID пользователя ВКонтакте (для проверки прав доступа)
            
        Returns:
            bool: True если заявка успешно удалена, False если произошла ошибка
        """
        try:
            # Подключаемся к базе данных
            print(f"Попытка удаления заявки: {ticket_id} для пользователя: {user_id}")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Преобразуем ticket_id в строку и user_id в число для согласованности
            ticket_id_str = str(ticket_id)
            user_id_int = int(user_id)
            
            # Проверяем, существует ли заявка и принадлежит ли она указанному пользователю
            sql_query = f"SELECT COUNT(*) FROM tickets WHERE ticket_id = '{ticket_id_str}' AND user_id = {user_id_int}"
            print(f"Выполняем SQL запрос: {sql_query}")
            cursor.execute(
                "SELECT COUNT(*) FROM tickets WHERE ticket_id = ? AND user_id = ?",
                (ticket_id_str, user_id_int)
            )
            result = cursor.fetchone()
            print(f"Результат проверки: {result}")
            
            # Если заявка не найдена или принадлежит другому пользователю
            if not result or result[0] == 0:
                print(f"Заявка не найдена или принадлежит другому пользователю: {ticket_id}")
                conn.close()
                return False
            
            # Удаляем заявку
            print(f"Удаляем заявку: {ticket_id}")
            cursor.execute(
                "DELETE FROM tickets WHERE ticket_id = ? AND user_id = ?",
                (ticket_id_str, user_id_int)
            )
            conn.commit()
            conn.close()
            print(f"Заявка успешно удалена: {ticket_id}")
            
            return True
        except Exception as e:
            print(f"Ошибка при удалении заявки: {e}")
            return False