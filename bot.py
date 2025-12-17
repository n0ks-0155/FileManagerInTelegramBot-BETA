import telebot
import config
from handlers.command_handlers import register_command_handlers
from handlers.callback_handlers import register_callback_handlers
from handlers.message_handlers import register_message_handlers
import time
import requests
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Для максимального количества информации в логах
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),  # Запись логов в файл
        logging.StreamHandler()          # И вывод в консоль, чтобы всё сразу видеть
    ]
)

logger = logging.getLogger(__name__)

def start_bot():
    bot = telebot.TeleBot(config.BOT_TOKEN)

    # Регистрация обработчиков
    register_command_handlers(bot)
    register_callback_handlers(bot)
    register_message_handlers(bot)

    # Запуск бота с обработкой возможных исключений
    while True:
        try:
            logger.info("Бот запущен и ожидает обновлений...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except requests.exceptions.ReadTimeout:
            logger.warning("Превышено время ожидания. Перезапуск...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Произошла ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_bot()