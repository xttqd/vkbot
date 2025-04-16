import logging
import sys

from vkbottle.bot import Bot

from . import config
from .db_handler import DatabaseHandler
from .form_handler import FormHandler
from .handlers import BotHandlers

logger = logging.getLogger(__name__)


def main() -> None:
    if not config.VK_TOKEN:
        logger.critical("VK_TOKEN is not set in the environment. Cannot start bot.")
        sys.exit(1)

    logger.info("Initializing bot components...")
    bot: Bot = Bot(token=config.VK_TOKEN)
    db_handler: DatabaseHandler = DatabaseHandler(db_name="tickets.db")
    form_handler: FormHandler = FormHandler(config.FORM_FIELDS_CONFIG, db_handler)
    bot_handlers: BotHandlers = BotHandlers(bot, form_handler, db_handler)
    bot_handlers.register_handlers()

    async def init_database() -> None:
        try:
            await db_handler.init_db()
            logger.info("Database initialization successful via startup task.")
        except Exception as e:
            logger.critical(f"CRITICAL: Database initialization failed: {e}")
            raise

    bot.loop_wrapper.on_startup.append(init_database())

    logger.info("Starting bot with run_forever()...")
    bot.run_forever()


if __name__ == "__main__":
    main()
