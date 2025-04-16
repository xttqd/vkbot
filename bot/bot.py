import logging

from vkbottle.bot import Bot

from . import config
from .db_handler import DatabaseHandler
from .form_handler import FormHandler
from .handlers import BotHandlers

logger = logging.getLogger(__name__)


def main():
    """Синхронная инициализация и запуск бота.
    Инициализация БД происходит через startup task.
    """
    logger.info("Initializing bot components...")
    bot = Bot(token=config.VK_TOKEN)
    db_handler = DatabaseHandler(db_name="tickets.db")
    form_handler = FormHandler(config.FORM_FIELDS, db_handler)
    bot_handlers = BotHandlers(bot, form_handler, db_handler)
    bot_handlers.register_handlers()

    async def init_database():
        try:
            await db_handler.init_db()
            logger.info("Database initialization successful via startup task.")
        except Exception as e:
            logger.critical(f"Database initialization failed: {e}")
            # Consider handling this more gracefully

    bot.loop_wrapper.on_startup.append(init_database())

    logger.info("Starting bot with run_forever()...")
    bot.run_forever()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
