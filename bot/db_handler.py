from datetime import datetime, UTC
from typing import Dict, Optional, List, Any
import os
import logging
from sqlalchemy import Integer, String, DateTime, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base, mapped_column, Mapped
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

logger = logging.getLogger(__name__)

Base = declarative_base()


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    form_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "form_data": self.form_data,
        }


class DatabaseHandler:
    db_path: str
    db_url: str
    engine: AsyncEngine
    async_session_maker: sessionmaker[AsyncSession]

    def __init__(self, db_name: str = "tickets.db"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, db_name)
        self.db_url = f"sqlite+aiosqlite:///{self.db_path}"
        logger.info(f"Database URL set to: {self.db_url}")

        self.engine = create_async_engine(self.db_url, echo=False)
        self.async_session_maker = sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self) -> None:
        async with self.engine.begin() as conn:
            try:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database initialized successfully.")
            except SQLAlchemyError as e:
                logger.error(f"Database initialization failed: {e}")
                raise
            except Exception as e:
                logger.critical(f"Unexpected error during database initialization: {e}")
                raise

    async def create_ticket(
        self, ticket_id: str, user_id: int, form_data: Dict[str, Any]
    ) -> bool:
        session: AsyncSession
        async with self.async_session_maker() as session:
            async with session.begin():
                try:
                    new_ticket = Ticket(
                        ticket_id=ticket_id,
                        user_id=user_id,
                        form_data=form_data,
                    )
                    session.add(new_ticket)
                    logger.info(f"Ticket {ticket_id} created for user {user_id}.")
                    return True
                except IntegrityError as e:
                    await session.rollback()
                    logger.warning(
                        f"Integrity error creating ticket {ticket_id} for user {user_id} (likely duplicate ID): {e}"
                    )
                    return False
                except SQLAlchemyError as e:
                    await session.rollback()
                    logger.error(
                        f"Database error creating ticket {ticket_id} for user {user_id}: {e}"
                    )
                    return False
                except Exception as e:
                    await session.rollback()
                    logger.error(
                        f"Unexpected error creating ticket {ticket_id} for user {user_id}: {e}"
                    )
                    return False

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        session: AsyncSession
        async with self.async_session_maker() as session:
            try:
                stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
                result = await session.execute(stmt)
                ticket: Optional[Ticket] = result.scalar_one_or_none()

                if ticket:
                    logger.debug(f"Ticket found: {ticket_id}.")
                    return ticket.to_dict()
                else:
                    logger.debug(f"Ticket not found: {ticket_id}.")
                    return None
            except SQLAlchemyError as e:
                logger.error(f"Database error getting ticket {ticket_id}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error getting ticket {ticket_id}: {e}")
                return None

    async def get_all_tickets(
        self, user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        session: AsyncSession
        async with self.async_session_maker() as session:
            user_info = f" for user {user_id}" if user_id else ""
            try:
                stmt = select(Ticket).order_by(Ticket.created_at.desc())
                if user_id is not None:
                    stmt = stmt.where(Ticket.user_id == user_id)

                result = await session.execute(stmt)
                tickets: List[Ticket] = list(result.scalars().all())
                logger.debug(f"Retrieved {len(tickets)} tickets{user_info}.")
                return [t.to_dict() for t in tickets]
            except SQLAlchemyError as e:
                log_msg = f"Database error getting all tickets{user_info}"
                logger.error(f"{log_msg}: {e}")
                return []
            except Exception as e:
                log_msg = f"Unexpected error getting all tickets{user_info}"
                logger.error(f"{log_msg}: {e}")
                return []

    async def delete_ticket(self, ticket_id: str, user_id: int) -> bool:
        session: AsyncSession
        async with self.async_session_maker() as session:
            async with session.begin():
                try:
                    stmt_select = (
                        select(Ticket.ticket_id)
                        .where(Ticket.ticket_id == ticket_id)
                        .where(Ticket.user_id == user_id)
                    )
                    result_select = await session.execute(stmt_select)
                    ticket_exists = result_select.scalar_one_or_none()

                    if not ticket_exists:
                        stmt_check = select(Ticket).where(Ticket.ticket_id == ticket_id)
                        result_check = await session.execute(stmt_check)
                        ticket_any = result_check.scalar_one_or_none()
                        if not ticket_any:
                            logger.warning(
                                f"Delete failed: Ticket not found: {ticket_id}."
                            )
                        else:
                            logger.warning(
                                f"Delete failed: Ticket {ticket_id} does not "
                                f"belong to user {user_id}."
                            )
                        return False

                    stmt_delete = (
                        delete(Ticket)
                        .where(Ticket.ticket_id == ticket_id)
                        .where(Ticket.user_id == user_id)
                    )
                    result_delete = await session.execute(stmt_delete)

                    if result_delete.rowcount > 0:
                        logger.info(
                            f"Ticket {ticket_id} belonging to user {user_id} deleted successfully."
                        )
                        return True
                    else:
                        logger.warning(
                            f"Delete seemed to fail for ticket {ticket_id} after verification pass (rowcount=0)."
                        )
                        return False

                except SQLAlchemyError as e:
                    await session.rollback()
                    log_msg = (
                        f"Database error deleting ticket {ticket_id} for user {user_id}"
                    )
                    logger.error(f"{log_msg}: {e}")
                    return False
                except Exception as e:
                    await session.rollback()
                    log_msg = f"Unexpected error deleting ticket {ticket_id} for user {user_id}"
                    logger.error(f"{log_msg}: {e}")
                    return False
