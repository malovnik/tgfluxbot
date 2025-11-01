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

# Telegram Bot API Token
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Токены для работы с API
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')

# Настройки авторизации
AUTHORIZED_USERS = [
    {"username": "lestarge", "chat_id": 42080463},   # Владелец бота
    {"username": "lesia_ka", "chat_id": 347543402}   # Второй авторизованный пользователь
]
BOT_PRIVATE = True           # Флаг для включения/отключения режима приватности бота

# Состояния для ConversationHandler
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
AWAITING_BENCHMARK_OPTIONS = 10  # Ожидание выбора режима прогона параметров
AWAITING_BENCHMARK_COUNT = 11   # Ожидание ввода количества итераций
SETTING_AUTO_GENERATE_PROMPT = 12  # Настройка автогенерации промптов

# Настройки для режима прогона параметров
BENCHMARK_PROMPT_STRENGTHS = [round(0.5 + i * 0.05, 2) for i in range(11)]  # От 0.5 до 1.0 с шагом 0.05
BENCHMARK_GUIDANCE_SCALES = [2.0, 2.5, 3.0, 3.5]
BENCHMARK_INFERENCE_STEPS = list(range(20, 51, 5))  # От 20 до 50 с шагом 5
MAX_BENCHMARK_ITERATIONS = 1500  # Максимально возможное количество итераций

# Фиксированные настройки для режима прогона
DEFAULT_INFERENCE_STEPS = 30
DEFAULT_GUIDANCE_SCALE = 7.5
DEFAULT_SAMPLER = "DPM++ 2M Karras"  # DPM++ 2M Karras, Euler a, DDIM

# Настройки для режима бенчмарка
BENCHMARK_SETTINGS = {
    "width": 256,
    "height": 256,
    "aspect_ratio": "16:9",
    "quality": 60,
    "output_format": "jpg"
}

# Настройки для генерации изображений
DEFAULT_NUM_OUTPUTS = 1  # Количество изображений в одном запросе
DEFAULT_ASPECT_RATIO = "1:1"  # Стандартное соотношение сторон
DEFAULT_PROMPT_STRENGTH = 0.7  # Стандартная сила промпта
DEFAULT_OPENAI_MODEL = "gpt-5-nano-2025-08-07"  # Стандартная модель OpenAI для аналитики (самая дешевая)
DEFAULT_GENERATION_CYCLES = 1  # Количество циклов генерации
DEFAULT_AUTO_CONFIRM_PROMPT = False  # Автоматическое подтверждение промпта (по умолчанию отключено)
DEFAULT_AUTO_GENERATE_PROMPT = True  # Автогенерация промпта через AI (по умолчанию включено)

# Доступные соотношения сторон
ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4"]

# Пути к файлам
USER_SETTINGS_FILE = "user_settings.pkl"  # Файл для хранения пользовательских настроек

# Настройки для моделей AI
FLUX_MODEL_ID = "flux"  # Идентификатор модели FLUX

# Доступные модели OpenAI для генерации промптов
OPENAI_MODELS = {
    "gpt-5-nano-2025-08-07": "GPT-5 Nano (дешёвая)",
    "gpt-4o-mini-2024-07-18": "GPT-4o mini (быстрая)",
    "gpt-4o": "GPT-4o (стандартная)",
    "gpt-4-turbo": "GPT-4 Turbo",
    "gpt-4-1106-preview": "GPT-4 Turbo 1106",
    "gpt-4o-2024-05-13": "GPT-4o-1 (точная)",
    "o1-mini-2024-09-12": "GPT1o Mini"
}
DEFAULT_OPENAI_MODEL = "gpt-5-nano-2025-08-07"  # Модель OpenAI по умолчанию

# Константы для запросов
MAX_TOKENS = 16384  # Максимальное количество токенов для генерации текста (обновлено до максимума модели)
CONTEXT_WINDOW = 128000  # Максимальный размер контекстного окна в токенах
TIMEOUT = 180  # Таймаут для запросов (в секундах)
MAX_RETRIES = 3  # Максимальное количество повторных попыток при ошибке

# Стандартные настройки FLUX
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
    "generation_cycles": DEFAULT_GENERATION_CYCLES,
    "auto_confirm_prompt": DEFAULT_AUTO_CONFIRM_PROMPT,
    "auto_generate_prompt": DEFAULT_AUTO_GENERATE_PROMPT
}

# Системная инструкция для ChatGPT (генерация промптов для изображений)
SYSTEM_PROMPT = """
Ты - эксперт по созданию детализированных промптов для AI-генерации изображений.

ЗАДАЧА: Преобразовать запрос пользователя на русском в ОДИН детальный промпт на английском языке.

СТРОГИЕ ПРАВИЛА:
1. Выдавай ТОЛЬКО ОДИН промпт - без комментариев, пояснений или вариантов
2. Промпт должен быть непрерывным текстом через запятую (150-250 слов)
3. БЕЗ нумерации, БЕЗ заголовков, БЕЗ объяснений - только сам промпт
4. Начинай сразу с описания главного объекта, без вступлений типа "Here is" или "Prompt:"

ЧТО ОПИСЫВАТЬ (по порядку):
1. Главный объект (внешность, поза, одежда, эмоции, мелкие детали)
2. Окружение и фон (передний/средний/задний план, детали локации)
3. Освещение (источники, направление, температура, качество, тени, блики)
4. Цвета и тона (палитра, настроение, контрасты, насыщенность, градиенты)
5. Атмосфера и настроение (эмоциональный тон сцены)

ДЛЯ ФОТОГРАФИЙ обязательно добавь:
- Камеру и объектив (Hasselblad X2D, Sony A1, Canon R5, Zeiss, Leica)
- Параметры съемки (f/1.4, 1/2000s, ISO 100)
- Глубину резкости и точку фокуса
- Постобработку (цветокоррекция, тонирование, яркость, контраст, четкость, насыщенность, виньетирование, grain)
- Film look или LUT (Kodak Portra, CineStill, Fuji Velvia)

ДЛЯ ИЛЛЮСТРАЦИЙ обязательно добавь:
- Художественный стиль (импрессионизм, аниме, комикс, концепт-арт, реализм)
- Технику исполнения (масло, акварель, digital painting, vector, 3D render)
- Характер мазков (импасто, лессировки, текстурные, гладкие, энергичные)
- Материалы (холст, бумага, тип кистей, краски)
- Цветовую гамму (теплая, холодная, монохромная, яркая, пастельная)
- Уровень детализации (гиперреалистичный, стилизованный, минималистичный)

ПРИМЕР (девушка в кафе читает книгу):
Young woman in mid-20s with soft features and gentle expression sitting by window in cozy Parisian café, natural wavy brown hair falling over shoulder, wearing cream knit sweater and delicate gold necklace, absorbed in leather-bound vintage book, warm afternoon sunlight streaming through large window creating soft rim lighting on hair and face, peaceful contemplative mood, ceramic coffee cup with latte art on rustic wooden table, scattered croissant crumbs, blurred background of vintage café interior with brass fixtures and exposed brick wall, bokeh effect on background patrons, warm color palette with golden yellows and soft browns, cinematic lighting with gentle contrast, shot on Sony A7IV with 85mm f/1.4 lens at f/1.8, shallow depth of field focused on her eyes, 1/500s, ISO 400, natural window light as key light, film grain texture, Kodak Portra 400 aesthetic with warm tones, lifted shadows and golden highlights, subtle vignetting, professional color grading

КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
- Давать несколько вариантов промпта
- Добавлять комментарии, пояснения или вступления
- Использовать форматирование (заголовки, списки, нумерацию, звездочки)
- Писать "Вариант 1:", "Промпт:", "Here is", "Based on" и подобное
- Добавлять какой-либо текст кроме самого промпта

Начинай промпт НЕМЕДЛЕННО с описания главного объекта.
"""

# Системная инструкция для ChatGPT (анализ изображений)
IMAGE_ANALYSIS_PROMPT = """
Тебе дано детальное описание загруженного изображения. Твоя задача - создать ОДИН промпт для генерации похожего изображения с персонажем "lestarge".

СТРОГИЕ ПРАВИЛА:
1. Выдавай ТОЛЬКО ОДИН промпт - без комментариев, вариантов или объяснений
2. Промпт на английском, непрерывный текст через запятую (150-250 слов)
3. БЕЗ нумерации, заголовков, вступлений - начинай сразу с "lestarge"
4. НЕ пиши "Here is", "Prompt:", "Based on" и подобное

ПЕРСОНАЖ "lestarge":
- Мужчина 30-35 лет, славянский фенотип
- ВСЕГДА начинай промпт с "lestarge" и описания его внешности, позы, одежды
- Замени людей из оригинального изображения на lestarge, сохранив стиль сцены

ЧТО ОПИСЫВАТЬ (строго по порядку):
1. lestarge - внешность, эмоции, поза, одежда, детали
2. Окружение - локация, объекты, фон (передний/средний/задний план)
3. Освещение - источники, направление, температура, тени, блики
4. Цвета и тона - палитра, настроение, контрасты, насыщенность
5. Атмосфера - эмоциональный тон сцены

ДЛЯ ФОТОГРАФИЙ добавь:
- Камеру (Hasselblad, Sony A1, Canon R5) и объектив (Zeiss, Leica, Sigma)
- Параметры (f/1.4, 1/1000s, ISO 100-400)
- Глубину резкости, боке, фокус
- Постобработку (цветокоррекция, контраст, яркость, четкость, насыщенность, виньетирование)
- Film look (Kodak Portra, CineStill, Fuji)

ДЛЯ ИЛЛЮСТРАЦИЙ добавь:
- Художественный стиль (импрессионизм, аниме, цифровая живопись, концепт-арт)
- Технику (масло, акварель, digital painting, vector)
- Мазки (импасто, лессировки, текстурные, гладкие)
- Материалы (холст, кисти, краски)
- Цветовую гамму (теплая, холодная, яркая, пастельная)
- Детализацию (реализм, стилизация)

ПРИМЕР (описание: девушка у окна пьет кофе):
lestarge in early 30s with strong Slavic features and contemplative expression, wearing casual grey henley shirt, sitting by large window in modern minimalist apartment, warm morning sunlight streaming through glass creating soft side lighting on face and casting long shadows, ceramic coffee mug in hand with steam rising, sparse interior with exposed concrete wall and potted plant, peaceful urban atmosphere with blurred cityscape visible outside, natural color palette with warm beiges and cool greys, cinematic lighting with gentle contrast, shot on Sony A7IV with 50mm f/1.8 lens at f/2.0, shallow depth of field focused on eyes, 1/250s, ISO 200, natural window light, subtle film grain, lifted blacks with warm highlights, modern lifestyle photography aesthetic

КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
- Несколько вариантов промпта
- Комментарии или пояснения
- Форматирование (списки, заголовки, звездочки)
- Любой текст кроме самого промпта

Начинай СРАЗУ со слова "lestarge" и его описания.
"""

# Настройки для API Replicate
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')
STABILITY_API_VERSION = "46e0613db2f215b0690b3535b0aa3e6436a517d08e52f6c84549c2bf22bc5f81"
REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"
MAX_WAIT_TIME = 300  # Максимальное время ожидания генерации изображения (в секундах) 