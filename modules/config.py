"""
Модуль с константами и настройками для Telegram бота.
"""

import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =================================================================
# API Tokens and Keys
# =================================================================

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')

# =================================================================
# Authorization Settings
# =================================================================

AUTHORIZED_USERS = [
    {"username": "lestarge", "chat_id": 42080463},
    {"username": "lesia_ka", "chat_id": 347543402}
]
BOT_PRIVATE = True  # Режим приватности бота

# =================================================================
# Conversation States
# =================================================================

SETTINGS = 0
AWAITING_PROMPT = 1
SETTING_ASPECT_RATIO = 2
SETTING_NUM_OUTPUTS = 3
SETTING_PROMPT_STRENGTH = 4
SETTING_OPENAI_MODEL = 5
SETTING_GENERATION_CYCLES = 6
SETTING_AUTO_CONFIRM_PROMPT = 7
AWAITING_BENCHMARK_PROMPT = 8
AWAITING_CONFIRMATION = 9
AWAITING_BENCHMARK_OPTIONS = 10
AWAITING_BENCHMARK_COUNT = 11

# =================================================================
# Benchmark Settings
# =================================================================

BENCHMARK_PROMPT_STRENGTHS = [round(0.5 + i * 0.05, 2) for i in range(11)]
BENCHMARK_GUIDANCE_SCALES = [2.0, 2.5, 3.0, 3.5]
BENCHMARK_INFERENCE_STEPS = list(range(20, 51, 5))
MAX_BENCHMARK_ITERATIONS = 1500

DEFAULT_INFERENCE_STEPS = 30
DEFAULT_GUIDANCE_SCALE = 7.5
DEFAULT_SAMPLER = "DPM++ 2M Karras"

BENCHMARK_SETTINGS = {
    "width": 256,
    "height": 256,
    "aspect_ratio": "16:9",
    "quality": 60,
    "output_format": "jpg"
}

# =================================================================
# Image Generation Settings
# =================================================================

DEFAULT_NUM_OUTPUTS = 1
DEFAULT_ASPECT_RATIO = "1:1"
DEFAULT_PROMPT_STRENGTH = 0.7
DEFAULT_OPENAI_MODEL = "gpt-5-nano-2025-08-07"
DEFAULT_GENERATION_CYCLES = 1
DEFAULT_AUTO_CONFIRM_PROMPT = False

ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4"]

# =================================================================
# OpenAI Models
# =================================================================

OPENAI_MODELS = {
    "gpt-5-nano-2025-08-07": "GPT-5 Nano (экономичная)",
    "gpt-4o-mini-2024-07-18": "GPT-4o Mini (быстрая и качественная)",
}

# =================================================================
# API Configuration
# =================================================================

MAX_TOKENS = 16384
CONTEXT_WINDOW = 128000
TIMEOUT = 180
MAX_RETRIES = 3

# Replicate API
STABILITY_API_VERSION = "b33842d0896aad6018790f120e7c455abb0bcad55c75b5b3bfebf2f7deeb8d3f"
REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"
MAX_WAIT_TIME = 300

# =================================================================
# Default FLUX Settings
# =================================================================

DEFAULT_SETTINGS = {
    "model": "dev",
    "width": 1440,
    "height": 1440,
    "go_fast": False,
    "lora_scale": 1,
    "megapixels": "1",
    "num_outputs": 1,
    "aspect_ratio": "1:1",
    "output_format": "jpg",
    "guidance_scale": 3,
    "output_quality": 100,
    "prompt_strength": 0.9,
    "extra_lora_scale": 1,
    "num_inference_steps": 36,
    "openai_model": DEFAULT_OPENAI_MODEL,
    "generation_cycles": DEFAULT_GENERATION_CYCLES
}

# =================================================================
# File Paths
# =================================================================

USER_SETTINGS_FILE = "user_settings.pkl"

# =================================================================
# System Prompts (imported from prompts module)
# =================================================================

from modules.prompts import SYSTEM_PROMPT, IMAGE_ANALYSIS_PROMPT
