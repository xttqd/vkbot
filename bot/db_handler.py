from datetime import datetime, UTC
from typing import Dict, Optional, List, Any
import os
import logging
from sqlalchemy import Integer, String, DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column
from sqlalchemy.dialects.sqlite import JSON

logger = logging.getLogger(__name__)

Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = mapped_column(String, primary_key=True)
    user_id = mapped_column(Integer, nullable=False, index=True)
    created_at = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    form_data = mapped_column(JSON, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует объект Ticket в словарь."""
        return {
            "ticket_id": self.ticket_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "form_data": self.form_data,
        }


class DatabaseHandler:
    """
    Асинхронный класс для работы с базой данных SQLite
    с использованием SQLAlchemy.
    Обеспечивает создание, чтение, обновление и удаление заявок.
    """

    def __init__(self, db_name: str = "tickets.db"):
        """
        Инициализация обработчика базы данных.

        Args:
            db_name: Имя файла базы данных SQLite
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, db_name)
        self.db_url = f"sqlite+aiosqlite:///{self.db_path}"
        logger.info(f"Database URL set to: {self.db_url}")

        self.engine = create_async_engine(self.db_url, echo=False)
        self.async_session_maker = sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self) -> None:
        """
        Асинхронная инициализация базы данных и создание таблиц,
        если они не существуют.
        """
        async with self.engine.begin() as conn:
            try:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing database: {e}")
                raise

    async def create_ticket(
        self, ticket_id: str, user_id: int, form_data: Dict[str, Any]
    ) -> bool:
        """
        Асинхронное создание новой заявки в базе данных.

        Args:
            ticket_id: Уникальный идентификатор заявки
            user_id: ID пользователя ВКонтакте
            form_data: Словарь с данными формы

        Returns:
            bool: True, если заявка успешно создана, иначе False
        """
        async with self.async_session_maker() as session:
            async with session.begin():
                try:
                    new_ticket = Ticket(
                        ticket_id=str(ticket_id),
                        user_id=int(user_id),
                        form_data=form_data,
                    )
                    session.add(new_ticket)
                    await session.commit()
                    logger.info(f"Ticket {ticket_id} created for user {user_id}.")
                    return True
                except Exception as e:
                    await session.rollback()
                    logger.error(
                        f"Error creating ticket {ticket_id} for user {user_id}: {e}"
                    )
                    return False

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Асинхронное получение заявки по её ID.

        Args:
            ticket_id: Идентификатор заявки

        Returns:
            Dict или None: Словарь с данными заявки или None,
            если заявка не найдена
        """
        async with self.async_session_maker() as session:
            try:
                stmt = select(Ticket).where(Ticket.ticket_id == str(ticket_id))
                result = await session.execute(stmt)
                ticket = result.scalar_one_or_none()

                if ticket:
                    logger.debug(f"Ticket found: {ticket_id}.")
                    return ticket.to_dict()
                else:
                    logger.debug(f"Ticket not found: {ticket_id}.")
                    return None
            except Exception as e:
                # Break long log message
                logger.error(f"Error getting ticket {ticket_id}: {e}")
                return None

    async def get_all_tickets(
        self, user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Асинхронное получение всех заявок
        или заявок конкретного пользователя.

        Args:
            user_id: ID пользователя ВКонтакте
                     (если None, возвращаются все заявки)

        Returns:
            List[Dict]: Список словарей с данными заявок
        """
        async with self.async_session_maker() as session:
            try:
                stmt = select(Ticket).order_by(Ticket.created_at.desc())
                if user_id is not None:
                    stmt = stmt.where(Ticket.user_id == int(user_id))

                result = await session.execute(stmt)
                tickets = [t.to_dict() for t in result.scalars().all()]
                user_info = f" for user {user_id}" if user_id else ""
                logger.debug(f"Retrieved {len(tickets)} tickets{user_info}.")
                return tickets
            except Exception as e:
                user_info = f" for user {user_id}" if user_id else ""
                log_msg = f"Error getting all tickets{user_info}"
                logger.error(f"{log_msg}: {e}")
                return []

    async def update_ticket(self, ticket_id: str, form_data: Dict[str, Any]) -> bool:
        """
        Асинхронное обновление данных заявки.

        Args:
            ticket_id: Идентификатор заявки
            form_data: Новые данные формы

        Returns:
            bool: True, если заявка успешно обновлена, иначе False
        """
        async with self.async_session_maker() as session:
            async with session.begin():
                try:
                    stmt = select(Ticket).where(Ticket.ticket_id == str(ticket_id))
                    result = await session.execute(stmt)
                    ticket_to_update = result.scalar_one_or_none()

                    if not ticket_to_update:
                        logger.warning(
                            f"Attempted to update non-existent ticket: {ticket_id}."
                        )
                        return False

                    ticket_to_update.form_data = form_data
                    await session.commit()
                    logger.info(f"Ticket {ticket_id} updated.")
                    return True

                except Exception as e:
                    await session.rollback()
                    logger.error(f"Error updating ticket {ticket_id}: {e}")
                    return False

    async def delete_ticket(self, ticket_id: str, user_id: int) -> bool:
        """
        Асинхронное удаление заявки из базы данных.

        Args:
            ticket_id: Идентификатор заявки для удаления
            user_id: ID пользователя ВКонтакте (для проверки прав доступа)

        Returns:
            bool: True если заявка успешно удалена, False если не найдена,
                  не принадлежит пользователю или произошла ошибка
        """
        async with self.async_session_maker() as session:
            async with session.begin():
                try:
                    stmt = select(Ticket).where(Ticket.ticket_id == str(ticket_id))
                    result = await session.execute(stmt)
                    ticket_to_delete = result.scalar_one_or_none()

                    if not ticket_to_delete:
                        logger.warning(f"Delete failed: Ticket not found: {ticket_id}.")
                        return False

                    if ticket_to_delete.user_id != int(user_id):
                        logger.warning(
                            f"Delete failed: Ticket {ticket_id} does not "
                            f"belong to user {user_id}."
                        )
                        return False

                    await session.delete(ticket_to_delete)
                    await session.commit()
                    logger.info(
                        f"Ticket {ticket_id} deleted successfully by user {user_id}."
                    )
                    return True

                except Exception as e:
                    await session.rollback()
                    log_msg = f"Error deleting ticket {ticket_id} by user {user_id}"
                    logger.error(f"{log_msg}: {e}")
                    return False
