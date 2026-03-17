"""
Модуль для взаимодействия с AI-сервисами (Google Gemini, fal.ai).
"""

import os
import tempfile
import base64
from typing import Optional, List, Dict, Any
import requests
import fal_client
from google import genai
from google.genai import types

from modules.config import (
    GEMINI_API_KEY, SYSTEM_PROMPT,
    IMAGE_ANALYSIS_PROMPT, DEFAULT_GEMINI_MODEL, MAX_TOKENS,
    TIMEOUT, MAX_RETRIES, logger, FAL_MODEL_ID, FAL_LORA_URL
)
from modules.settings import get_user_settings

# Инициализация клиента Gemini
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


async def generate_prompt(text: str, user_id: int = None) -> Optional[str]:
    """
    Генерирует промпт для создания изображения с помощью Gemini.

    Args:
        text: Запрос пользователя на русском языке
        user_id: ID пользователя для получения настроек

    Returns:
        Промпт на английском языке с префиксом MLVNK или None в случае ошибки
    """
    try:
        model = DEFAULT_GEMINI_MODEL
        if user_id:
            settings = get_user_settings(user_id)
            model = settings.get("gemini_model", DEFAULT_GEMINI_MODEL)

        logger.info(f"Генерация промпта с использованием модели {model}")

        response = gemini_client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=MAX_TOKENS,
            ),
            contents=text,
        )

        prompt = response.text.strip()

        if not prompt.lower().startswith("mlvnk"):
            prompt = f"MLVNK {prompt}"

        return prompt
    except Exception as e:
        logger.error(f"Ошибка при генерации промпта: {e}")
        return None


async def analyze_image(image_description: str, user_id: int = None) -> Optional[str]:
    """
    Генерирует промпт на основе описания изображения.

    Args:
        image_description: Описание изображения
        user_id: ID пользователя для получения настроек

    Returns:
        Промпт для создания похожего изображения с человеком 'MLVNK' или None
    """
    try:
        model = DEFAULT_GEMINI_MODEL
        if user_id:
            settings = get_user_settings(user_id)
            model = settings.get("gemini_model", DEFAULT_GEMINI_MODEL)

        logger.info(f"Анализ изображения с использованием модели {model}")

        response = gemini_client.models.generate_content(
            model=model,
            config=types.GenerateContentConfig(
                system_instruction=IMAGE_ANALYSIS_PROMPT,
                temperature=0.7,
                max_output_tokens=MAX_TOKENS,
            ),
            contents=image_description,
        )

        prompt = response.text.strip()

        if not prompt.lower().startswith("mlvnk"):
            prompt = f"MLVNK {prompt}"

        return prompt
    except Exception as e:
        logger.error(f"Ошибка при анализе изображения: {e}")
        return None


async def transcribe_audio(audio_file_path: str) -> Optional[str]:
    """
    Транскрибирует аудиофайл с помощью Gemini.

    Args:
        audio_file_path: Путь к аудиофайлу

    Returns:
        Транскрибированный текст или None в случае ошибки
    """
    try:
        if not os.path.exists(audio_file_path):
            logger.error(f"Файл аудио не найден: {audio_file_path}")
            return None

        file_size = os.path.getsize(audio_file_path)
        if file_size == 0:
            logger.error(f"Файл аудио пустой: {audio_file_path}")
            return None

        logger.info(f"Отправка аудиофайла размером {file_size} байт на транскрибацию")

        with open(audio_file_path, "rb") as f:
            audio_data = f.read()

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(parts=[
                    types.Part.from_bytes(data=audio_data, mime_type="audio/ogg"),
                    types.Part.from_text("Транскрибируй это аудио на русском языке. Выведи только текст, без комментариев."),
                ])
            ],
        )

        transcribed_text = response.text.strip()
        logger.info(f"Транскрибация успешна, получен текст длиной {len(transcribed_text)} символов")
        return transcribed_text
    except Exception as e:
        logger.error(f"Ошибка при транскрибации аудио: {e}")
        return None


async def analyze_image_content(image_path: str, user_id: int = None) -> Optional[str]:
    """
    Анализирует содержимое изображения с помощью Gemini.

    Args:
        image_path: Путь к файлу изображения
        user_id: ID пользователя для получения настроек

    Returns:
        Описание изображения или None в случае ошибки
    """
    try:
        if not os.path.exists(image_path):
            logger.error(f"Файл изображения не найден: {image_path}")
            return None

        file_size = os.path.getsize(image_path)
        if file_size == 0:
            logger.error(f"Файл изображения пустой: {image_path}")
            return None

        logger.info(f"Обработка изображения размером {file_size} байт")

        with open(image_path, "rb") as f:
            image_data = f.read()

        mime_type = "image/jpeg"
        if image_path.lower().endswith(".png"):
            mime_type = "image/png"

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction="Ты - эксперт по детальному анализу изображений. Опиши изображение максимально подробно, включая объекты, людей, цвета, композицию, освещение, эмоции и атмосферу. Сосредоточься на визуальных аспектах и деталях, которые можно использовать для генерации похожего изображения.",
                max_output_tokens=MAX_TOKENS,
            ),
            contents=[
                types.Content(parts=[
                    types.Part.from_bytes(data=image_data, mime_type=mime_type),
                    types.Part.from_text("Опиши это изображение максимально подробно:"),
                ])
            ],
        )

        return response.text
    except Exception as e:
        logger.error(f"Ошибка при анализе содержимого изображения: {e}")
        return None


async def generate_image(prompt: str, user_id: int) -> Optional[List[str]]:
    """
    Отправляет запрос на генерацию изображения через fal.ai API.

    Args:
        prompt: Промпт для генерации изображения
        user_id: ID пользователя Telegram

    Returns:
        Список URL сгенерированных изображений или None в случае ошибки
    """
    logger.info(f"=== НАЧАЛО generate_image (fal.ai) ===")
    logger.info(f"Промпт: {prompt[:100]}...")
    logger.info(f"User ID: {user_id}")

    settings = get_user_settings(user_id)
    logger.info(f"Настройки получены: {settings}")

    # Маппинг соотношений сторон
    aspect_map = {
        "1:1": "square",
        "16:9": "landscape_16_9",
        "9:16": "portrait_16_9",
        "4:3": "landscape_4_3",
        "3:4": "portrait_4_3",
    }

    aspect_ratio = settings.get("aspect_ratio", "1:1")
    image_size = aspect_map.get(aspect_ratio, "square")
    num_outputs = settings.get("num_outputs", 1)

    # Формируем LoRA конфигурацию
    loras = []
    if FAL_LORA_URL:
        loras.append({
            "path": FAL_LORA_URL,
            "scale": 1.0,
        })

    arguments = {
        "prompt": prompt,
        "image_size": image_size,
        "num_images": num_outputs,
        "num_inference_steps": 28,
        "guidance_scale": 3.0,
        "output_format": "jpeg",
        "enable_safety_checker": False,
        "loras": loras,
    }

    retries = 0
    while retries < MAX_RETRIES:
        try:
            logger.info(f"Отправка запроса на генерацию. image_size={image_size}, num_images={num_outputs}")

            result = fal_client.subscribe(
                FAL_MODEL_ID,
                arguments=arguments,
                with_logs=True,
                on_queue_update=lambda update: (
                    logger.info(f"fal.ai статус: {update}")
                    if not isinstance(update, fal_client.InProgress)
                    else None
                ),
            )

            images = result.get("images", [])
            if not images:
                logger.error("fal.ai вернул пустой список изображений")
                return None

            urls = [img["url"] for img in images]
            logger.info(f"Генерация завершена успешно. Получено {len(urls)} изображений")
            return urls

        except Exception as e:
            logger.error(f"Ошибка при запросе к fal.ai (попытка {retries + 1}/{MAX_RETRIES}): {e}")
            retries += 1
            if retries < MAX_RETRIES:
                import asyncio
                await asyncio.sleep(2)

    logger.error(f"Не удалось сгенерировать изображение после {MAX_RETRIES} попыток")
    return None


async def generate_image_with_params(prompt: str, params: dict) -> Optional[List[str]]:
    """
    Генерирует изображение с заданными параметрами через fal.ai API.

    Args:
        prompt: Текстовое описание для генерации
        params: Словарь с параметрами генерации

    Returns:
        Список URL-адресов сгенерированных изображений или None
    """
    logger.info(f"Запуск генерации с пользовательскими параметрами: {params}")

    loras = []
    if FAL_LORA_URL:
        loras.append({
            "path": FAL_LORA_URL,
            "scale": 1.0,
        })

    arguments = {
        "prompt": prompt,
        "image_size": "square",
        "num_images": 1,
        "num_inference_steps": params.get("num_inference_steps", 28),
        "guidance_scale": params.get("guidance_scale", 3.0),
        "output_format": params.get("output_format", "jpeg"),
        "enable_safety_checker": False,
        "loras": loras,
    }

    try:
        result = fal_client.subscribe(
            FAL_MODEL_ID,
            arguments=arguments,
            with_logs=True,
            on_queue_update=lambda update: None,
        )

        images = result.get("images", [])
        if not images:
            logger.warning("fal.ai вернул пустой список изображений")
            return None

        urls = [img["url"] for img in images]
        logger.info(f"Изображение сгенерировано. Получено {len(urls)} изображений")
        return urls

    except Exception as e:
        logger.error(f"Ошибка при генерации изображения: {e}")
        return None


async def download_file(file_url: str, local_filename: Optional[str] = None) -> Optional[str]:
    """
    Скачивает файл по URL.

    Args:
        file_url: URL файла
        local_filename: Локальное имя файла

    Returns:
        Путь к скачанному файлу или None в случае ошибки
    """
    if not local_filename:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        local_filename = tmp.name
        tmp.close()

    try:
        with requests.get(file_url, stream=True, timeout=TIMEOUT) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename
    except Exception as e:
        logger.error(f"Ошибка при скачивании файла: {e}")
        if os.path.exists(local_filename):
            os.remove(local_filename)
        return None
