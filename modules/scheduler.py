"""
Модуль планировщика фотосессий.
Управление расписанием через python-telegram-bot JobQueue.
"""

import io
from datetime import time, timedelta
from typing import List

from telegram import InputMediaPhoto
from telegram.ext import ContextTypes

from modules.config import logger
from modules.photoshoot import run_photoshoot
from modules.settings import get_user_settings, update_user_settings


# ─────────────────────────────────────────────
# Настройки расписания по умолчанию
# ─────────────────────────────────────────────

DEFAULT_SCHEDULE = {
    "enabled": False,
    "days": [0, 3],          # Понедельник и четверг (0=Mon, 6=Sun)
    "hour": 10,
    "minute": 0,
    "num_photos": 10,
}

DAY_NAMES = {
    0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"
}


# ─────────────────────────────────────────────
# Получение/обновление расписания
# ─────────────────────────────────────────────

def get_schedule(user_id: int) -> dict:
    """Получает расписание фотосессий пользователя."""
    settings = get_user_settings(user_id)
    return settings.get("photoshoot_schedule", DEFAULT_SCHEDULE.copy())


def update_schedule(user_id: int, schedule: dict) -> None:
    """Обновляет расписание фотосессий пользователя."""
    update_user_settings(user_id, "photoshoot_schedule", schedule)


def format_schedule(schedule: dict) -> str:
    """Форматирует расписание для отображения."""
    if not schedule.get("enabled"):
        return "Выключено"

    days = ", ".join(DAY_NAMES.get(d, "?") for d in sorted(schedule.get("days", [])))
    hour = schedule.get("hour", 10)
    minute = schedule.get("minute", 0)
    num = schedule.get("num_photos", 10)

    return f"{days} в {hour:02d}:{minute:02d}, {num} фото"


# ─────────────────────────────────────────────
# Job callback для scheduled фотосессий
# ─────────────────────────────────────────────

async def scheduled_photoshoot_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback для JobQueue — генерирует и отправляет фотосессию.
    job.data = {"chat_id": int, "user_id": int, "num_photos": int}
    """
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    user_id = job_data["user_id"]
    num_photos = job_data.get("num_photos", 10)

    logger.info(f"Scheduled photoshoot для user {user_id}, chat {chat_id}")

    try:
        # Уведомление о старте
        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="Генерация запланированной фотосессии...",
        )

        # Callback для прогресса
        async def progress(current, total, text=""):
            try:
                await status_msg.edit_text(text or f"Генерация {current}/{total}...")
            except Exception:
                pass

        # Генерация
        result = await run_photoshoot(
            num_photos=num_photos,
            progress_callback=progress,
        )

        # Отправка результата
        await send_photoshoot_result(context.bot, chat_id, result)

        # Удаляем статусное сообщение
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Ошибка scheduled photoshoot: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Ошибка генерации фотосессии: {str(e)[:200]}",
        )


# ─────────────────────────────────────────────
# Отправка результата в Telegram
# ─────────────────────────────────────────────

async def send_photoshoot_result(bot, chat_id: int, result: dict) -> None:
    """Отправляет фотосессию: галерея + ZIP."""

    image_bytes_list = result["image_bytes"]
    theme = result["theme"]

    # Отправляем media group (галерея, до 10 фото)
    media_group = []
    for i, img_data in enumerate(image_bytes_list[:10]):
        bio = io.BytesIO(img_data)
        bio.name = f"photo_{i+1:02d}.jpg"

        caption = theme if i == 0 else None
        media_group.append(InputMediaPhoto(media=bio, caption=caption))

    if media_group:
        await bot.send_media_group(chat_id=chat_id, media=media_group)

    # Отправляем ZIP
    zip_data = result["zip_bytes"]
    zip_bio = io.BytesIO(zip_data)
    zip_bio.name = f"{result['session_name']}.zip"

    await bot.send_document(
        chat_id=chat_id,
        document=zip_bio,
        caption=f"ZIP: {theme} ({len(image_bytes_list)} фото, полный размер)",
    )


# ─────────────────────────────────────────────
# Управление scheduled jobs
# ─────────────────────────────────────────────

def setup_scheduled_jobs(application, user_id: int, chat_id: int) -> None:
    """Настраивает scheduled jobs для пользователя на основе его расписания."""
    job_queue = application.job_queue
    job_name = f"photoshoot_{user_id}"

    # Удаляем существующие jobs
    remove_scheduled_jobs(application, user_id)

    schedule = get_schedule(user_id)
    if not schedule.get("enabled"):
        logger.info(f"Расписание для {user_id} выключено, jobs не создаются")
        return

    hour = schedule.get("hour", 10)
    minute = schedule.get("minute", 0)
    days = schedule.get("days", [0, 3])
    num_photos = schedule.get("num_photos", 10)

    job_time = time(hour=hour, minute=minute)

    for day in days:
        job_queue.run_daily(
            scheduled_photoshoot_job,
            time=job_time,
            days=(day,),
            data={"chat_id": chat_id, "user_id": user_id, "num_photos": num_photos},
            name=f"{job_name}_day{day}",
        )
        logger.info(f"Job создан: {job_name}_day{day} в {hour:02d}:{minute:02d}")


def remove_scheduled_jobs(application, user_id: int) -> None:
    """Удаляет все scheduled jobs для пользователя."""
    job_name_prefix = f"photoshoot_{user_id}"
    current_jobs = application.job_queue.get_jobs_by_name(job_name_prefix)

    # get_jobs_by_name ищет по точному имени, поэтому ищем по всем дням
    for day in range(7):
        jobs = application.job_queue.get_jobs_by_name(f"{job_name_prefix}_day{day}")
        for job in jobs:
            job.schedule_removal()
            logger.info(f"Job удалён: {job.name}")
