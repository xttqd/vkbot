import sqlite3
import json
from datetime import datetime
from typing import Dict, Optional, List, Any
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseHandler:
    """
    Класс для работы с базой данных SQLite.
    Обеспечивает создание, чтение, обновление и удаление заявок.
    Использует context manager для соединений.
    """
    
    def __init__(self, db_name: str = "tickets.db"):
        """
        Инициализация обработчика базы данных.
        
        Args:
            db_name: Имя файла базы данных SQLite
        """
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_name)
        logger.info(f"Database path set to: {self.db_path}")
        
        self._init_db()
    
    def _get_connection(self):
        """Возвращает соединение с базой данных."""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self) -> None:
        """
        Инициализация базы данных и создание таблиц, если они не существуют.
        Создает таблицу tickets для хранения заявок пользователей.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    form_data TEXT NOT NULL
                )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
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
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                form_data_json = json.dumps(form_data, ensure_ascii=False)
                
                cursor.execute(
                    "INSERT INTO tickets (ticket_id, user_id, created_at, form_data) VALUES (?, ?, ?, ?)",
                    (ticket_id, user_id, datetime.now().isoformat(), form_data_json)
                )
                
                conn.commit()
                logger.info(f"Ticket {ticket_id} created for user {user_id}.")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error creating ticket {ticket_id} for user {user_id}: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Error encoding form_data for ticket {ticket_id}: {e}")
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
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                ticket_id_str = str(ticket_id)
                cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id_str,))
                ticket_row = cursor.fetchone()
                
                if not ticket_row:
                    logger.debug(f"Ticket not found: {ticket_id}")
                    return None
                
                ticket_data = dict(ticket_row)
                ticket_data['form_data'] = json.loads(ticket_data['form_data'])
                
                ticket_data['user_id'] = int(ticket_data['user_id'])
                
                logger.debug(f"Ticket found: {ticket_id}")
                return ticket_data
        except sqlite3.Error as e:
            logger.error(f"Error getting ticket {ticket_id}: {e}")
            return None
        except json.JSONDecodeError as e:
             logger.error(f"Error decoding form_data for ticket {ticket_id}: {e}")
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
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if user_id is not None:
                    cursor.execute("SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
                else:
                    cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
                
                tickets = []
                for row in cursor.fetchall():
                    try:
                        ticket_data = dict(row)
                        ticket_data['form_data'] = json.loads(ticket_data['form_data'])
                        ticket_data['user_id'] = int(ticket_data['user_id'])
                        tickets.append(ticket_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding form_data for ticket {row['ticket_id']} in get_all_tickets: {e}")
                        continue 
                    except KeyError as e:
                        logger.error(f"Missing expected key in ticket row {dict(row)}: {e}")
                        continue
                
                logger.debug(f"Retrieved {len(tickets)} tickets" + (f" for user {user_id}" if user_id else ""))
                return tickets
        except sqlite3.Error as e:
            logger.error(f"Error getting all tickets" + (f" for user {user_id}" if user_id else "") + f": {e}")
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
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                form_data_json = json.dumps(form_data, ensure_ascii=False)
                
                cursor.execute(
                    "UPDATE tickets SET form_data = ? WHERE ticket_id = ?",
                    (form_data_json, ticket_id)
                )
                
                if cursor.rowcount == 0:
                    logger.warning(f"Attempted to update non-existent ticket: {ticket_id}")
                    return False
                
                conn.commit()
                logger.info(f"Ticket {ticket_id} updated.")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating ticket {ticket_id}: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Error encoding form_data for ticket update {ticket_id}: {e}")
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
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                logger.info(f"Попытка удаления заявки: {ticket_id} для пользователя: {user_id}")
                
                ticket_id_str = str(ticket_id)
                user_id_int = int(user_id)
                
                sql_query = f"SELECT COUNT(*) FROM tickets WHERE ticket_id = '{ticket_id_str}' AND user_id = {user_id_int}"
                logger.debug(f"Выполняем SQL запрос: {sql_query}")
                cursor.execute(
                    "SELECT COUNT(*) FROM tickets WHERE ticket_id = ? AND user_id = ?",
                    (ticket_id_str, user_id_int)
                )
                result = cursor.fetchone()
                logger.debug(f"Результат проверки: {result}")
                
                if not result or result[0] == 0:
                    logger.warning(f"Заявка не найдена или принадлежит другому пользователю: {ticket_id}")
                    return False
                
                logger.info(f"Удаляем заявку: {ticket_id}")
                cursor.execute(
                    "DELETE FROM tickets WHERE ticket_id = ? AND user_id = ?",
                    (ticket_id_str, user_id_int)
                )
                conn.commit()
                logger.info(f"Заявка успешно удалена: {ticket_id}")
                
                return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting ticket {ticket_id} by user {user_id}: {e}")
            return False