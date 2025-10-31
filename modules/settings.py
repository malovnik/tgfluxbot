"""
Модуль для работы с пользовательскими настройками.
"""

import os
import pickle
from typing import Dict, Any

from modules.config import (
    DEFAULT_NUM_OUTPUTS, DEFAULT_ASPECT_RATIO, DEFAULT_PROMPT_STRENGTH,
    USER_SETTINGS_FILE, logger, DEFAULT_OPENAI_MODEL, DEFAULT_GENERATION_CYCLES,
    DEFAULT_AUTO_CONFIRM_PROMPT
)

def load_user_settings() -> Dict[int, Dict[str, Any]]:
    """
    Загружает настройки пользователей из файла.
    
    Returns:
        Dict[int, Dict[str, Any]]: Словарь с настройками пользователей
    """
    if os.path.exists(USER_SETTINGS_FILE):
        try:
            with open(USER_SETTINGS_FILE, 'rb') as f:
                settings = pickle.load(f)
            return settings
        except Exception as e:
            logger.error(f"Ошибка при загрузке настроек: {e}")
    
    return {}

def save_user_settings(settings: Dict[int, Dict[str, Any]]) -> None:
    """
    Сохраняет настройки пользователей в файл.
    
    Args:
        settings (Dict[int, Dict[str, Any]]): Словарь с настройками пользователей
    """
    try:
        with open(USER_SETTINGS_FILE, 'wb') as f:
            pickle.dump(settings, f)
    except Exception as e:
        logger.error(f"Ошибка при сохранении настроек: {e}")

def get_user_settings(user_id: int) -> Dict[str, Any]:
    """
    Получает настройки пользователя.
    
    Args:
        user_id (int): ID пользователя Telegram
        
    Returns:
        Dict[str, Any]: Словарь с настройками пользователя
    """
    settings = load_user_settings()
    if user_id not in settings:
        settings[user_id] = {
            "num_outputs": DEFAULT_NUM_OUTPUTS,
            "aspect_ratio": DEFAULT_ASPECT_RATIO,
            "prompt_strength": DEFAULT_PROMPT_STRENGTH,
            "openai_model": DEFAULT_OPENAI_MODEL,
            "generation_cycles": DEFAULT_GENERATION_CYCLES,
            "auto_confirm_prompt": DEFAULT_AUTO_CONFIRM_PROMPT
        }
        save_user_settings(settings)
    
    # Проверяем наличие новых параметров в настройках
    if "openai_model" not in settings[user_id]:
        settings[user_id]["openai_model"] = DEFAULT_OPENAI_MODEL
        save_user_settings(settings)
        
    if "generation_cycles" not in settings[user_id]:
        settings[user_id]["generation_cycles"] = DEFAULT_GENERATION_CYCLES
        save_user_settings(settings)
    
    if "auto_confirm_prompt" not in settings[user_id]:
        settings[user_id]["auto_confirm_prompt"] = DEFAULT_AUTO_CONFIRM_PROMPT
        save_user_settings(settings)
    
    return settings[user_id]

def update_user_settings(user_id: int, key: str, value: Any) -> None:
    """
    Обновляет настройки пользователя.
    
    Args:
        user_id (int): ID пользователя Telegram
        key (str): Ключ настройки
        value (Any): Значение настройки
    """
    settings = load_user_settings()
    if user_id not in settings:
        settings[user_id] = {
            "num_outputs": DEFAULT_NUM_OUTPUTS,
            "aspect_ratio": DEFAULT_ASPECT_RATIO,
            "prompt_strength": DEFAULT_PROMPT_STRENGTH,
            "openai_model": DEFAULT_OPENAI_MODEL,
            "generation_cycles": DEFAULT_GENERATION_CYCLES,
            "auto_confirm_prompt": DEFAULT_AUTO_CONFIRM_PROMPT
        }
    
    settings[user_id][key] = value
    save_user_settings(settings)
    logger.info(f"Обновлены настройки пользователя {user_id}: {key}={value}")

def reset_user_settings(user_id: int) -> None:
    """
    Сбрасывает настройки пользователя до значений по умолчанию.
    
    Args:
        user_id (int): ID пользователя Telegram
    """
    settings = load_user_settings()
    settings[user_id] = {
        "num_outputs": DEFAULT_NUM_OUTPUTS,
        "aspect_ratio": DEFAULT_ASPECT_RATIO,
        "prompt_strength": DEFAULT_PROMPT_STRENGTH,
        "openai_model": DEFAULT_OPENAI_MODEL,
        "generation_cycles": DEFAULT_GENERATION_CYCLES,
        "auto_confirm_prompt": DEFAULT_AUTO_CONFIRM_PROMPT
    }
    save_user_settings(settings)
    logger.info(f"Сброшены настройки пользователя {user_id}") 