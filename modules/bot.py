"""
Основной модуль Telegram бота для генерации изображений с FLUX.
"""

import os
import logging
import sys
import asyncio
import warnings
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)

from modules.config import (
    MAX_RETRIES, TELEGRAM_TOKEN, AUTHORIZED_USERS,
    BOT_PRIVATE, SETTINGS, AWAITING_PROMPT, SETTING_ASPECT_RATIO,
    SETTING_NUM_OUTPUTS, SETTING_PROMPT_STRENGTH, SETTING_OPENAI_MODEL,
    SETTING_GENERATION_CYCLES, AWAITING_BENCHMARK_PROMPT, AWAITING_CONFIRMATION,
    logger,
    AWAITING_BENCHMARK_OPTIONS, AWAITING_BENCHMARK_COUNT,
    SETTING_AUTO_CONFIRM_PROMPT
)
from modules.handlers import (
    start, help_command, cancel_command, settings_command,
    settings_handler, num_outputs_handler, aspect_ratio_handler,
    prompt_strength_handler, handle_text_message, handle_voice_message,
    handle_photo_message, prompt_confirmation, openai_model_handler,
    generation_cycles_handler, handle_aspect_ratio_message, benchmark_prompt_handler,
    benchmark_options_handler, benchmark_count_handler,
    auto_confirm_prompt_handler
)

warnings.filterwarnings('ignore')

def setup_logging():
    """Настраивает логирование для бота."""
    # Создаем директорию для логов, если она не существует
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Настраиваем логирование в файл
    file_handler = logging.FileHandler('logs/bot.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Устанавливаем уровень логирования
    logger.setLevel(logging.INFO)
    
    logger.info("Логирование настроено")

def main():
    """Основная функция для запуска бота."""
    try:
        # Настройка и запуск бота
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            logger.critical("TELEGRAM_TOKEN отсутствует в .env файле. Бот не может быть запущен.")
            sys.exit(1)
            
        # Настраиваем логирование
        setup_logging()
        
        # Вывод информации о режиме бота
        if BOT_PRIVATE:
            authorized_usernames = [user["username"] for user in AUTHORIZED_USERS if "username" in user]
            authorized_ids = [user["chat_id"] for user in AUTHORIZED_USERS if "chat_id" in user]
            logger.info(f"Бот запускается в приватном режиме. Доступ разрешен только для авторизованных пользователей:")
            for user in AUTHORIZED_USERS:
                logger.info(f"  - @{user.get('username', 'Нет имени')} (ID: {user.get('chat_id', 'Нет ID')})")
        else:
            logger.info("Бот запускается в публичном режиме. Доступ открыт для всех пользователей.")
        
        # Создаем экземпляр бота
        application = Application.builder().token(token).build()
        
        # Conversation Handler для настроек бота
        settings_handlers = [
            CallbackQueryHandler(settings_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_aspect_ratio_message),
        ]
        
        # Регистрируем ConversationHandler для настроек
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("settings", settings_command)],
            states={
                SETTINGS: [CallbackQueryHandler(settings_handler)],
                SETTING_ASPECT_RATIO: [CallbackQueryHandler(aspect_ratio_handler)],
                SETTING_NUM_OUTPUTS: [CallbackQueryHandler(num_outputs_handler)],
                SETTING_PROMPT_STRENGTH: [CallbackQueryHandler(prompt_strength_handler)],
                SETTING_OPENAI_MODEL: [CallbackQueryHandler(openai_model_handler)],
                SETTING_GENERATION_CYCLES: [CallbackQueryHandler(generation_cycles_handler)],
                SETTING_AUTO_CONFIRM_PROMPT: [CallbackQueryHandler(auto_confirm_prompt_handler)],
                AWAITING_BENCHMARK_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, benchmark_prompt_handler)],
                AWAITING_BENCHMARK_OPTIONS: [CallbackQueryHandler(benchmark_options_handler)],
                AWAITING_BENCHMARK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, benchmark_count_handler)],
                AWAITING_CONFIRMATION: [CallbackQueryHandler(prompt_confirmation)],
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
        )
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(conv_handler)
        
        # Регистрируем обработчик для подтверждения промпта
        application.add_handler(CallbackQueryHandler(prompt_confirmation, pattern="^prompt_"))
        
        # Обработчики сообщений
        application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Запускаем бота
        logger.info("Бот запущен и готов к работе")
        application.run_polling()
        
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 