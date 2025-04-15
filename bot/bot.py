import logging
from vkbottle.bot import Bot
from . import config
from .form_handler import FormHandler
from .db_handler import DatabaseHandler
from .handlers import BotHandlers

logger = logging.getLogger(__name__)

def main():
    """Инициализация и запуск бота."""
    logger.info("Initializing bot components...")
    bot = Bot(token=config.VK_TOKEN)
    db_handler = DatabaseHandler(db_name="tickets.db")
    form_handler = FormHandler(config.FORM_FIELDS)
    bot_handlers = BotHandlers(bot, form_handler, db_handler)
    bot_handlers.register_handlers()

    logger.info("Starting bot...")
    bot.run_forever()

if __name__ == "__main__":
    main()