"""
Модуль для взаимодействия с AI-сервисами (OpenAI, Replicate).
"""

import os
import time
import tempfile
import base64
from typing import Optional, List, Dict, Any, Union
import requests
from openai import OpenAI
import aiohttp
import asyncio

from modules.config import (
    OPENAI_API_KEY, REPLICATE_API_TOKEN, SYSTEM_PROMPT, 
    IMAGE_ANALYSIS_PROMPT, DEFAULT_OPENAI_MODEL, MAX_TOKENS,
    TIMEOUT, MAX_RETRIES, logger, STABILITY_API_VERSION, REPLICATE_API_URL, MAX_WAIT_TIME
)
from modules.settings import get_user_settings

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

async def generate_prompt(text: str, user_id: int = None) -> Optional[str]:
    """
    Генерирует промпт для создания изображения с помощью ChatGPT.

    Args:
        text (str): Запрос пользователя на русском языке
        user_id (int, optional): ID пользователя для получения настроек

    Returns:
        Optional[str]: Промпт на английском языке с префиксом-ключевым словом или None в случае ошибки
    """
    try:
        # Получаем настройки пользователя, если предоставлен ID
        model = DEFAULT_OPENAI_MODEL
        keyword = "lestarge"  # Значение по умолчанию
        if user_id:
            settings = get_user_settings(user_id)
            model = settings.get("openai_model", DEFAULT_OPENAI_MODEL)
            keyword = settings.get("keyword", "lestarge")

        logger.info(f"Генерация промпта с использованием модели {model} и ключевого слова '{keyword}'")

        # Формируем параметры запроса
        request_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            "max_completion_tokens": MAX_TOKENS,
            "timeout": TIMEOUT
        }

        # gpt-5-nano не поддерживает кастомный temperature (только default=1.0)
        if model != "gpt-5-nano-2025-08-07":
            request_params["temperature"] = 0.7

        response = client.chat.completions.create(**request_params)
        prompt = response.choices[0].message.content.strip()

        # Добавляем префикс-ключевое слово к промпту, если оно задано и еще не добавлено
        if keyword and not prompt.lower().startswith(keyword.lower()):
            prompt = f"{keyword} {prompt}"

        return prompt
    except Exception as e:
        logger.error(f"Ошибка при генерации промпта: {e}")
        return None

async def analyze_image(image_description: str, user_id: int = None) -> Optional[str]:
    """
    Генерирует промпт на основе описания изображения.

    Args:
        image_description (str): Описание изображения
        user_id (int, optional): ID пользователя для получения настроек

    Returns:
        Optional[str]: Промпт для создания похожего изображения с ключевым словом или None в случае ошибки
    """
    try:
        # Получаем настройки пользователя, если предоставлен ID
        model = DEFAULT_OPENAI_MODEL
        keyword = "lestarge"  # Значение по умолчанию
        if user_id:
            settings = get_user_settings(user_id)
            model = settings.get("openai_model", DEFAULT_OPENAI_MODEL)
            keyword = settings.get("keyword", "lestarge")

        logger.info(f"Анализ изображения с использованием модели {model} и ключевого слова '{keyword}'")

        # Формируем параметры запроса
        request_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": IMAGE_ANALYSIS_PROMPT},
                {"role": "user", "content": image_description}
            ],
            "max_completion_tokens": MAX_TOKENS,
            "timeout": TIMEOUT
        }

        # gpt-5-nano не поддерживает кастомный temperature (только default=1.0)
        if model != "gpt-5-nano-2025-08-07":
            request_params["temperature"] = 0.7

        response = client.chat.completions.create(**request_params)
        prompt = response.choices[0].message.content.strip()

        # Добавляем префикс-ключевое слово к промпту, если оно задано и еще не добавлено
        if keyword and not prompt.lower().startswith(keyword.lower()):
            prompt = f"{keyword} {prompt}"

        return prompt
    except Exception as e:
        logger.error(f"Ошибка при анализе изображения: {e}")
        return None

async def transcribe_audio(audio_file_path: str) -> Optional[str]:
    """
    Транскрибирует аудиофайл с помощью Whisper API.
    
    Args:
        audio_file_path (str): Путь к аудиофайлу
        
    Returns:
        Optional[str]: Транскрибированный текст или None в случае ошибки
    """
    try:
        # Проверяем, существует ли файл
        if not os.path.exists(audio_file_path):
            logger.error(f"Файл аудио не найден: {audio_file_path}")
            return None
            
        with open(audio_file_path, "rb") as audio_file:
            # Дополнительная проверка размера файла
            file_size = os.path.getsize(audio_file_path)
            if file_size == 0:
                logger.error(f"Файл аудио пустой: {audio_file_path}")
                return None
                
            logger.info(f"Отправка аудиофайла размером {file_size} байт на транскрибацию")
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru",
                timeout=TIMEOUT
            )
        
        transcribed_text = transcript.text
        logger.info(f"Транскрибация успешна, получен текст длиной {len(transcribed_text)} символов")
        return transcribed_text
    except Exception as e:
        logger.error(f"Ошибка при транскрибации аудио: {e}")
        return None

async def analyze_image_content(image_path: str, user_id: int = None) -> Optional[str]:
    """
    Анализирует содержимое изображения с помощью GPT-4 Vision.
    
    Args:
        image_path (str): Путь к файлу изображения
        user_id (int, optional): ID пользователя для получения настроек
        
    Returns:
        Optional[str]: Описание изображения или None в случае ошибки
    """
    try:
        # Проверяем, существует ли файл
        if not os.path.exists(image_path):
            logger.error(f"Файл изображения не найден: {image_path}")
            return None
            
        # Проверяем размер файла
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            logger.error(f"Файл изображения пустой: {image_path}")
            return None
            
        logger.info(f"Обработка изображения размером {file_size} байт")
        
        # Получаем настройки пользователя, если предоставлен ID
        model = "gpt-4o"  # Для анализа изображений лучше использовать GPT-4o
        if user_id:
            settings = get_user_settings(user_id)
            # Для анализа изображений игнорируем модели, не поддерживающие зрение
            if "gpt-4" in settings.get("openai_model", DEFAULT_OPENAI_MODEL):
                model = settings.get("openai_model", DEFAULT_OPENAI_MODEL)
            
        logger.info(f"Анализ содержимого изображения с использованием модели {model}")
        
        # Открываем изображение и кодируем его в base64
        with open(image_path, "rb") as image_file:
            # Читаем данные изображения
            image_data = image_file.read()
            # Кодируем в base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Формируем URL с данными изображения
            image_url = f"data:image/jpeg;base64,{base64_image}"
            logger.info(f"Изображение успешно закодировано в base64, длина строки: {len(base64_image)}")
            
            # Отправляем запрос на анализ изображения
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты - эксперт по детальному анализу изображений. Опиши изображение максимально подробно, включая объекты, людей, цвета, композицию, освещение, эмоции и атмосферу. Сосредоточься на визуальных аспектах и деталях, которые можно использовать для генерации похожего изображения."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Опиши это изображение максимально подробно:"},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_completion_tokens=MAX_TOKENS,
                timeout=TIMEOUT
            )
            
            # Получаем описание изображения
            image_description = response.choices[0].message.content
            
            return image_description
    except Exception as e:
        logger.error(f"Ошибка при анализе содержимого изображения: {e}")
        return None

async def generate_image(prompt: str, user_id: int) -> Optional[List[str]]:
    """
    Отправляет запрос на генерацию изображения через Replicate API.

    Args:
        prompt (str): Промпт для генерации изображения
        user_id (int): ID пользователя Telegram

    Returns:
        Optional[List[str]]: Список URL сгенерированных изображений или None в случае ошибки
    """
    logger.info(f"=== НАЧАЛО generate_image ===")
    logger.info(f"Промпт: {prompt[:100]}...")
    logger.info(f"User ID: {user_id}")

    # Заголовки для запроса
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait"
    }

    # Получаем настройки пользователя
    settings = get_user_settings(user_id)
    logger.info(f"Настройки получены: {settings}")
    
    # Формируем данные для запроса
    data = {
        "version": "b33842d0896aad6018790f120e7c455abb0bcad55c75b5b3bfebf2f7deeb8d3f",
        "input": {
            "prompt": prompt,
            "num_outputs": settings.get("num_outputs", 1),
            "aspect_ratio": settings.get("aspect_ratio", "1:1"),
            "prompt_strength": settings.get("prompt_strength", 0.9),
            "model": "dev",
            "width": 1440,
            "height": 1440,
            "go_fast": False,
            "lora_scale": 1,
            "megapixels": "1",
            "output_format": "jpg",
            "guidance_scale": 3,
            "output_quality": 100,
            "extra_lora_scale": 1,
            "num_inference_steps": 36
        }
    }
    
    # Счетчик попыток
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            logger.info(f"Отправка запроса на генерацию изображения. Промпт: {prompt[:100]}...")
            logger.info(f"Параметры: num_outputs={data['input']['num_outputs']}, aspect_ratio={data['input']['aspect_ratio']}, prompt_strength={data['input']['prompt_strength']}")

            # Отправляем запрос на создание предсказания
            response = requests.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json=data,
                timeout=TIMEOUT
            )
            logger.info(f"Статус ответа от Replicate: {response.status_code}")

            if response.status_code != 201 and response.status_code != 200:
                error_text = response.text
                logger.error(f"Ошибка от Replicate API: {error_text}")
                response.raise_for_status()

            prediction = response.json()
            logger.info(f"Получен ответ от Replicate: {prediction}")
            
            # Получаем ID предсказания
            prediction_id = prediction.get("id")
            if not prediction_id:
                logger.error("Не удалось получить ID предсказания")
                return None

            # Проверяем статус генерации каждые 5 секунд с таймаутом
            start_time = time.time()
            while True:
                # Проверяем, не превышен ли лимит времени ожидания
                elapsed_time = time.time() - start_time
                if elapsed_time > MAX_WAIT_TIME:
                    logger.error(f"Превышено максимальное время ожидания генерации ({MAX_WAIT_TIME}s). Elapsed: {elapsed_time:.1f}s")
                    return None

                response = requests.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers=headers,
                    timeout=TIMEOUT
                )
                response.raise_for_status()
                prediction = response.json()

                logger.info(f"Статус генерации: {prediction.get('status')} (прошло {elapsed_time:.1f}s)")

                # Если генерация завершена, возвращаем URL'ы изображений
                if prediction.get("status") == "succeeded":
                    output = prediction.get("output")
                    logger.info(f"Генерация завершена успешно. Тип output: {type(output)}, значение: {output}")

                    # Нормализуем output в список
                    if output is None:
                        logger.error("Output пустой (None)")
                        return None
                    elif isinstance(output, str):
                        # Если output - одна строка (URL), оборачиваем в список
                        logger.info(f"Output - одна URL-ссылка, преобразуем в список")
                        return [output]
                    elif isinstance(output, list):
                        # Если output уже список, возвращаем как есть
                        logger.info(f"Output - список из {len(output)} элементов")
                        return output
                    else:
                        logger.error(f"Неожиданный тип output: {type(output)}")
                        return None

                elif prediction.get("status") == "failed":
                    logger.error(f"Ошибка при генерации: {prediction.get('error')}")
                    return None

                # Ждем перед следующей проверкой
                time.sleep(5)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к Replicate API (попытка {retries+1}/{MAX_RETRIES}): {e}")
            retries += 1
            time.sleep(2)  # Ждем перед повторной попыткой
            
    logger.error(f"Не удалось сгенерировать изображение после {MAX_RETRIES} попыток")
    return None

async def generate_image_with_params(prompt: str, params: dict) -> List[str]:
    """
    Генерирует изображение с заданными пользователем параметрами через API Replicate.
    
    Args:
        prompt: Текстовое описание для генерации изображения
        params: Словарь с параметрами генерации (prompt_strength, guidance_scale, num_inference_steps и др.)
        
    Returns:
        List[str]: Список URL-адресов сгенерированных изображений или None в случае ошибки
    """
    logger.info(f"Запуск генерации изображения с пользовательскими параметрами: {params}")
    
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Подготовка данных для запроса
    data = {
        "version": STABILITY_API_VERSION,
        "input": {
            "prompt": prompt,
            "prompt_strength": params.get("prompt_strength", 0.8),
            "num_outputs": 1,  # Всегда генерируем по 1 изображению за раз для прогона
            "guidance_scale": params.get("guidance_scale", 7.5),
            "num_inference_steps": params.get("num_inference_steps", 30),
            "width": params.get("width", 512),
            "height": params.get("height", 512),
            "scheduler": "K_EULER",
            "output_format": params.get("output_format", "png"),
            "apply_watermark": False,
            "high_noise_frac": 0.8,
            "negative_prompt": "low quality, bad quality, sketches, watermark, grainy, extra limbs"
        }
    }
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            # Отправляем запрос на генерацию изображения
            async with aiohttp.ClientSession() as session:
                async with session.post(REPLICATE_API_URL, headers=headers, json=data) as response:
                    if response.status != 201 and response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ошибка при отправке запроса на генерацию изображения: {response.status} - {error_text}")
                        return None
                    
                    response_data = await response.json()
                    prediction_id = response_data.get("id")
                    if not prediction_id:
                        logger.error("Не получен ID предсказания в ответе от API")
                        return None
                        
                    # URL для проверки статуса генерации
                    get_url = f"{REPLICATE_API_URL}/{prediction_id}"
                    
                    # Ожидаем завершения генерации
                    start_time = time.time()
                    while True:
                        # Проверяем, не превышено ли максимальное время ожидания
                        if time.time() - start_time > MAX_WAIT_TIME:
                            logger.error(f"Превышено максимальное время ожидания ({MAX_WAIT_TIME} сек) для генерации изображения")
                            return None
                            
                        # Проверяем статус генерации
                        async with session.get(get_url, headers=headers) as status_response:
                            if status_response.status != 200:
                                logger.error(f"Ошибка при проверке статуса генерации: {status_response.status}")
                                break
                                
                            status_data = await status_response.json()
                            status = status_data.get("status")
                            
                            if status == "succeeded":
                                # Генерация успешно завершена
                                output = status_data.get("output")
                                logger.info(f"Генерация завершена успешно. Тип output: {type(output)}, значение: {output}")

                                # Нормализуем output в список
                                if output is None:
                                    logger.warning("Генерация завершена успешно, но output пустой (None)")
                                    return None
                                elif isinstance(output, str):
                                    # Если output - одна строка (URL), оборачиваем в список
                                    logger.info(f"Output - одна URL-ссылка, преобразуем в список")
                                    return [output]
                                elif isinstance(output, list):
                                    # Если output уже список, проверяем что он не пустой
                                    if not output:
                                        logger.warning("Генерация завершена успешно, но список output пустой")
                                        return None
                                    logger.info(f"Изображение успешно сгенерировано с параметрами: {params}. Получено {len(output)} изображений")
                                    return output
                                else:
                                    logger.error(f"Неожиданный тип output: {type(output)}")
                                    return None
                                
                            elif status == "failed":
                                # Произошла ошибка при генерации
                                error_message = status_data.get("error", "Неизвестная ошибка")
                                logger.error(f"Ошибка при генерации изображения: {error_message}")
                                return None
                                
                            elif status in ["starting", "processing"]:
                                # Генерация все еще выполняется, ждем 5 секунд и проверяем снова
                                await asyncio.sleep(5)
                                continue
                                
                            else:
                                # Неизвестный статус
                                logger.warning(f"Получен неизвестный статус генерации: {status}")
                                await asyncio.sleep(5)
                                continue
            
        except Exception as e:
            logger.error(f"Произошла ошибка при генерации изображения: {str(e)}")
            retry_count += 1
            if retry_count < MAX_RETRIES:
                logger.info(f"Повторная попытка {retry_count+1}/{MAX_RETRIES}...")
                await asyncio.sleep(2)
            else:
                logger.error(f"Исчерпаны все попытки генерации изображения. Последняя ошибка: {str(e)}")
                return None
                
    return None

async def download_file(file_url: str, local_filename: Optional[str] = None) -> Optional[str]:
    """
    Скачивает файл по URL.
    
    Args:
        file_url (str): URL файла
        local_filename (Optional[str]): Локальное имя файла
        
    Returns:
        Optional[str]: Путь к скачанному файлу или None в случае ошибки
    """
    if not local_filename:
        # Создаем временный файл, если имя не указано
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