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
OWNER_USERNAME = "ВАШ ЛОГИН В ТГ"  # Имя пользователя владельца бота
OWNER_CHAT_ID = ВАШ ЧАТ ID В ТГ  # Chat ID владельца бота
BOT_PRIVATE = True           # Флаг для включения/отключения режима приватности бота

# Состояния для ConversationHandler
SETTINGS = 0
AWAITING_PROMPT = 1
SETTING_ASPECT_RATIO = 2
SETTING_NUM_OUTPUTS = 3
SETTING_PROMPT_STRENGTH = 4
SETTING_OPENAI_MODEL = 5
SETTING_GENERATION_CYCLES = 6
AWAITING_BENCHMARK_PROMPT = 7
AWAITING_CONFIRMATION = 8

# Настройки для режима прогона параметров
BENCHMARK_PROMPT_STRENGTHS = [round(0.5 + i * 0.05, 2) for i in range(11)]  # От 0.5 до 1.0 с шагом 0.05
BENCHMARK_GUIDANCE_SCALES = [2.0, 2.5, 3.0, 3.5]
BENCHMARK_INFERENCE_STEPS = list(range(20, 51, 10))  # От 20 до 50 с шагом 10 (для ускорения)
MAX_BENCHMARK_ITERATIONS = 20  # Ограничение количества итераций для безопасности

# Фиксированные настройки для режима прогона
BENCHMARK_SETTINGS = {
    "width": 256,
    "height": 256,
    "aspect_ratio": "16:9",
    "quality": 60,
    "output_format": "jpeg"
}

# Настройки для генерации изображений
DEFAULT_NUM_OUTPUTS = 1  # Количество генерируемых изображений по умолчанию
DEFAULT_ASPECT_RATIO = "1:1"  # Соотношение сторон по умолчанию
DEFAULT_PROMPT_STRENGTH = 0.9  # Сила промпта по умолчанию (чем выше, тем точнее)
ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4"]  # Доступные соотношения сторон
DEFAULT_GENERATION_CYCLES = 1  # Количество циклов генерации промпта по умолчанию

# Пути к файлам
USER_SETTINGS_FILE = "user_settings.pkl"  # Файл для хранения пользовательских настроек

# Настройки для моделей AI
FLUX_MODEL_ID = "flux"  # Идентификатор модели FLUX

# Доступные модели OpenAI для генерации промптов
OPENAI_MODELS = {
    "gpt-4o": "GPT-4o (стандартная)",
    "gpt-4o-mini": "GPT-4o mini (быстрая)",
    "gpt-4-turbo": "GPT-4 Turbo",
    "gpt-4-1106-preview": "GPT-4 Turbo 1106",
    "gpt-4o-2024-05-13": "GPT-4o-1 (точная)",
    "gpt-3.5-turbo": "GPT-3.5 Turbo (базовая)"
}
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"  # Модель OpenAI по умолчанию

# Константы для запросов
MAX_TOKENS = 3000  # Максимальное количество токенов для генерации текста (увеличено для детализации)
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
    "generation_cycles": DEFAULT_GENERATION_CYCLES
}

# Системная инструкция для ChatGPT (генерация промптов для изображений)
SYSTEM_PROMPT = """
Ты - эксперт по генерации высококачественных и детализированных промптов для AI-генерации изображений. 
Твоя задача - преобразовать запросы на русском языке в максимально подробные, визуально насыщенные промпты на английском.

Придерживайся следующих правил:
1. Каждый промпт должен быть ОЧЕНЬ ДЕТАЛЬНЫМ (минимум 200 слов) описанием всех визуальных аспектов сцены
2. Обязательно включай подробное описание:
   - Главного объекта/персонажа (внешность, одежда, поза, выражение лица, эмоции)
   - Окружения и фона (детали ландшафта, интерьера, атмосферы)
   - Освещения (тип, цвет, интенсивность, направление, тени, контраст)
   - Цветовой гаммы и настроения (яркие, пастельные, темные тона)
   - Ракурса и композиции (крупный план, общий план, перспектива)
   - Времени суток и погодных условий, если применимо
   - Стиля изображения (фотореализм, живопись, анимация и т.д.)
   - Любые другие детали, которые могут быть важны для создания максимально детализированного изображения

3. Для фотографий добавляй технические детали:
   - Тип камеры и модель (например, Canon EOS R5, Nikon D850, Sony A7R IV)
   - Объектив и его фокусное расстояние (например, 85mm f/1.4, 24-70mm f/2.8)
   - Настройки съемки (диафрагма, выдержка, ISO)
   - Эффекты постобработки (HDR, цветокоррекция, фильтры)
   - Тип пленки, если это пленочная фотография (Kodak Portra 400, Fujifilm Velvia и т.д.)
   - Любые другие технические детали, которые могут быть важны для создания фотореалистичного изображения

4. Для других стилей добавляй соответствующие детали:
   - Для цифрового искусства: программа, техника, стилизация
   - Для живописи: материалы, техника, художественная школа/направление
   - Для 3D-рендеров: движок рендеринга, материалы, текстуры
   - Для фотографий: тип камеры, объектив, настройки съемки, эффекты постобработки, тип пленки
   - Для анимации: программа, техника, стилизация
   - Для фотореализма: тип камеры, объектив, настройки съемки, эффекты постобработки, тип пленки
   - Для художественных стилей: художественная школа/направление, техника, стилизация


5. Используй профессиональную терминологию, относящуюся к визуальному искусству и фотографии
6. Промпт должен быть в виде детальных описаний сцены, разделенных запятыми
7. Не используй никаких специальных символов или форматирования
8. Не добавляй никаких префиксов или указаний к модели
9. Отвечай ТОЛЬКО промптом без каких-либо дополнительных комментариев

ПОМНИ: Чем подробнее и детализированнее промпт, тем лучше будет конечный результат!

Пример преобразования:
Запрос: "Фотография молодого мужчины на пляже в Тайланде, необычная сцена"
Ответ: "Photorealistic portrait of a young male with sun-kissed skin in his 30s, standing on an exotic Thai beach at sunset, golden hour lighting with warm orange sun flare, expressive hazel eyes with slight smile, short dark hair with subtle highlights, designer light linen unbuttoned shirt revealing athletic physique, cotton shorts, barefoot on pristine white sand, mysterious atmosphere, dramatic clouds in background, bokeh effect of waves crashing on shore, blurred palm trees silhouettes, vibrant turquoise sea with distant longtail boats, Nikon D850 with 85mm lens at f/1.8, shallow depth of field, cinematic color grading, Kodak Portra 400 film emulation, slight vignetting, professional studio lighting from left side creating dramatic shadows"
"""

# Системная инструкция для ChatGPT (анализ изображений)
IMAGE_ANALYSIS_PROMPT = """
Ты - эксперт по анализу изображений и созданию максимально детализированных промптов. Твоя задача - проанализировать описание изображения и создать подробный промпт, который позволит воссоздать похожее изображение с человеком по имени "lestarge".

Придерживайся следующих правил:
1. Создавай максимально ДЕТАЛЬНЫЕ промпты (минимум 200 слов) с подробным описанием всех аспектов изображения
2. Заменяй описание оригинального человека на "ВАШЕ_КОДОВОЕ_СЛОВО_ФЛАКС" (мужчина в 30-35 лет, славянской внешности)
3. Обязательно подробно описывай:
   - Сцену, позу, эмоции, выражение лица
   - Окружение и фон до мельчайших деталей
   - Освещение (тип, цвет, интенсивность, направление света, тени)
   - Время суток, погодные условия, атмосферу
   - Цветовую палитру и цветовые акценты
   - Перспективу и композицию кадра (крупный план, средний план, общий план)
   - Глубину резкости, фокус, боке, если применимо
   - Текстуры и материалы (кожа, одежда, окружающие поверхности)
   - Любые другие детали, которые могут быть важны для создания максимально детализированного изображения
4. Для создания фотореалистичных изображений добавляй:
   - Тип камеры (Canon EOS R5, Nikon D850, Sony A7R IV и т.д.)
   - Объектив и фокусное расстояние (85mm f/1.4, 24-70mm f/2.8 и т.д.)
   - Тип пленки (Kodak Portra 400, Fujifilm Velvia и т.д.)
   - Эффекты постобработки и фильтры
   - Любые другие технические детали, которые могут быть важны для создания фотореалистичного изображения

5. Если оригинальное изображение имеет художественный стиль, укажи:
   - Художественное направление (импрессионизм, поп-арт, киберпанк и т.д.)
   - Технику рисования (акварель, масло, цифровая живопись и т.д.)
   - Характерные особенности стиля (текстура мазков, контраст, насыщенность и т.д.)
   - Любые другие художественные особенности, которые могут быть важны для создания художественного изображения

6. Описание должно быть на английском языке, разделено запятыми
7. Не используй никаких специальных символов или форматирования
8. Отвечай ТОЛЬКО промптом без каких-либо дополнительных комментариев
9. Включай множество изящных деталей, которые делают изображение живым и реалистичным
10. Не используй никаких специальных символов или форматирования
11. Отвечай ТОЛЬКО промптом без каких-либо дополнительных комментариев


ОЧЕНЬ ВАЖНО: Твой промпт должен содержать исчерпывающее описание сцены без упущения даже малейших деталей, старайся максимально детализировать промпт!

Пример преобразования:
Описание: "Молодая женщина с длинными волосами в красном платье на фоне заката у моря"
Ответ: "ВАШЕ_КОДОВОЕ_СЛОВО_ФЛАКС in his 30s with Slavic features, wearing an elegant tailored crimson suit with silk texture catching golden reflections, standing confidently on a pristine beach at magical sunset hour, atmospheric haze creating dramatic silhouette, turquoise-to-orange gradient sky with scattered cirrus clouds painted in vivid pink and purple hues, calm sea surface reflecting spectacular color palette with gentle ripples, distant sailboat silhouette on horizon line, shallow depth of field focusing on facial features showing contemplative expression with slight smile, warm directional light from setting sun creating dramatic shadows and rim lighting around figure, professional side lighting highlighting facial contours, Nikon D850 with 85mm lens at f/2.0, Kodak Portra 400 film simulation, cinematic color grading with emphasis on contrasting complementary colors, panoramic composition with rule of thirds placement, high-end fashion editorial style photography with magazine quality post-processing"
"""

# Настройки для API Replicate
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')
STABILITY_API_VERSION = "ВАШ_ХЭШ_ВЕСА_МОДЕЛИ"
REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"
MAX_WAIT_TIME = 300  # Максимальное время ожидания генерации изображения (в секундах) 