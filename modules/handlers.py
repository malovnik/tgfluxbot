"""
Модуль с обработчиками команд и сообщений Telegram бота.
"""

import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from modules.config import (
    AWAITING_CONFIRMATION, SETTINGS,
    SETTING_NUM_OUTPUTS, SETTING_ASPECT_RATIO, SETTING_PROMPT_STRENGTH,
    SETTING_OPENAI_MODEL, SETTING_GENERATION_CYCLES,
    ASPECT_RATIOS, OPENAI_MODELS, 
    logger, OWNER_USERNAME, OWNER_CHAT_ID, BOT_PRIVATE,
    AWAITING_BENCHMARK_PROMPT, BENCHMARK_SETTINGS, BENCHMARK_PROMPT_STRENGTHS,
    BENCHMARK_GUIDANCE_SCALES, BENCHMARK_INFERENCE_STEPS, MAX_BENCHMARK_ITERATIONS
)
from modules.settings import (
    get_user_settings, update_user_settings, reset_user_settings
)
from modules.ai_services import (
    generate_prompt, analyze_image, transcribe_audio, 
    analyze_image_content, generate_image, download_file
)

# =================================================================
# Функция проверки авторизации
# =================================================================

async def check_authorization(update: Update) -> bool:
    """
    Проверяет, имеет ли пользователь право использовать бота.
    
    Args:
        update (Update): Объект с данными от Telegram
        
    Returns:
        bool: True если пользователь авторизован, False в противном случае
    """
    if not BOT_PRIVATE:
        return True  # Если бот не в приватном режиме, все пользователи авторизованы
        
    user = update.effective_user
    user_id = user.id
    username = user.username
    
    # Проверяем совпадение ID чата или имени пользователя
    is_authorized = (user_id == OWNER_CHAT_ID or username == OWNER_USERNAME)
    
    if not is_authorized:
        logger.warning(f"Неавторизованная попытка доступа: user_id={user_id}, username={username}")
    
    return is_authorized

async def send_unauthorized_message(update: Update):
    """Отправляет сообщение о недостаточных правах."""
    await update.message.reply_text(
        "⛔ Извините, но этот бот является личным фотографом @ВАШ ЛОГИН В ТГ.\n\n"
        "Вы можете создать своего бота на основе этого проекта, "
        "но данный экземпляр доступен только для его владельца."
    )

# =================================================================
# Основные команды
# =================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет стартовое сообщение при команде /start."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
        
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.first_name}! Я бот для генерации изображений с FLUX.\n\n'
        f'Вы можете:\n'
        f'📝 Отправить описание изображения текстом\n'
        f'🎤 Отправить голосовое сообщение с описанием\n'
        f'🖼 Отправить изображение для создания похожего с вами\n\n'
        f'Напишите /settings чтобы настроить параметры генерации.\n'
        f'Напишите /help для получения дополнительной информации.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет справочное сообщение."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
        
    await update.message.reply_text(
        "🤖 *Справка по использованию бота*\n\n"
        "*Основные команды:*\n"
        "/start - Начать работу с ботом\n"
        "/settings - Настройки генерации изображений\n"
        "/cancel - Отменить текущую операцию\n"
        "/help - Показать эту справку\n\n"
        
        "*Как использовать:*\n"
        "1️⃣ *Текстовые запросы:* просто отправьте описание желаемого изображения\n"
        "2️⃣ *Голосовые сообщения:* отправьте голосовое сообщение с описанием\n"
        "3️⃣ *По образцу:* отправьте изображение, и бот создаст похожее с вами\n\n"
        
        "После обработки запроса вы сможете подтвердить промпт, запросить новый или отменить операцию.\n\n"
        
        "*Настройки:*\n"
        "• Количество изображений (1-4)\n"
        "• Соотношение сторон (1:1, 16:9...)\n"
        "• Уровень следования промпту (0.75-1.0)\n\n"
        
        "*Примечание:* Генерация изображений может занять до 3 минут.",
        parse_mode="Markdown"
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает все активные диалоги."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
        
    await update.message.reply_text("Все текущие операции отменены. Вы можете начать снова.")
    return ConversationHandler.END

# =================================================================
# Обработчики настроек
# =================================================================

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображает настройки пользователя."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
        
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    
    keyboard = [
        [InlineKeyboardButton("Количество изображений", callback_data="set_num_outputs")],
        [InlineKeyboardButton("Соотношение сторон", callback_data="set_aspect_ratio")],
        [InlineKeyboardButton("Уровень следования промпту", callback_data="set_prompt_strength")],
        [InlineKeyboardButton("Модель OpenAI", callback_data="set_openai_model")],
        [InlineKeyboardButton("Количество циклов генерации", callback_data="set_generation_cycles")],
        [InlineKeyboardButton("🔬 Запустить прогон параметров", callback_data="start_benchmark")],
        [InlineKeyboardButton("Вернуться к стандартным настройкам", callback_data="reset_settings")],
        [InlineKeyboardButton("Закрыть настройки", callback_data="close_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Получаем читаемое название модели OpenAI
    openai_model_name = OPENAI_MODELS.get(settings['openai_model'], settings['openai_model'])
    
    await update.message.reply_text(
        f"📊 *Текущие настройки*:\n\n"
        f"🖼 Количество изображений: {settings['num_outputs']}\n"
        f"📐 Соотношение сторон: {settings['aspect_ratio']}\n"
        f"⚖️ Уровень следования промпту: {settings['prompt_strength']}\n"
        f"🧠 Модель OpenAI: {openai_model_name}\n"
        f"🔄 Циклов генерации: {settings['generation_cycles']}\n\n"
        f"Выберите параметр для изменения:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SETTINGS

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок в меню настроек."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    try:
        if query.data == "close_settings":
            await query.message.edit_text("✅ Настройки успешно сохранены. Отправьте описание изображения для генерации.")
            return ConversationHandler.END
        
        elif query.data == "reset_settings":
            reset_user_settings(user_id)
            
            await query.message.edit_text(
                "⚙️ Настройки сброшены до стандартных значений.\n"
                "Отправьте описание изображения для генерации."
            )
            return ConversationHandler.END
        
        elif query.data == "start_benchmark":
            await query.message.edit_text(
                "🔄 *Режим прогона параметров*\n\n"
                "Этот режим позволяет найти оптимальные параметры для конкретного промпта путем перебора различных значений.\n\n"
                "📌 *Фиксированные параметры:*\n"
                "• Размер: 256x256\n"
                "• Соотношение сторон: 16:9\n"
                "• Качество: 60%\n"
                "• Формат: JPEG\n\n"
                "📊 *Перебираемые параметры:*\n"
                "• Сила промпта: от 0.5 до 1.0 (шаг 0.05)\n"
                "• Guidance Scale: 2, 2.5, 3, 3.5\n"
                "• Шаги инференса: от 20 до 50\n\n"
                "⚠️ *Внимание:* будет запущено тестирование параметров (не более 20 итераций), что займет продолжительное время.\n\n"
                "Пожалуйста, введите промпт на английском языке для прогона:",
                parse_mode="Markdown"
            )
            return AWAITING_BENCHMARK_PROMPT
        
        elif query.data == "set_num_outputs":
            keyboard = []
            row = []
            for i in range(1, 5):
                row.append(InlineKeyboardButton(str(i), callback_data=f"num_outputs_{i}"))
            keyboard.append(row)
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "Выберите количество изображений для генерации (1-4):\n\n"
                "📝 *Примечание*: Чем больше изображений, тем дольше будет генерация.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return SETTING_NUM_OUTPUTS
        
        elif query.data == "set_aspect_ratio":
            keyboard = []
            aspect_ratio_descriptions = {
                "1:1": "квадрат",
                "16:9": "широкоформатный горизонтальный",
                "9:16": "вертикальный (для Stories)",
                "4:3": "классический горизонтальный",
                "3:4": "классический вертикальный"
            }
            
            for ratio in ASPECT_RATIOS:
                desc = aspect_ratio_descriptions.get(ratio, "")
                keyboard.append([InlineKeyboardButton(f"{ratio} ({desc})", callback_data=f"aspect_ratio_{ratio}")])
                
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "Выберите соотношение сторон изображения:\n\n"
                "📝 *Примечание*: Соотношение влияет на композицию и количество деталей в изображении.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return SETTING_ASPECT_RATIO
        
        elif query.data == "set_prompt_strength":
            keyboard = [
                [
                    InlineKeyboardButton("0.75 (свободнее)", callback_data="prompt_strength_0.75"),
                    InlineKeyboardButton("0.8", callback_data="prompt_strength_0.8"),
                    InlineKeyboardButton("0.85", callback_data="prompt_strength_0.85")
                ],
                [
                    InlineKeyboardButton("0.9 (стандарт)", callback_data="prompt_strength_0.9"),
                    InlineKeyboardButton("0.95", callback_data="prompt_strength_0.95"),
                    InlineKeyboardButton("1.0 (точнее)", callback_data="prompt_strength_1.0")
                ],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "Выберите уровень следования промпту:\n\n"
                "📝 *Пояснение*:\n"
                "• *Низкий* (0.75-0.85) - больше креативности и свободной интерпретации\n"
                "• *Средний* (0.9) - баланс между точностью и творчеством\n"
                "• *Высокий* (0.95-1.0) - строгое следование всем деталям промпта",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return SETTING_PROMPT_STRENGTH
            
        elif query.data == "set_openai_model":
            keyboard = []
            model_descriptions = {
                "gpt-4o": "🌟 Флагманская модель - баланс точности и скорости",
                "gpt-4o-mini": "⚡ Экономичная и быстрая, подходит для простых запросов",
                "gpt-4-turbo": "🚀 Мощная модель с отличной детализацией",
                "gpt-4-1106-preview": "🔍 Высокоточная модель для сложных запросов",
                "gpt-4o-2024-05-13": "📊 Продвинутая GPT-4o с улучшенной точностью",
                "gpt-3.5-turbo": "🔋 Базовая модель, быстрая и надежная"
            }
            
            for model_id, model_name in OPENAI_MODELS.items():
                desc = model_descriptions.get(model_id, "")
                keyboard.append([InlineKeyboardButton(f"{model_name} - {desc}", callback_data=f"openai_model_{model_id}")])
                
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "Выберите модель OpenAI для генерации промптов:\n\n"
                "📝 *Различия моделей*:\n"
                "• *GPT-4o* - наиболее точная и мощная, лучший выбор по умолчанию\n"
                "• *GPT-4o mini* - компактная версия, быстрее, но менее точная\n"
                "• *GPT-4 Turbo* - оптимизирована для сложных текстовых запросов\n"
                "• *GPT-4o-1* - специализированная точная версия для сложных запросов\n"
                "• *GPT-3.5 Turbo* - базовая модель, быстрая, но с меньшей детализацией\n\n"
                "💡 Более мощные модели генерируют более детальные промпты.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return SETTING_OPENAI_MODEL
            
        elif query.data == "set_generation_cycles":
            keyboard = []
            row = []
            for i in range(1, 6):
                row.append(InlineKeyboardButton(str(i), callback_data=f"generation_cycles_{i}"))
            keyboard.append(row)
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "Выберите количество циклов генерации промпта (1-5):\n\n"
                "📝 *Как это работает*:\n"
                "• *1 цикл* (стандарт) - один промпт и одна генерация\n"
                "• *2-5 циклов* - для каждого цикла:\n"
                "  1. Генерируется новый уникальный промпт на основе вашего исходного запроса\n"
                "  2. По каждому промпту создаются изображения\n"
                "  3. Результаты присылаются последовательно\n\n"
                "Это позволяет получить разные интерпретации одного запроса.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return SETTING_GENERATION_CYCLES
        
        elif query.data == "back_to_settings":
            return await settings_command(update, context)
    
    except Exception as e:
        logger.error(f"Ошибка в обработчике настроек: {e}")
        await query.message.edit_text("Произошла ошибка. Попробуйте позже или используйте /cancel.")
        return ConversationHandler.END
        
    return SETTINGS

async def num_outputs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор количества изображений."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "back_to_settings":
        return await settings_command(update, context)
    
    try:
        # Проверяем формат callback_data перед извлечением числа
        if not query.data.startswith("num_outputs_"):
            logger.error(f"Неожиданный формат callback_data: {query.data}")
            await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
            
        # Извлекаем число из callback_data
        num_outputs = int(query.data.split("_")[-1])
        update_user_settings(user_id, "num_outputs", num_outputs)
        
        # Сначала подтверждаем успешное обновление настройки
        await query.message.edit_text(f"Количество изображений успешно установлено: {num_outputs}")
        
        # Затем возвращаемся к меню настроек
        # Используем await и задержку для избежания ошибок обновления интерфейса
        import asyncio
        await asyncio.sleep(1)  # Добавляем небольшую задержку перед обновлением интерфейса
        return await settings_command(update, context)
    except ValueError as e:
        logger.error(f"Ошибка при обработке callback_data {query.data}: {e}")
        await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
        return ConversationHandler.END

async def aspect_ratio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор соотношения сторон для генерации изображений."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    try:
        # Проверяем формат callback data
        if ":" in query.data:
            aspect_ratio = query.data.split("_")[-1]
            # Проверяем, что соотношение сторон валидное
            if aspect_ratio in ASPECT_RATIOS:
                # Обновляем настройки пользователя
                update_user_settings(user_id, "aspect_ratio", aspect_ratio)
                
                # Показываем подтверждение
                await query.message.edit_text(
                    f"✅ Соотношение сторон установлено: {aspect_ratio}\n"
                    "Настройка применена успешно!",
                    parse_mode="Markdown"
                )
                
                # Добавляем небольшую задержку для улучшения UX
                await asyncio.sleep(1)
                
                # Возвращаемся в меню настроек
                await settings_command(update, context)
                return SETTINGS
                
        # Возвращаемся в меню настроек, если данные некорректны
        await settings_command(update, context)
        return SETTINGS
        
    except Exception as e:
        logger.error(f"Ошибка при обработке соотношения сторон: {e}")
        await query.message.edit_text(
            f"❌ Произошла ошибка при установке соотношения сторон.\n"
            f"Ошибка: {str(e)[:100]}...\n\n"
            f"Пожалуйста, попробуйте еще раз или используйте /cancel для сброса."
        )
        return ConversationHandler.END

async def handle_aspect_ratio_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовый ввод для соотношения сторон."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
        
    user_input = update.message.text.strip()
    
    # Проверяем, что введено валидное соотношение сторон (например, "16:9")
    if ":" in user_input and user_input in ASPECT_RATIOS:
        user_id = update.effective_user.id
        update_user_settings(user_id, "aspect_ratio", user_input)
        
        await update.message.reply_text(
            f"✅ Соотношение сторон установлено: {user_input}\n"
            "Настройка применена успешно!"
        )
        
        # Возвращаемся в меню настроек
        await settings_command(update, context)
        return SETTINGS
    else:
        await update.message.reply_text(
            "❌ Неверный формат. Пожалуйста, выберите одно из предложенных соотношений сторон или используйте /cancel для отмены."
        )
        return SETTING_ASPECT_RATIO

async def prompt_strength_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор уровня следования промпту."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "back_to_settings":
        return await settings_command(update, context)
    
    try:
        # Проверяем формат callback_data перед обработкой
        if not query.data.startswith("prompt_strength_"):
            logger.error(f"Неожиданный формат callback_data: {query.data}")
            await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
            
        # Извлекаем значение уровня из callback_data
        prompt_strength = float(query.data.split("_")[-1])
        update_user_settings(user_id, "prompt_strength", prompt_strength)
        
        # Сначала подтверждаем успешное обновление настройки
        await query.message.edit_text(f"Уровень следования промпту успешно установлен: {prompt_strength}")
        
        # Затем возвращаемся к меню настроек
        # Используем await и задержку для избежания ошибок обновления интерфейса
        import asyncio
        await asyncio.sleep(1)  # Добавляем небольшую задержку перед обновлением интерфейса
        return await settings_command(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке callback_data {query.data}: {e}")
        await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
        return ConversationHandler.END

async def openai_model_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор модели OpenAI."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "back_to_settings":
        return await settings_command(update, context)
    
    try:
        # Проверяем формат callback_data перед обработкой
        if not query.data.startswith("openai_model_"):
            logger.error(f"Неожиданный формат callback_data: {query.data}")
            await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
            
        # Извлекаем модель из callback_data
        model_id = query.data.replace("openai_model_", "")
        
        if model_id not in OPENAI_MODELS:
            logger.error(f"Неизвестная модель OpenAI: {model_id}")
            await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
            
        update_user_settings(user_id, "openai_model", model_id)
        model_name = OPENAI_MODELS.get(model_id, model_id)
        
        # Сначала подтверждаем успешное обновление настройки
        await query.message.edit_text(f"Модель OpenAI успешно установлена: {model_name}")
        
        # Затем возвращаемся к меню настроек
        # Используем await и задержку для избежания ошибок обновления интерфейса
        import asyncio
        await asyncio.sleep(1)  # Добавляем небольшую задержку перед обновлением интерфейса
        return await settings_command(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке callback_data {query.data}: {e}")
        await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
        return ConversationHandler.END

async def generation_cycles_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор количества циклов генерации."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "back_to_settings":
        return await settings_command(update, context)
    
    try:
        # Проверяем формат callback_data перед обработкой
        if not query.data.startswith("generation_cycles_"):
            logger.error(f"Неожиданный формат callback_data: {query.data}")
            await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
            
        # Извлекаем количество циклов из callback_data
        cycles = int(query.data.split("_")[-1])
        
        if cycles < 1 or cycles > 5:
            logger.error(f"Недопустимое количество циклов: {cycles}")
            await query.message.edit_text("Выбрано недопустимое количество циклов. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
            
        update_user_settings(user_id, "generation_cycles", cycles)
        
        # Сначала подтверждаем успешное обновление настройки
        await query.message.edit_text(f"Количество циклов генерации успешно установлено: {cycles}")
        
        # Затем возвращаемся к меню настроек
        # Используем await и задержку для избежания ошибок обновления интерфейса
        import asyncio
        await asyncio.sleep(1)  # Добавляем небольшую задержку перед обновлением интерфейса
        return await settings_command(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке callback_data {query.data}: {e}")
        await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
        return ConversationHandler.END

# =================================================================
# Обработчики пользовательских запросов
# =================================================================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
        
    # Сохраняем запрос пользователя в контексте
    context.user_data["user_request"] = update.message.text
    context.user_data["request_type"] = "text"
    
    # Сообщаем пользователю, что запрос обрабатывается
    message = await update.message.reply_text("⏳ Обрабатываю ваш текстовый запрос...")
    
    try:
        # Получаем ID пользователя для использования выбранной модели
        user_id = update.effective_user.id
        
        # Генерируем промпт через ChatGPT
        prompt = await generate_prompt(update.message.text, user_id)
        if not prompt:
            await message.edit_text("Произошла ошибка при создании промпта. Пожалуйста, попробуйте позже.")
            return ConversationHandler.END
        
        # Сохраняем промпт в контексте
        context.user_data["prompt"] = prompt
        
        return await show_prompt_confirmation(update, context, message, prompt)
        
    except Exception as e:
        logger.error(f"Произошла ошибка при обработке текстового сообщения: {e}")
        await message.edit_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        return ConversationHandler.END

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает голосовые сообщения."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
        
    # Сообщаем пользователю, что запрос обрабатывается
    message = await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        # Проверяем размер голосового сообщения
        voice_duration = update.message.voice.duration
        voice_file_size = update.message.voice.file_size
        logger.info(f"Получено голосовое сообщение длительностью {voice_duration} сек, размер: {voice_file_size} байт")
        
        if voice_duration > 60:  # Ограничение на длительность - 60 секунд
            await message.edit_text("⚠️ Голосовое сообщение слишком длинное. Пожалуйста, отправьте сообщение длительностью до 60 секунд.")
            return ConversationHandler.END
        
        # Получаем файл с голосовым сообщением
        voice_file = await update.message.voice.get_file()
        
        # Создаем временный файл для сохранения голосового сообщения
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_voice:
            voice_path = temp_voice.name
        
        # Загружаем голосовое сообщение
        await voice_file.download_to_drive(voice_path)
        logger.info(f"Голосовое сообщение сохранено во временный файл: {voice_path}")
        
        # Проверяем, что файл существует и не пустой
        if not os.path.exists(voice_path) or os.path.getsize(voice_path) == 0:
            logger.error(f"Проблема с сохранением голосового сообщения: файл не создан или пустой")
            await message.edit_text("Произошла ошибка при сохранении голосового сообщения. Пожалуйста, попробуйте снова.")
            
            # Попытка удаления временного файла, если он существует
            if os.path.exists(voice_path):
                os.remove(voice_path)
                
            return ConversationHandler.END
        
        # Транскрибируем голосовое сообщение
        await message.edit_text("🎤 Распознаю речь...")
        transcription = await transcribe_audio(voice_path)
        
        # Удаляем временный файл
        try:
            os.remove(voice_path)
            logger.info(f"Временный файл удален: {voice_path}")
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл: {e}")
        
        if not transcription:
            await message.edit_text("⚠️ Не удалось распознать голосовое сообщение. Пожалуйста, попробуйте снова или отправьте текстовый запрос.")
            return ConversationHandler.END
        
        # Сохраняем распознанный текст в контексте
        context.user_data["user_request"] = transcription
        context.user_data["request_type"] = "voice"
        
        # Информируем пользователя о распознанном тексте
        await message.edit_text(f"🎤 Распознанный текст:\n\n{transcription}\n\n⏳ Генерирую промпт...")
        
        # Получаем ID пользователя для использования выбранной модели
        user_id = update.effective_user.id
        
        # Генерируем промпт через ChatGPT с использованием выбранной модели
        prompt = await generate_prompt(transcription, user_id)
        if not prompt:
            await message.edit_text("Произошла ошибка при создании промпта. Пожалуйста, попробуйте позже.")
            return ConversationHandler.END
        
        # Сохраняем промпт в контексте
        context.user_data["prompt"] = prompt
        
        return await show_prompt_confirmation(update, context, message, prompt)
        
    except Exception as e:
        logger.error(f"Произошла ошибка при обработке голосового сообщения: {e}")
        await message.edit_text("Произошла ошибка при обработке голосового сообщения. Пожалуйста, попробуйте позже.")
        return ConversationHandler.END

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает сообщения с фотографиями."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
        
    # Сообщаем пользователю, что запрос обрабатывается
    message = await update.message.reply_text("🖼 Анализирую изображение...")
    
    try:
        # Проверяем, есть ли фото в сообщении
        if not update.message.photo or len(update.message.photo) == 0:
            logger.error("В сообщении нет фотографий")
            await message.edit_text("⚠️ Не удалось обработать изображение. Пожалуйста, отправьте другое фото.")
            return ConversationHandler.END
        
        # Получаем размер фото для логирования
        photo_size = update.message.photo[-1].file_size
        logger.info(f"Получено изображение размером {photo_size} байт")
        
        # Получаем файл изображения (берем с наилучшим качеством)
        photo_file = await update.message.photo[-1].get_file()
        
        # Создаем временный файл для сохранения изображения
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_photo:
            photo_path = temp_photo.name
        
        # Загружаем изображение
        await photo_file.download_to_drive(photo_path)
        logger.info(f"Изображение сохранено во временный файл: {photo_path}")
        
        # Проверяем, что файл существует и не пустой
        if not os.path.exists(photo_path) or os.path.getsize(photo_path) == 0:
            logger.error(f"Проблема с сохранением изображения: файл не создан или пустой")
            await message.edit_text("⚠️ Произошла ошибка при сохранении изображения. Пожалуйста, попробуйте еще раз.")
            
            # Попытка удаления временного файла, если он существует
            if os.path.exists(photo_path):
                os.remove(photo_path)
                
            return ConversationHandler.END
        
        # Получаем ID пользователя для использования выбранной модели
        user_id = update.effective_user.id
        
        # Анализируем содержимое изображения с использованием выбранной модели
        image_description = await analyze_image_content(photo_path, user_id)
        
        # Удаляем временный файл
        try:
            os.remove(photo_path)
            logger.info(f"Временный файл удален: {photo_path}")
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл: {e}")
        
        if not image_description:
            await message.edit_text("⚠️ Не удалось проанализировать изображение. Пожалуйста, попробуйте другое изображение или отправьте текстовый запрос.")
            return ConversationHandler.END
        
        # Сохраняем описание изображения в контексте
        context.user_data["user_request"] = image_description
        context.user_data["request_type"] = "image"
        
        # Информируем пользователя о том, что изображение проанализировано
        await message.edit_text("🖼 Изображение проанализировано. Генерирую промпт...")
        
        # Генерируем промпт на основе описания изображения с использованием выбранной модели
        prompt = await analyze_image(image_description, user_id)
        if not prompt:
            await message.edit_text("Произошла ошибка при создании промпта. Пожалуйста, попробуйте позже.")
            return ConversationHandler.END
        
        # Сохраняем промпт в контексте
        context.user_data["prompt"] = prompt
        
        return await show_prompt_confirmation(update, context, message, prompt)
        
    except Exception as e:
        logger.error(f"Произошла ошибка при обработке фотографии: {e}")
        await message.edit_text("Произошла ошибка при анализе изображения. Пожалуйста, попробуйте позже.")
        return ConversationHandler.END

async def show_prompt_confirmation(update: Update, context, message, prompt):
    """Показывает запрос на подтверждение промпта."""
    # Создаем клавиатуру для подтверждения
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, сгенерировать", callback_data="prompt_ok"),
            InlineKeyboardButton("🔄 Повторить", callback_data="prompt_retry")
        ],
        [InlineKeyboardButton("❌ Отменить", callback_data="prompt_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    request_type_icon = {
        "text": "📝",
        "voice": "🎤",
        "image": "🖼"
    }.get(context.user_data.get("request_type", "text"), "📝")
    
    # Отображаем промпт и запрашиваем подтверждение
    await message.edit_text(
        f"{request_type_icon} *Ваш запрос:*\n{context.user_data.get('user_request', '')[:100]}...\n\n"
        f"🧠 *Сгенерированный промпт:*\n`{prompt}`\n\n"
        f"Начать генерацию с этим промптом?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return AWAITING_CONFIRMATION

async def prompt_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответ пользователя на подтверждение промпта."""
    query = update.callback_query
    await query.answer()
    
    try:
        # Проверяем корректность callback_data
        if query.data not in ["prompt_ok", "prompt_retry", "prompt_cancel"]:
            logger.error(f"Неожиданный формат callback_data: {query.data}")
            await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
        
        if query.data == "prompt_ok":
            # Пользователь подтвердил промпт, начинаем генерацию
            user_id = query.from_user.id
            settings = get_user_settings(user_id)
            cycles = settings.get("generation_cycles", 1)
            
            # Получаем исходный запрос и промпт
            user_request = context.user_data.get("user_request")
            prompt = context.user_data.get("prompt")
            request_type = context.user_data.get("request_type", "text")
            
            # Проверяем, что запрос и промпт существуют
            if not user_request or not prompt:
                await query.message.edit_text("Произошла ошибка: запрос или промпт не найдены. Пожалуйста, попробуйте снова.")
                return ConversationHandler.END
            
            # Удаляем сообщение о подтверждении
            await query.message.delete()
            
            # Отправляем сообщение о начале генерации
            status_message = await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"🎨 Начинаю генерацию изображений ({cycles} цикл{'ов' if cycles > 1 else ''})..."
            )
            
            # Генерируем изображения в нескольких циклах
            for cycle in range(1, cycles + 1):
                if cycles > 1:
                    await status_message.edit_text(f"🎨 Цикл {cycle}/{cycles}: генерирую промпт...")
                    
                    # В каждом цикле (кроме первого) генерируем новый промпт
                    if cycle > 1:
                        if request_type == "image":
                            prompt = await analyze_image(user_request, user_id)
                        else:
                            prompt = await generate_prompt(user_request, user_id)
                            
                        if not prompt:
                            await status_message.edit_text(f"⚠️ Ошибка при генерации промпта в цикле {cycle}. Пропускаю...")
                            continue
                
                # Обновляем статус
                if cycles > 1:
                    await status_message.edit_text(f"🎨 Цикл {cycle}/{cycles}: генерирую изображение (это может занять до 3 минут)...")
                else:
                    await status_message.edit_text("🎨 Генерирую изображение (это может занять до 3 минут)...")
                
                # Генерируем изображение
                image_urls = await generate_image(prompt, user_id)
                if not image_urls:
                    if cycles > 1:
                        await status_message.edit_text(f"⚠️ Ошибка при генерации изображения в цикле {cycle}. Пропускаю...")
                        continue
                    else:
                        await status_message.edit_text("Произошла ошибка при генерации изображения. Пожалуйста, попробуйте позже.")
                        return ConversationHandler.END
                
                # Отправляем все сгенерированные изображения
                for url in image_urls:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=url)
                
                # Отправляем использованный промпт для справки
                cycle_text = f" (цикл {cycle}/{cycles})" if cycles > 1 else ""
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Использованный промпт{cycle_text}:\n`{prompt}`",
                    parse_mode="Markdown"
                )
            
            # Удаляем сообщение о статусе
            await status_message.delete()
            
            # Сообщаем о завершении всех циклов
            if cycles > 1:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"✅ Генерация завершена! Сгенерировано {cycles} вариант{'ов' if cycles > 1 else ''}."
                )
            
        elif query.data == "prompt_retry":
            # Пользователь хочет повторно сгенерировать промпт
            await query.message.edit_text("🔄 Генерирую новый промпт...")
            
            user_request = context.user_data.get("user_request")
            if not user_request:
                await query.message.edit_text("Произошла ошибка: запрос не найден. Пожалуйста, попробуйте снова.")
                return ConversationHandler.END
            
            # Получаем ID пользователя для использования выбранной модели
            user_id = update.effective_user.id
            
            # Генерируем новый промпт в зависимости от типа запроса
            request_type = context.user_data.get("request_type", "text")
            if request_type == "image":
                prompt = await analyze_image(user_request, user_id)
            else:
                prompt = await generate_prompt(user_request, user_id)
                
            if not prompt:
                await query.message.edit_text("Произошла ошибка при создании промпта. Пожалуйста, попробуйте позже.")
                return ConversationHandler.END
            
            # Обновляем промпт в контексте
            context.user_data["prompt"] = prompt
            
            # Создаем клавиатуру для подтверждения
            keyboard = [
                [
                    InlineKeyboardButton("✅ Да, сгенерировать", callback_data="prompt_ok"),
                    InlineKeyboardButton("🔄 Повторить", callback_data="prompt_retry")
                ],
                [InlineKeyboardButton("❌ Отменить", callback_data="prompt_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            request_type_icon = {
                "text": "📝",
                "voice": "🎤",
                "image": "🖼"
            }.get(request_type, "📝")
            
            # Отображаем новый промпт и запрашиваем подтверждение
            await query.message.edit_text(
                f"{request_type_icon} *Ваш запрос:*\n{user_request[:100]}...\n\n"
                f"🧠 *Новый промпт:*\n`{prompt}`\n\n"
                f"Начать генерацию с этим промптом?",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
            return AWAITING_CONFIRMATION
            
        elif query.data == "prompt_cancel":
            # Пользователь отменил операцию
            await query.message.edit_text("❌ Операция отменена. Отправьте новый запрос для генерации изображения.")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке callback_data {query.data}: {e}")
        await query.message.edit_text(f"Произошла ошибка при обработке запроса: {str(e)[:100]}... Попробуйте позже или используйте /cancel для сброса.")
    
    return ConversationHandler.END

async def benchmark_prompt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод промпта для прогона параметров."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
    
    # Получаем промпт от пользователя
    prompt = update.message.text
    
    if not prompt or len(prompt) < 10:
        await update.message.reply_text("⚠️ Введен слишком короткий промпт. Пожалуйста, введите более подробное описание.")
        return AWAITING_BENCHMARK_PROMPT
    
    # Информируем пользователя о начале прогона
    status_message = await update.message.reply_text(
        "🔬 *Начинаю прогон параметров*\n\n"
        f"Промпт: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`\n\n"
        "⏳ Генерация началась. Это займет продолжительное время...",
        parse_mode="Markdown"
    )
    
    # Получаем базовые параметры для прогона
    base_params = BENCHMARK_SETTINGS.copy()
    
    # Создаем список комбинаций параметров для прогона
    parameter_combinations = []
    for prompt_strength in BENCHMARK_PROMPT_STRENGTHS:
        for guidance_scale in BENCHMARK_GUIDANCE_SCALES:
            for inference_steps in BENCHMARK_INFERENCE_STEPS:
                parameter_combinations.append({
                    "prompt_strength": prompt_strength,
                    "guidance_scale": guidance_scale,
                    "num_inference_steps": inference_steps
                })
    
    # Ограничиваем количество итераций для безопасности
    if len(parameter_combinations) > MAX_BENCHMARK_ITERATIONS:
        # Выбираем случайные комбинации параметров
        import random
        parameter_combinations = random.sample(parameter_combinations, MAX_BENCHMARK_ITERATIONS)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ Внимание: количество комбинаций параметров ({len(BENCHMARK_PROMPT_STRENGTHS) * len(BENCHMARK_GUIDANCE_SCALES) * len(BENCHMARK_INFERENCE_STEPS)}) слишком велико.\n"
                 f"Будет выполнено {MAX_BENCHMARK_ITERATIONS} случайных комбинаций."
        )
    
    # Запускаем прогон параметров
    try:
        total_iterations = len(parameter_combinations)
        for i, params in enumerate(parameter_combinations, 1):
            # Обновляем статусное сообщение
            await status_message.edit_text(
                f"🔬 *Прогон параметров: {i}/{total_iterations}*\n\n"
                f"• Сила промпта: {params['prompt_strength']}\n"
                f"• Guidance Scale: {params['guidance_scale']}\n"
                f"• Шаги инференса: {params['num_inference_steps']}\n\n"
                "⏳ Генерация изображения...",
                parse_mode="Markdown"
            )
            
            # Собираем все параметры
            generation_params = base_params.copy()
            generation_params.update(params)
            
            # Запускаем генерацию изображения с текущими параметрами
            image_urls = await generate_image_with_params(prompt, generation_params)
            
            if not image_urls:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ Ошибка генерации для комбинации #{i}:\n"
                         f"• Сила промпта: {params['prompt_strength']}\n"
                         f"• Guidance Scale: {params['guidance_scale']}\n"
                         f"• Шаги инференса: {params['num_inference_steps']}"
                )
                continue
            
            # Отправляем изображение с описанием параметров
            caption = (
                f"🔍 *Результат прогона #{i}/{total_iterations}*\n\n"
                f"• Сила промпта: {params['prompt_strength']}\n"
                f"• Guidance Scale: {params['guidance_scale']}\n"
                f"• Шаги инференса: {params['num_inference_steps']}"
            )
            
            # Отправляем сгенерированное изображение
            for url in image_urls:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=url,
                    caption=caption,
                    parse_mode="Markdown"
                )
        
        # Завершаем прогон
        await status_message.edit_text(
            f"✅ *Прогон параметров завершен!*\n\n"
            f"Было сгенерировано {total_iterations} вариантов с разными параметрами.\n"
            f"Выберите наиболее подходящую комбинацию параметров для своих задач.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении прогона параметров: {e}")
        await status_message.edit_text(
            f"❌ *Произошла ошибка при выполнении прогона:*\n{str(e)[:100]}\n\n"
            f"Было выполнено {i-1} из {total_iterations} итераций.",
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END 