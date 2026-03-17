"""
Основной модуль Telegram бота для генерации изображений с FLUX.
"""

import os
import logging
import sys
import warnings
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)

from modules.config import (
    AUTHORIZED_USERS,
    BOT_PRIVATE, SETTINGS, SETTING_ASPECT_RATIO,
    SETTING_NUM_OUTPUTS, SETTING_PROMPT_STRENGTH, SETTING_GEMINI_MODEL,
    SETTING_GENERATION_CYCLES, AWAITING_BENCHMARK_PROMPT, AWAITING_CONFIRMATION,
    SETTING_PHOTOSHOOT_SCHEDULE,
    logger,
    AWAITING_BENCHMARK_OPTIONS, AWAITING_BENCHMARK_COUNT,
    SETTING_AUTO_CONFIRM_PROMPT
)
from modules.handlers import (
    start, help_command, cancel_command, settings_command,
    settings_handler, num_outputs_handler, aspect_ratio_handler,
    prompt_strength_handler, handle_text_message, handle_voice_message,
    handle_photo_message, prompt_confirmation, gemini_model_handler,
    generation_cycles_handler, handle_aspect_ratio_message, benchmark_prompt_handler,
    benchmark_options_handler, benchmark_count_handler,
    auto_confirm_prompt_handler,
    photoshoot_command, photoshoot_schedule_handler
)

warnings.filterwarnings('ignore')


def setup_logging():
    """Настраивает логирование для бота."""
    if not os.path.exists('logs'):
        os.makedirs('logs')

    file_handler = logging.FileHandler('logs/bot.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.info("Логирование настроено")


def main():
    """Основная функция для запуска бота."""
    try:
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            logger.critical("TELEGRAM_TOKEN отсутствует в .env файле. Бот не может быть запущен.")
            sys.exit(1)

        setup_logging()

        if BOT_PRIVATE:
            logger.info("Бот запускается в приватном режиме.")
            for user in AUTHORIZED_USERS:
                logger.info(f"  - @{user.get('username', 'N/A')} (ID: {user.get('chat_id', 'N/A')})")
        else:
            logger.info("Бот запускается в публичном режиме.")

        application = Application.builder().token(token).build()

        # ConversationHandler для настроек
        settings_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("settings", settings_command)],
            states={
                SETTINGS: [CallbackQueryHandler(settings_handler)],
                SETTING_ASPECT_RATIO: [CallbackQueryHandler(aspect_ratio_handler)],
                SETTING_NUM_OUTPUTS: [CallbackQueryHandler(num_outputs_handler)],
                SETTING_PROMPT_STRENGTH: [CallbackQueryHandler(prompt_strength_handler)],
                SETTING_GEMINI_MODEL: [CallbackQueryHandler(gemini_model_handler)],
                SETTING_GENERATION_CYCLES: [CallbackQueryHandler(generation_cycles_handler)],
                SETTING_AUTO_CONFIRM_PROMPT: [CallbackQueryHandler(auto_confirm_prompt_handler)],
                SETTING_PHOTOSHOOT_SCHEDULE: [CallbackQueryHandler(photoshoot_schedule_handler)],
                AWAITING_BENCHMARK_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, benchmark_prompt_handler)],
                AWAITING_BENCHMARK_OPTIONS: [CallbackQueryHandler(benchmark_options_handler)],
                AWAITING_BENCHMARK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, benchmark_count_handler)],
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
        )

        # ConversationHandler для генерации изображений
        generation_conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message),
                MessageHandler(filters.VOICE, handle_voice_message),
                MessageHandler(filters.PHOTO, handle_photo_message)
            ],
            states={
                AWAITING_CONFIRMATION: [CallbackQueryHandler(prompt_confirmation, pattern="^prompt_")],
            },
            fallbacks=[CommandHandler("cancel", cancel_command)],
        )

        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CommandHandler("photoshoot", photoshoot_command))
        application.add_handler(settings_conv_handler)
        application.add_handler(generation_conv_handler)

        logger.info("Бот запущен и готов к работе")
        application.run_polling()

    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
