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
            conn = sqlite3.connect(self.db_path)
            # Настраиваем соединение для получения результатов в виде словаря
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Поиск заявки по ID, приводим ID к строке для безопасности
            cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (str(ticket_id),))
            ticket_row = cursor.fetchone()
            
            if not ticket_row:
                # Если заявка не найдена, возвращаем None
                return None
            
            # Преобразуем строку JSON обратно в словарь Python
            ticket_data = dict(ticket_row)
            ticket_data['form_data'] = json.loads(ticket_data['form_data'])
            
            conn.close()
            return ticket_data
        except Exception:
            # В случае ошибки при получении заявки возвращаем None
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
    
    def delete_ticket(self, ticket_id: str) -> bool:
        """
        Удаление заявки из базы данных.
        
        Args:
            ticket_id: Идентификатор заявки
            
        Returns:
            bool: True, если заявка успешно удалена, иначе False
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Удаляем заявку с указанным ID
            cursor.execute("DELETE FROM tickets WHERE ticket_id = ?", (ticket_id,))
            
            if cursor.rowcount == 0:
                # Если ни одна строка не была удалена, значит заявка не найдена
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            # В случае ошибки при удалении заявки возвращаем False
            return False