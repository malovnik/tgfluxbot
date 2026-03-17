"""
Модуль с обработчиками команд и сообщений Telegram бота.
"""

import os
import tempfile
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from modules.config import (
    AWAITING_CONFIRMATION, SETTINGS,
    SETTING_NUM_OUTPUTS, SETTING_ASPECT_RATIO, SETTING_PROMPT_STRENGTH,
    SETTING_GEMINI_MODEL, SETTING_GENERATION_CYCLES, SETTING_AUTO_CONFIRM_PROMPT,
    SETTING_PHOTOSHOOT_SCHEDULE,
    ASPECT_RATIOS, GEMINI_MODELS,
    logger, AUTHORIZED_USERS, BOT_PRIVATE,
    AWAITING_BENCHMARK_PROMPT, BENCHMARK_SETTINGS, BENCHMARK_PROMPT_STRENGTHS,
    BENCHMARK_GUIDANCE_SCALES, BENCHMARK_INFERENCE_STEPS, MAX_BENCHMARK_ITERATIONS,
    AWAITING_BENCHMARK_OPTIONS, AWAITING_BENCHMARK_COUNT
)
from modules.settings import (
    get_user_settings, update_user_settings, reset_user_settings
)
from modules.ai_services import (
    generate_prompt, analyze_image, transcribe_audio,
    analyze_image_content, generate_image, download_file,
    generate_image_with_params
)
from modules.photoshoot import run_photoshoot
from modules.scheduler import (
    get_schedule, update_schedule, format_schedule,
    send_photoshoot_result, setup_scheduled_jobs, remove_scheduled_jobs,
    DAY_NAMES
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
    
    # Проверяем совпадение ID чата или имени пользователя в списке авторизованных пользователей
    is_authorized = False
    
    for auth_user in AUTHORIZED_USERS:
        if user_id == auth_user["chat_id"] or username == auth_user["username"]:
            is_authorized = True
            break
    
    if not is_authorized:
        logger.warning(f"Неавторизованная попытка доступа: user_id={user_id}, username={username}")
    
    return is_authorized

async def send_unauthorized_message(update: Update):
    """Отправляет сообщение о недостаточных правах."""
    await update.message.reply_text(
        "⛔ Извините, но этот бот является приватным.\n\n"
        "Доступ к боту имеют только авторизованные пользователи."
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
        [InlineKeyboardButton("Модель Gemini", callback_data="set_gemini_model")],
        [InlineKeyboardButton("Количество циклов генерации", callback_data="set_generation_cycles")],
        [InlineKeyboardButton("Автоподтверждение промпта", callback_data="set_auto_confirm_prompt")],
        [InlineKeyboardButton("Расписание фотосессий", callback_data="set_photoshoot_schedule")],
        [InlineKeyboardButton("Запустить прогон параметров", callback_data="start_benchmark")],
        [InlineKeyboardButton("Вернуться к стандартным настройкам", callback_data="reset_settings")],
        [InlineKeyboardButton("Закрыть настройки", callback_data="close_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Получаем читаемое название модели Gemini
    gemini_model_name = GEMINI_MODELS.get(settings['gemini_model'], settings['gemini_model'])
    
    # Получаем читаемый статус автоподтверждения промпта
    auto_confirm_status = "Включено ✅" if settings.get('auto_confirm_prompt', False) else "Отключено ❌"
    
    await update.message.reply_text(
        f"📊 *Текущие настройки*:\n\n"
        f"🖼 Количество изображений: {settings['num_outputs']}\n"
        f"📐 Соотношение сторон: {settings['aspect_ratio']}\n"
        f"⚖️ Уровень следования промпту: {settings['prompt_strength']}\n"
        f"🧠 Модель Gemini: {gemini_model_name}\n"
        f"🔄 Циклов генерации: {settings['generation_cycles']}\n"
        f"🔄 Автоподтверждение промпта: {auto_confirm_status}\n\n"
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
            
        elif query.data == "set_aspect_ratio":
            # Формируем клавиатуру для выбора соотношения сторон
            keyboard = []
            for aspect_ratio in ASPECT_RATIOS:
                keyboard.append([InlineKeyboardButton(f"{aspect_ratio}", callback_data=f"aspect_ratio_{aspect_ratio}")])
            keyboard.append([InlineKeyboardButton("Своё значение", callback_data="aspect_ratio_custom")])
            keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение с клавиатурой
            await query.message.edit_text(
                "📐 Выберите соотношение сторон изображения:",
                reply_markup=reply_markup
            )
            
            return SETTING_ASPECT_RATIO
            
        elif query.data == "set_num_outputs":
            # Формируем клавиатуру для выбора количества изображений
            keyboard = []
            for i in range(1, 5):  # От 1 до 4 изображений
                keyboard.append([InlineKeyboardButton(f"{i}", callback_data=f"num_outputs_{i}")])
            keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение с клавиатурой
            await query.message.edit_text(
                "🖼 Выберите количество генерируемых изображений за один запрос:",
                reply_markup=reply_markup
            )
            
            return SETTING_NUM_OUTPUTS
            
        elif query.data == "set_prompt_strength":
            # Формируем клавиатуру для выбора уровня следования промпту
            keyboard = []
            for value in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
                keyboard.append([InlineKeyboardButton(f"{value}", callback_data=f"prompt_strength_{value}")])
            keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение с клавиатурой
            await query.message.edit_text(
                "⚖️ Выберите уровень следования промпту:\n\n"
                "💡 Чем выше значение, тем точнее соответствие изображения запросу, "
                "но меньше креативности. Рекомендуемое значение: 0.7-0.8",
                reply_markup=reply_markup
            )
            
            return SETTING_PROMPT_STRENGTH
            
        elif query.data == "set_gemini_model":
            # Формируем клавиатуру для выбора модели Gemini
            keyboard = []
            for model_id, model_name in GEMINI_MODELS.items():
                keyboard.append([InlineKeyboardButton(f"{model_name}", callback_data=f"gemini_model_{model_id}")])
            keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение с клавиатурой
            await query.message.edit_text(
                "🧠 Выберите модель Gemini для анализа запросов:",
                reply_markup=reply_markup
            )
            
            return SETTING_GEMINI_MODEL
            
        elif query.data == "set_generation_cycles":
            # Формируем клавиатуру для выбора количества циклов генерации
            keyboard = []
            for i in range(1, 6):  # От 1 до 5 циклов
                keyboard.append([InlineKeyboardButton(f"{i}", callback_data=f"generation_cycles_{i}")])
            keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение с клавиатурой
            await query.message.edit_text(
                "🔄 Выберите количество циклов генерации:\n\n"
                "💡 При выборе нескольких циклов для каждого запроса будет "
                "генерироваться несколько разных промптов и изображений.",
                reply_markup=reply_markup
            )
            
            return SETTING_GENERATION_CYCLES
            
        elif query.data == "set_auto_confirm_prompt":
            # Формируем клавиатуру для настройки автоподтверждения промпта
            keyboard = []
            keyboard.append([InlineKeyboardButton("Включить ✅", callback_data="auto_confirm_true")])
            keyboard.append([InlineKeyboardButton("Отключить ❌", callback_data="auto_confirm_false")])
            keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение с клавиатурой
            await query.message.edit_text(
                "🔄 Настройка автоматического подтверждения промпта:\n\n"
                "💡 Если включено, промпт будет автоматически отправляться на генерацию "
                "без запроса на подтверждение.",
                reply_markup=reply_markup
            )
            
            return SETTING_AUTO_CONFIRM_PROMPT
            
        elif query.data == "set_photoshoot_schedule":
            schedule = get_schedule(user_id)
            await _show_schedule_menu(query, schedule)
            return SETTING_PHOTOSHOOT_SCHEDULE

        elif query.data == "start_benchmark":
            # Запрашиваем у пользователя промпт для прогона параметров
            await query.message.edit_text(
                "🔬 *Запуск режима прогона параметров*\n\n"
                "Введите промпт (описание изображения), которое хотите использовать для тестирования "
                "различных параметров генерации.\n\n"
                "Промпт будет использован для создания нескольких вариантов изображения с разными настройками.",
                parse_mode="Markdown"
            )
            
            return AWAITING_BENCHMARK_PROMPT
    
    except Exception as e:
        logger.error(f"Ошибка при обработке настроек: {e}")
        await query.message.edit_text(f"Произошла ошибка при обработке запроса: {str(e)[:100]}... Попробуйте позже или используйте /cancel для сброса.")
    
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
        
        # Показываем сообщение о подтверждении
        await query.message.edit_text(f"✅ Количество изображений успешно установлено: {num_outputs}")
        
        # Добавляем задержку и возвращаемся к меню настроек
        await asyncio.sleep(1)

        # Обновляем сообщение, заменяя его на меню настроек
        settings = get_user_settings(user_id)
        keyboard = [
            [InlineKeyboardButton("Количество изображений", callback_data="set_num_outputs")],
            [InlineKeyboardButton("Соотношение сторон", callback_data="set_aspect_ratio")],
            [InlineKeyboardButton("Уровень следования промпту", callback_data="set_prompt_strength")],
            [InlineKeyboardButton("Модель Gemini", callback_data="set_gemini_model")],
            [InlineKeyboardButton("Количество циклов генерации", callback_data="set_generation_cycles")],
            [InlineKeyboardButton("🔬 Запустить прогон параметров", callback_data="start_benchmark")],
            [InlineKeyboardButton("Вернуться к стандартным настройкам", callback_data="reset_settings")],
            [InlineKeyboardButton("Закрыть настройки", callback_data="close_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем читаемое название модели Gemini
        gemini_model_name = GEMINI_MODELS.get(settings['gemini_model'], settings['gemini_model'])
        
        await query.message.edit_text(
            f"📊 *Текущие настройки*:\n\n"
            f"🖼 Количество изображений: {settings['num_outputs']}\n"
            f"📐 Соотношение сторон: {settings['aspect_ratio']}\n"
            f"⚖️ Уровень следования промпту: {settings['prompt_strength']}\n"
            f"🧠 Модель Gemini: {gemini_model_name}\n"
            f"🔄 Циклов генерации: {settings['generation_cycles']}\n\n"
            f"Выберите параметр для изменения:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SETTINGS
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
                
                # Обновляем сообщение, заменяя его на меню настроек
                settings = get_user_settings(user_id)
                keyboard = [
                    [InlineKeyboardButton("Количество изображений", callback_data="set_num_outputs")],
                    [InlineKeyboardButton("Соотношение сторон", callback_data="set_aspect_ratio")],
                    [InlineKeyboardButton("Уровень следования промпту", callback_data="set_prompt_strength")],
                    [InlineKeyboardButton("Модель Gemini", callback_data="set_gemini_model")],
                    [InlineKeyboardButton("Количество циклов генерации", callback_data="set_generation_cycles")],
                    [InlineKeyboardButton("🔬 Запустить прогон параметров", callback_data="start_benchmark")],
                    [InlineKeyboardButton("Вернуться к стандартным настройкам", callback_data="reset_settings")],
                    [InlineKeyboardButton("Закрыть настройки", callback_data="close_settings")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Получаем читаемое название модели Gemini
                gemini_model_name = GEMINI_MODELS.get(settings['gemini_model'], settings['gemini_model'])
                
                await query.message.edit_text(
                    f"📊 *Текущие настройки*:\n\n"
                    f"🖼 Количество изображений: {settings['num_outputs']}\n"
                    f"📐 Соотношение сторон: {settings['aspect_ratio']}\n"
                    f"⚖️ Уровень следования промпту: {settings['prompt_strength']}\n"
                    f"🧠 Модель Gemini: {gemini_model_name}\n"
                    f"🔄 Циклов генерации: {settings['generation_cycles']}\n\n"
                    f"Выберите параметр для изменения:",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
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
        
        # Показываем подтверждение
        message = await update.message.reply_text(
            f"✅ Соотношение сторон установлено: {user_input}\n"
            "Настройка применена успешно!"
        )
        
        # Добавляем задержку
        await asyncio.sleep(1)
        
        # Обновляем сообщение, заменяя его на меню настроек
        settings = get_user_settings(user_id)
        keyboard = [
            [InlineKeyboardButton("Количество изображений", callback_data="set_num_outputs")],
            [InlineKeyboardButton("Соотношение сторон", callback_data="set_aspect_ratio")],
            [InlineKeyboardButton("Уровень следования промпту", callback_data="set_prompt_strength")],
            [InlineKeyboardButton("Модель Gemini", callback_data="set_gemini_model")],
            [InlineKeyboardButton("Количество циклов генерации", callback_data="set_generation_cycles")],
            [InlineKeyboardButton("🔬 Запустить прогон параметров", callback_data="start_benchmark")],
            [InlineKeyboardButton("Вернуться к стандартным настройкам", callback_data="reset_settings")],
            [InlineKeyboardButton("Закрыть настройки", callback_data="close_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем читаемое название модели Gemini
        gemini_model_name = GEMINI_MODELS.get(settings['gemini_model'], settings['gemini_model'])
        
        await update.message.reply_text(
            f"📊 *Текущие настройки*:\n\n"
            f"🖼 Количество изображений: {settings['num_outputs']}\n"
            f"📐 Соотношение сторон: {settings['aspect_ratio']}\n"
            f"⚖️ Уровень следования промпту: {settings['prompt_strength']}\n"
            f"🧠 Модель Gemini: {gemini_model_name}\n"
            f"🔄 Циклов генерации: {settings['generation_cycles']}\n\n"
            f"Выберите параметр для изменения:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
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
        
        # Показываем подтверждение
        await query.message.edit_text(f"✅ Уровень следования промпту успешно установлен: {prompt_strength}")
        
        # Добавляем задержку
        await asyncio.sleep(1)
        
        # Обновляем сообщение, заменяя его на меню настроек
        settings = get_user_settings(user_id)
        keyboard = [
            [InlineKeyboardButton("Количество изображений", callback_data="set_num_outputs")],
            [InlineKeyboardButton("Соотношение сторон", callback_data="set_aspect_ratio")],
            [InlineKeyboardButton("Уровень следования промпту", callback_data="set_prompt_strength")],
            [InlineKeyboardButton("Модель Gemini", callback_data="set_gemini_model")],
            [InlineKeyboardButton("Количество циклов генерации", callback_data="set_generation_cycles")],
            [InlineKeyboardButton("🔬 Запустить прогон параметров", callback_data="start_benchmark")],
            [InlineKeyboardButton("Вернуться к стандартным настройкам", callback_data="reset_settings")],
            [InlineKeyboardButton("Закрыть настройки", callback_data="close_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем читаемое название модели Gemini
        gemini_model_name = GEMINI_MODELS.get(settings['gemini_model'], settings['gemini_model'])
        
        await query.message.edit_text(
            f"📊 *Текущие настройки*:\n\n"
            f"🖼 Количество изображений: {settings['num_outputs']}\n"
            f"📐 Соотношение сторон: {settings['aspect_ratio']}\n"
            f"⚖️ Уровень следования промпту: {settings['prompt_strength']}\n"
            f"🧠 Модель Gemini: {gemini_model_name}\n"
            f"🔄 Циклов генерации: {settings['generation_cycles']}\n\n"
            f"Выберите параметр для изменения:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SETTINGS
    except Exception as e:
        logger.error(f"Ошибка при обработке callback_data {query.data}: {e}")
        await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
        return ConversationHandler.END

async def gemini_model_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор модели Gemini."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "back_to_settings":
        return await settings_command(update, context)
    
    try:
        # Проверяем формат callback_data перед обработкой
        if not query.data.startswith("gemini_model_"):
            logger.error(f"Неожиданный формат callback_data: {query.data}")
            await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
            
        # Извлекаем модель из callback_data
        model_id = query.data.replace("gemini_model_", "")
        
        if model_id not in GEMINI_MODELS:
            logger.error(f"Неизвестная модель Gemini: {model_id}")
            await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
            
        update_user_settings(user_id, "gemini_model", model_id)
        model_name = GEMINI_MODELS.get(model_id, model_id)
        
        # Показываем подтверждение
        await query.message.edit_text(f"✅ Модель Gemini успешно установлена: {model_name}")
        
        # Добавляем задержку
        await asyncio.sleep(1)
        
        # Обновляем сообщение, заменяя его на меню настроек
        settings = get_user_settings(user_id)
        keyboard = [
            [InlineKeyboardButton("Количество изображений", callback_data="set_num_outputs")],
            [InlineKeyboardButton("Соотношение сторон", callback_data="set_aspect_ratio")],
            [InlineKeyboardButton("Уровень следования промпту", callback_data="set_prompt_strength")],
            [InlineKeyboardButton("Модель Gemini", callback_data="set_gemini_model")],
            [InlineKeyboardButton("Количество циклов генерации", callback_data="set_generation_cycles")],
            [InlineKeyboardButton("🔬 Запустить прогон параметров", callback_data="start_benchmark")],
            [InlineKeyboardButton("Вернуться к стандартным настройкам", callback_data="reset_settings")],
            [InlineKeyboardButton("Закрыть настройки", callback_data="close_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем читаемое название модели Gemini
        gemini_model_name = GEMINI_MODELS.get(settings['gemini_model'], settings['gemini_model'])
        
        await query.message.edit_text(
            f"📊 *Текущие настройки*:\n\n"
            f"🖼 Количество изображений: {settings['num_outputs']}\n"
            f"📐 Соотношение сторон: {settings['aspect_ratio']}\n"
            f"⚖️ Уровень следования промпту: {settings['prompt_strength']}\n"
            f"🧠 Модель Gemini: {gemini_model_name}\n"
            f"🔄 Циклов генерации: {settings['generation_cycles']}\n\n"
            f"Выберите параметр для изменения:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SETTINGS
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
        
        # Показываем подтверждение
        await query.message.edit_text(f"✅ Количество циклов генерации успешно установлено: {cycles}")
        
        # Добавляем задержку
        await asyncio.sleep(1)
        
        # Обновляем сообщение, заменяя его на меню настроек
        settings = get_user_settings(user_id)
        keyboard = [
            [InlineKeyboardButton("Количество изображений", callback_data="set_num_outputs")],
            [InlineKeyboardButton("Соотношение сторон", callback_data="set_aspect_ratio")],
            [InlineKeyboardButton("Уровень следования промпту", callback_data="set_prompt_strength")],
            [InlineKeyboardButton("Модель Gemini", callback_data="set_gemini_model")],
            [InlineKeyboardButton("Количество циклов генерации", callback_data="set_generation_cycles")],
            [InlineKeyboardButton("🔬 Запустить прогон параметров", callback_data="start_benchmark")],
            [InlineKeyboardButton("Вернуться к стандартным настройкам", callback_data="reset_settings")],
            [InlineKeyboardButton("Закрыть настройки", callback_data="close_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем читаемое название модели Gemini
        gemini_model_name = GEMINI_MODELS.get(settings['gemini_model'], settings['gemini_model'])
        
        await query.message.edit_text(
            f"📊 *Текущие настройки*:\n\n"
            f"🖼 Количество изображений: {settings['num_outputs']}\n"
            f"📐 Соотношение сторон: {settings['aspect_ratio']}\n"
            f"⚖️ Уровень следования промпту: {settings['prompt_strength']}\n"
            f"🧠 Модель Gemini: {gemini_model_name}\n"
            f"🔄 Циклов генерации: {settings['generation_cycles']}\n\n"
            f"Выберите параметр для изменения:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SETTINGS
    except Exception as e:
        logger.error(f"Ошибка при обработке callback_data {query.data}: {e}")
        await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
        return ConversationHandler.END

async def auto_confirm_prompt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает настройку автоматического подтверждения промптов."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "back_to_settings":
        return await settings_command(update, context)
    
    try:
        # Проверяем формат callback_data перед обработкой
        if not query.data.startswith("auto_confirm_"):
            logger.error(f"Неожиданный формат callback_data: {query.data}")
            await query.message.edit_text("Произошла ошибка. Используйте /cancel и повторите попытку.")
            return ConversationHandler.END
            
        # Извлекаем значение из callback_data
        auto_confirm = query.data == "auto_confirm_true"
        update_user_settings(user_id, "auto_confirm_prompt", auto_confirm)
        
        # Показываем подтверждение
        status = "включено" if auto_confirm else "отключено"
        await query.message.edit_text(f"✅ Автоматическое подтверждение промптов {status}")
        
        # Добавляем задержку
        await asyncio.sleep(1)
        
        # Получаем обновленные настройки пользователя
        settings = get_user_settings(user_id)
        
        # Создаем клавиатуру для возврата в меню настроек
        keyboard = [
            [InlineKeyboardButton("Количество изображений", callback_data="set_num_outputs")],
            [InlineKeyboardButton("Соотношение сторон", callback_data="set_aspect_ratio")],
            [InlineKeyboardButton("Уровень следования промпту", callback_data="set_prompt_strength")],
            [InlineKeyboardButton("Модель Gemini", callback_data="set_gemini_model")],
            [InlineKeyboardButton("Количество циклов генерации", callback_data="set_generation_cycles")],
            [InlineKeyboardButton("Автоподтверждение промпта", callback_data="set_auto_confirm_prompt")],
            [InlineKeyboardButton("🔬 Запустить прогон параметров", callback_data="start_benchmark")],
            [InlineKeyboardButton("Вернуться к стандартным настройкам", callback_data="reset_settings")],
            [InlineKeyboardButton("Закрыть настройки", callback_data="close_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Получаем читаемое название модели Gemini
        gemini_model_name = GEMINI_MODELS.get(settings['gemini_model'], settings['gemini_model'])
        
        # Получаем читаемый статус автоподтверждения промпта
        auto_confirm_status = "Включено ✅" if settings['auto_confirm_prompt'] else "Отключено ❌"
        
        await query.message.edit_text(
            f"📊 *Текущие настройки*:\n\n"
            f"🖼 Количество изображений: {settings['num_outputs']}\n"
            f"📐 Соотношение сторон: {settings['aspect_ratio']}\n"
            f"⚖️ Уровень следования промпту: {settings['prompt_strength']}\n"
            f"🧠 Модель Gemini: {gemini_model_name}\n"
            f"🔄 Циклов генерации: {settings['generation_cycles']}\n"
            f"🔄 Автоподтверждение промпта: {auto_confirm_status}\n\n"
            f"Выберите параметр для изменения:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SETTINGS
        
    except Exception as e:
        logger.error(f"Ошибка при настройке автоподтверждения промпта: {e}")
        await query.message.edit_text(
            f"❌ Произошла ошибка при настройке автоподтверждения промпта.\n"
            f"Ошибка: {str(e)[:100]}...\n\n"
            f"Пожалуйста, попробуйте еще раз или используйте /cancel для сброса."
        )
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
        
        # Генерируем промпт через Gemini
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
        
        # Генерируем промпт через Gemini с использованием выбранной модели
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
    # Получаем настройки пользователя
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    
    # Если включено автоматическое подтверждение, сразу запускаем генерацию
    if settings.get("auto_confirm_prompt", False):
        # Для автоматического подтверждения используем те же действия что и при callback_data="prompt_ok"
        # Сообщаем о начале генерации
        await message.edit_text("🎨 Начинаю генерацию изображений...")
        
        # Получаем исходный запрос и промпт
        user_request = context.user_data.get("user_request")
        request_type = context.user_data.get("request_type", "text")
        cycles = settings.get("generation_cycles", 1)
        
        # Генерируем изображения в нескольких циклах
        for cycle in range(1, cycles + 1):
            if cycles > 1:
                await message.edit_text(f"🎨 Цикл {cycle}/{cycles}: генерирую промпт...")
                
                # В каждом цикле (кроме первого) генерируем новый промпт
                if cycle > 1:
                    if request_type == "image":
                        prompt = await analyze_image(user_request, user_id)
                    else:
                        prompt = await generate_prompt(user_request, user_id)
                        
                    if not prompt:
                        await message.edit_text(f"⚠️ Ошибка при генерации промпта в цикле {cycle}. Пропускаю...")
                        continue
            
            # Обновляем статус
            if cycles > 1:
                await message.edit_text(f"🎨 Цикл {cycle}/{cycles}: генерирую изображение (это может занять до 3 минут)...")
            else:
                await message.edit_text("🎨 Генерирую изображение (это может занять до 3 минут)...")
            
            # Генерируем изображение
            image_urls = await generate_image(prompt, user_id)
            if not image_urls:
                if cycles > 1:
                    await message.edit_text(f"⚠️ Ошибка при генерации изображения в цикле {cycle}. Пропускаю...")
                    continue
                else:
                    await message.edit_text("Произошла ошибка при генерации изображения. Пожалуйста, попробуйте позже.")
                    return ConversationHandler.END
            
            # Отправляем все сгенерированные изображения
            for url in image_urls:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=url)

            # Отправляем использованный промпт для справки (обрезаем если слишком длинный)
            cycle_text = f" (цикл {cycle}/{cycles})" if cycles > 1 else ""
            max_prompt_length = 1000
            prompt_display = prompt if len(prompt) <= max_prompt_length else prompt[:max_prompt_length] + "..."

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Использованный промпт{cycle_text}:\n`{prompt_display}`",
                parse_mode="Markdown",
                read_timeout=30,
                write_timeout=30
            )
        
        # Удаляем сообщение о статусе
        await message.delete()
        
        # Сообщаем о завершении всех циклов
        if cycles > 1:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Генерация завершена! Сгенерировано {cycles} вариант{'ов' if cycles > 1 else ''}."
            )
            
        return ConversationHandler.END
    
    # Иначе показываем запрос на подтверждение промпта как обычно
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
                # В каждом цикле (кроме первого) генерируем новый промпт
                if cycles > 1 and cycle > 1:
                    await status_message.edit_text(f"🎨 Цикл {cycle}/{cycles}: генерирую промпт...")

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

                # Отправляем использованный промпт для справки (обрезаем если слишком длинный)
                cycle_text = f" (цикл {cycle}/{cycles})" if cycles > 1 else ""
                max_prompt_length = 1000
                prompt_display = prompt if len(prompt) <= max_prompt_length else prompt[:max_prompt_length] + "..."

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Использованный промпт{cycle_text}:\n`{prompt_display}`",
                    parse_mode="Markdown",
                    read_timeout=30,
                    write_timeout=30
                )

            # Удаляем сообщение о статусе
            await status_message.delete()

            # Сообщаем о завершении всех циклов
            if cycles > 1:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"✅ Генерация завершена! Сгенерировано {cycles} вариант{'ов' if cycles > 1 else ''}."
                )

            # ВАЖНО: Завершаем разговор после генерации изображений
            return ConversationHandler.END

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
            return ConversationHandler.END

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
    
    # Сохраняем промпт в контексте для дальнейшего использования
    context.user_data["benchmark_prompt"] = prompt
    
    # Рассчитываем общее количество возможных комбинаций
    total_combinations = len(BENCHMARK_PROMPT_STRENGTHS) * len(BENCHMARK_GUIDANCE_SCALES) * len(BENCHMARK_INFERENCE_STEPS)
    
    # Создаем клавиатуру с вариантами действий
    keyboard = [
        [InlineKeyboardButton(f"Выполнить все комбинации ({total_combinations})", callback_data="run_all_combinations")],
        [InlineKeyboardButton("Указать количество случайных комбинаций", callback_data="set_combinations_count")],
        [InlineKeyboardButton("◀️ Назад к настройкам", callback_data="back_to_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔬 *Выбор режима прогона параметров*\n\n"
        f"Промпт: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`\n\n"
        f"Всего возможных комбинаций параметров: {total_combinations}\n\n"
        f"• Сила промпта: {len(BENCHMARK_PROMPT_STRENGTHS)} значений (0.5-1.0)\n"
        f"• Guidance Scale: {len(BENCHMARK_GUIDANCE_SCALES)} значения (2.0-3.5)\n"
        f"• Шаги инференса: {len(BENCHMARK_INFERENCE_STEPS)} значения (20-50)\n\n"
        f"Выберите режим прогона параметров:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return AWAITING_BENCHMARK_OPTIONS

async def benchmark_options_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор режима прогона параметров."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "back_to_settings":
        return await settings_command(update, context)
    
    # Получаем промпт из контекста
    prompt = context.user_data.get("benchmark_prompt")
    if not prompt:
        await query.message.edit_text("❌ Произошла ошибка: промпт не найден. Пожалуйста, начните заново.")
        return ConversationHandler.END
    
    # Рассчитываем общее количество возможных комбинаций
    total_combinations = len(BENCHMARK_PROMPT_STRENGTHS) * len(BENCHMARK_GUIDANCE_SCALES) * len(BENCHMARK_INFERENCE_STEPS)
    
    if query.data == "run_all_combinations":
        # Проверяем, не превышает ли количество комбинаций максимально допустимое
        if total_combinations > MAX_BENCHMARK_ITERATIONS:
            await query.message.edit_text(
                f"⚠️ Количество комбинаций ({total_combinations}) превышает максимально допустимое значение ({MAX_BENCHMARK_ITERATIONS}).\n"
                f"Пожалуйста, используйте опцию указания количества случайных комбинаций."
            )
            # Возвращаем пользователя к выбору режима
            keyboard = [
                [InlineKeyboardButton(f"Выполнить все комбинации ({total_combinations})", callback_data="run_all_combinations")],
                [InlineKeyboardButton("Указать количество случайных комбинаций", callback_data="set_combinations_count")],
                [InlineKeyboardButton("◀️ Назад к настройкам", callback_data="back_to_settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                f"🔬 *Выбор режима прогона параметров*\n\n"
                f"Промпт: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`\n\n"
                f"Всего возможных комбинаций параметров: {total_combinations}\n\n"
                f"• Сила промпта: {len(BENCHMARK_PROMPT_STRENGTHS)} значений (0.5-1.0)\n"
                f"• Guidance Scale: {len(BENCHMARK_GUIDANCE_SCALES)} значения (2.0-3.5)\n"
                f"• Шаги инференса: {len(BENCHMARK_INFERENCE_STEPS)} значения (20-50)\n\n"
                f"Выберите режим прогона параметров:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return AWAITING_BENCHMARK_OPTIONS
        
        # Если количество комбинаций допустимо, запускаем прогон всех комбинаций
        context.user_data["benchmark_iterations"] = total_combinations
        await query.message.edit_text(
            f"✅ Выбран режим прогона всех комбинаций параметров ({total_combinations}).\n"
            f"Начинаю генерацию..."
        )
        return await run_benchmark(update, context, prompt, total_combinations)
        
    elif query.data == "set_combinations_count":
        await query.message.edit_text(
            f"📊 *Ввод количества случайных комбинаций*\n\n"
            f"Всего возможных комбинаций: {total_combinations}\n"
            f"Максимально допустимое количество: {MAX_BENCHMARK_ITERATIONS}\n\n"
            f"Пожалуйста, введите желаемое количество случайных комбинаций параметров (от 1 до {min(total_combinations, MAX_BENCHMARK_ITERATIONS)}):"
        )
        return AWAITING_BENCHMARK_COUNT
    
    return AWAITING_BENCHMARK_OPTIONS

async def benchmark_count_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод количества случайных комбинаций для прогона параметров."""
    # Проверяем авторизацию
    if not await check_authorization(update):
        await send_unauthorized_message(update)
        return ConversationHandler.END
    
    try:
        # Получаем промпт из контекста
        prompt = context.user_data.get("benchmark_prompt")
        if not prompt:
            await update.message.reply_text("❌ Произошла ошибка: промпт не найден. Пожалуйста, начните заново.")
            return ConversationHandler.END
        
        # Рассчитываем общее количество возможных комбинаций
        total_combinations = len(BENCHMARK_PROMPT_STRENGTHS) * len(BENCHMARK_GUIDANCE_SCALES) * len(BENCHMARK_INFERENCE_STEPS)
        max_iterations = min(total_combinations, MAX_BENCHMARK_ITERATIONS)
        
        # Пытаемся преобразовать ввод пользователя в число
        try:
            count = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text(
                "⚠️ Пожалуйста, введите корректное число."
            )
            return AWAITING_BENCHMARK_COUNT
        
        # Проверяем, что введенное число в допустимых пределах
        if count < 1:
            await update.message.reply_text(
                "⚠️ Количество комбинаций должно быть не менее 1."
            )
            return AWAITING_BENCHMARK_COUNT
        elif count > max_iterations:
            await update.message.reply_text(
                f"⚠️ Введенное количество ({count}) превышает максимально допустимое ({max_iterations}).\n"
                f"Будет использовано максимально допустимое значение: {max_iterations}."
            )
            count = max_iterations
        
        # Сохраняем количество комбинаций в контексте
        context.user_data["benchmark_iterations"] = count
        
        # Информируем пользователя о начале прогона
        status_message = await update.message.reply_text(
            f"✅ Выбрано количество случайных комбинаций: {count}\n"
            f"Начинаю генерацию..."
        )
        
        return await run_benchmark(update, context, prompt, count)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке количества комбинаций: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка: {str(e)[:100]}\n"
            "Пожалуйста, попробуйте еще раз или используйте /cancel для отмены."
        )
        return AWAITING_BENCHMARK_COUNT

async def run_benchmark(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str, iterations: int):
    """Запускает прогон параметров с заданным количеством итераций."""
    # Определяем, откуда пришел запрос - из сообщения или из коллбэка
    if update.callback_query:
        chat_id = update.callback_query.message.chat_id
        status_message = await context.bot.send_message(
            chat_id=chat_id,
            text="🔬 *Начинаю прогон параметров*\n\n"
                f"Промпт: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`\n\n"
                "⏳ Генерация началась. Это займет продолжительное время...",
            parse_mode="Markdown"
        )
    else:
        chat_id = update.effective_chat.id
        status_message = await update.message.reply_text(
            "🔬 *Начинаю прогон параметров*\n\n"
            f"Промпт: `{prompt[:100]}{'...' if len(prompt) > 100 else ''}`\n\n"
            "⏳ Генерация началась. Это займет продолжительное время...",
            parse_mode="Markdown"
        )
    
    # Получаем базовые параметры для прогона
    base_params = BENCHMARK_SETTINGS.copy()
    
    # Создаем список всех возможных комбинаций параметров для прогона
    all_parameter_combinations = []
    for prompt_strength in BENCHMARK_PROMPT_STRENGTHS:
        for guidance_scale in BENCHMARK_GUIDANCE_SCALES:
            for inference_steps in BENCHMARK_INFERENCE_STEPS:
                all_parameter_combinations.append({
                    "prompt_strength": prompt_strength,
                    "guidance_scale": guidance_scale,
                    "num_inference_steps": inference_steps
                })
    
    # Выбираем нужное количество комбинаций
    parameter_combinations = all_parameter_combinations
    if iterations < len(all_parameter_combinations):
        # Если нужно меньше комбинаций, чем всего возможно, выбираем случайные
        import random
        parameter_combinations = random.sample(all_parameter_combinations, iterations)
    
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
                    chat_id=chat_id,
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
                    chat_id=chat_id,
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


# =================================================================
# Фотосессии
# =================================================================

async def photoshoot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /photoshoot — генерирует фотосессию."""
    if not await check_authorization(update):
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    status_msg = await update.message.reply_text(
        "Подготовка фотосессии (10 фото)...\n"
        "Это займёт 2-5 минут."
    )

    async def progress_callback(current, total, text=""):
        try:
            await status_msg.edit_text(text or f"Генерация {current}/{total}...")
        except Exception:
            pass

    try:
        result = await run_photoshoot(
            num_photos=10,
            progress_callback=progress_callback,
        )

        # Удаляем статусное сообщение
        try:
            await status_msg.delete()
        except Exception:
            pass

        # Отправляем результат
        await send_photoshoot_result(context.bot, chat_id, result)

    except Exception as e:
        logger.error(f"Ошибка фотосессии: {e}")
        await status_msg.edit_text(f"Ошибка: {str(e)[:200]}")


async def photoshoot_schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает настройки расписания фотосессий."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = update.effective_chat.id
    data = query.data

    schedule = get_schedule(user_id)

    if data == "ps_toggle":
        schedule["enabled"] = not schedule.get("enabled", False)
        update_schedule(user_id, schedule)

        if schedule["enabled"]:
            setup_scheduled_jobs(context.application, user_id, chat_id)
        else:
            remove_scheduled_jobs(context.application, user_id)

    elif data.startswith("ps_day_"):
        day = int(data.replace("ps_day_", ""))
        days = schedule.get("days", [0, 3])
        if day in days:
            days.remove(day)
        else:
            days.append(day)
            days.sort()
        schedule["days"] = days
        update_schedule(user_id, schedule)

        if schedule.get("enabled"):
            setup_scheduled_jobs(context.application, user_id, chat_id)

    elif data.startswith("ps_hour_"):
        hour = int(data.replace("ps_hour_", ""))
        schedule["hour"] = hour
        update_schedule(user_id, schedule)

        if schedule.get("enabled"):
            setup_scheduled_jobs(context.application, user_id, chat_id)

    elif data == "ps_back":
        # Возвращаемся в меню настроек
        return await settings_command(update, context)

    # Показываем обновлённое меню расписания
    await _show_schedule_menu(query, schedule)
    return SETTING_PHOTOSHOOT_SCHEDULE


async def _show_schedule_menu(query, schedule: dict):
    """Отображает меню настройки расписания."""
    enabled = schedule.get("enabled", False)
    status_emoji = "ON" if enabled else "OFF"

    keyboard = [
        [InlineKeyboardButton(
            f"{'Выключить' if enabled else 'Включить'} расписание",
            callback_data="ps_toggle"
        )],
    ]

    if enabled:
        # Дни недели
        day_buttons = []
        current_days = schedule.get("days", [0, 3])
        for d, name in DAY_NAMES.items():
            mark = "v " if d in current_days else "  "
            day_buttons.append(
                InlineKeyboardButton(f"{mark}{name}", callback_data=f"ps_day_{d}")
            )
        # По 4 в ряд
        keyboard.append(day_buttons[:4])
        keyboard.append(day_buttons[4:])

        # Время (3 варианта)
        hour = schedule.get("hour", 10)
        time_buttons = []
        for h in [8, 10, 12, 14, 18]:
            mark = "v " if h == hour else "  "
            time_buttons.append(
                InlineKeyboardButton(f"{mark}{h:02d}:00", callback_data=f"ps_hour_{h}")
            )
        keyboard.append(time_buttons[:3])
        keyboard.append(time_buttons[3:])

    keyboard.append([InlineKeyboardButton("Назад", callback_data="ps_back")])

    current_text = format_schedule(schedule)

    await query.message.edit_text(
        f"Расписание фотосессий: {status_emoji}\n"
        f"Текущее: {current_text}\n\n"
        f"Настройте расписание автоматических фотосессий:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
