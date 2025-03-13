# FLUX Telegram Image Generator Bot

A Telegram bot for generating AI images using FLUX model. This bot allows users to create high-quality images from text prompts with various customizable settings.

[Русская версия ниже / Russian version below](#flux-telegram-bot-ru)

## Features

- Generate images from text prompts using FLUX AI model
- Voice message transcription and image generation
- Image analysis and creation of similar images with you as the main subject
- Customize aspect ratio, quality, and other image parameters
- Support for multiple OpenAI models for prompt enhancement
- User settings persistence
- Benchmark mode for parameter testing
- Private mode for restricted access

## Requirements

- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key
- Replicate API Token

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/malovnik/tgfluxbot.git
   cd tgfluxbot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys (see `.env.example` for reference)

## Configuration

Create a `.env` file in the root directory with the following variables:
```
TELEGRAM_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
REPLICATE_API_TOKEN=your_replicate_api_token
OWNER_USERNAME=your_telegram_username
OWNER_CHAT_ID=your_telegram_chat_id
```

You can also customize the bot settings in `modules/config.py` according to your preferences.

## Important Changes Before Using

Before running the bot, you need to make the following changes to the code:

### In file `modules/ai_services.py`:

1. Replace the line `"version": "ВАШИ_ВЕСА_МОДЕЛИ"` with the ID of your trained FLUX model weights. This will be a string representing the model weights hash, for example:
   ```python
   "version": "46e0613db2f215b0690b3535b0aa3e6436a517d08e52f6c84549c2bf22bc5f81"
   ```

2. Replace all mentions of `"ВАШ_ПРЕФИКС_ФЛАКС"` on the string `"ВАШ_ПРЕФИКС_ФЛАКС"` with the codeword used for your FLUX model. This is a secret codeword that is recovered during model training and is necessary for correct results. For example:
   ```python
   if not prompt.lower().startswith("dreamshaper"):
       prompt = f"dreamshaper {prompt}"
   ```
   
   Search and replace for the string `"ВАШ_ПРЕФИКС_ФЛАКС"` will find all places where this replacement is required.

These changes are necessary for the bot to work correctly with your trained FLUX model. Without these changes, image generation will be impossible or incorrect.

## Project Structure

```
tgfluxbot/
├── bot.py                  # Main file to run the bot
├── modules/                # Bot modules
│   ├── __init__.py         # Package initialization
│   ├── ai_services.py      # Interaction with AI services (OpenAI, Replicate)
│   ├── bot.py              # Bot core logic
│   ├── config.py           # Configuration and constants
│   ├── handlers.py         # Command and message handlers
│   └── settings.py         # User settings management
├── .env                    # Environment variables file (not included in repository)
├── .gitignore              # Git exclude file
├── requirements.txt        # Project dependencies
└── README.md               # Documentation
```

## Usage

1. Start the bot:
   ```bash
   python bot.py
   ```

2. Open Telegram and start a conversation with your bot.

3. Use `/start` command to begin and follow the instructions.

## Bot Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/settings` - Configure bot settings
- `/cancel` - Cancel the current operation (reset dialogue)
- `/generate` - Generate a new image
- `/benchmark` - Run parameter benchmark (owner only)

## Customization

Users can customize various parameters:
- Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
- Number of outputs (1-4)
- Prompt strength (0.75-1.0)
- OpenAI model for prompt enhancement
- Generation cycles (1-5)

### OpenAI Models

The bot provides a choice of several OpenAI models for prompt generation:

- **GPT-4o** (standard) - most accurate, creates detailed and high-quality prompts
- **GPT-4o mini** - works faster, but may be less accurate
- **GPT-4o-1** - specialized accurate model for complex requests
- **GPT-3.5 Turbo** - basic model, suitable for simple requests, works quickly

### Generation Cycles

The generation cycles feature allows you to create multiple variants of images for a single request:

1. When selecting 1 cycle (default), the bot will create one prompt and generate images based on it
2. When selecting 2-5 cycles, the bot will:
   - Generate a new prompt for each cycle based on the original request
   - Create images for each prompt
   - Send the results sequentially with an indication of the cycle number

This feature is useful for getting diverse interpretations of your request.

## Private Mode

By default, the bot is configured to work with only one user (the owner). This protects you from unnecessary API expenses and prevents unauthorized use.

To work in private mode:
1. In the `modules/config.py` file, make sure the authorization settings contain your data:
```python
OWNER_USERNAME = "your_username"  # Your Telegram username
OWNER_CHAT_ID = your_chat_id      # Your Telegram Chat ID
BOT_PRIVATE = True                # Enable private mode
```

To find out your Chat ID, you can use the @userinfobot bot.

If you want to make the bot publicly available, set `BOT_PRIVATE = False`.

## Technologies

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Library for working with Telegram Bot API
- [OpenAI API](https://openai.com/api/) - For prompt generation and image analysis
- [Replicate API](https://replicate.com/) - For generating images using the FLUX model
- [Whisper API](https://openai.com/research/whisper) - For speech recognition

## Notes

- Image generation can take up to 3 minutes depending on the load on Replicate servers
- For best results, try to give detailed descriptions of the desired images
- If the bot stops responding to commands, use `/cancel` to reset the state

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<a name="flux-telegram-bot-ru"></a>
# FluxMalovnikTelegram (Русская версия)

Telegram бот для генерации изображений с использованием модели FLUX и ChatGPT для создания промптов.

## Возможности

- 📝 Генерация изображений на основе текстовых описаний
- 🎤 Распознавание голосовых сообщений и генерация изображений на их основе
- 🖼 Анализ изображений и создание похожих с вами в главной роли
- ⚙️ Настройка параметров генерации (количество изображений, соотношение сторон, уровень следования промпту)
- 🔄 Возможность редактирования промптов перед генерацией

## Требования

- Python 3.8+
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- OpenAI API Key
- Replicate API Token

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/malovnik/tgfluxbot.git
   cd tgfluxbot
   ```

2. Создайте и активируйте виртуальную среду:
   ```bash
   python -m venv .venv
   # Для Windows:
   .venv\Scripts\activate
   # Для macOS/Linux:
   source .venv/bin/activate
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Создайте файл `.env` со своими API-ключами (см. пример в `.env.example`)

## Конфигурация

Создайте файл `.env` в корне проекта со следующим содержимым:
```
TELEGRAM_TOKEN=ваш_телеграм_токен
OPENAI_API_KEY=ваш_openai_ключ
REPLICATE_API_TOKEN=ваш_replicate_токен
OWNER_USERNAME=ваше_имя_пользователя_telegram
OWNER_CHAT_ID=ваш_идентификатор_чата_telegram
```

Вы также можете настроить параметры бота в файле `modules/config.py` в соответствии с вашими предпочтениями.

## Важные изменения перед использованием

Перед запуском бота необходимо внести следующие изменения в код:

### В файле `modules/ai_services.py`:

1. Замените строку `"version": "ВАШИ_ВЕСА_МОДЕЛИ"` на идентификатор весов вашей обученной модели FLUX. Это будет строка, представляющая хэш весов модели, например:
   ```python
   "version": "46e0613db2f215b0690b3535b0aa3e6436a517d08e52f6c84549c2bf22bc5f81"
   ```

2. Замените все упоминания `"ВАШ_ПРЕФИКС_ФЛАКС"` на кодовое слово, которое используется для вашей модели FLUX. Это секретное кодовое слово, которое восстанавливается при обучении модели и необходимо для получения правильных результатов. Например:
   ```python
   if not prompt.lower().startswith("dreamshaper"):
       prompt = f"dreamshaper {prompt}"
   ```
   
   Поиск и замена по строке `"ВАШ_ПРЕФИКС_ФЛАКС"` позволит найти все места, где требуется эта замена.

Эти изменения необходимы для корректной работы бота с вашей обученной моделью FLUX. Без этих замен генерация изображений будет невозможна или некорректна.

## Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/settings` - Настройки генерации изображений
- `/cancel` - Отменить текущую операцию (сбросить диалог)
- `/generate` - Сгенерировать новое изображение
- `/benchmark` - Запустить тестирование параметров (только для владельца)

## Приватный режим

По умолчанию бот настроен на работу только с одним пользователем (владельцем). Это защищает вас от лишних расходов на API и предотвращает неавторизованное использование.

Для работы в приватном режиме:
1. В файле `modules/config.py` убедитесь, что настройки авторизации содержат ваши данные:
```python
OWNER_USERNAME = "ваш_username"  # Ваше имя пользователя в Telegram
OWNER_CHAT_ID = ваш_chat_id      # Ваш Chat ID в Telegram
BOT_PRIVATE = True               # Включение приватного режима
```

Чтобы узнать свой Chat ID, можно использовать бота @userinfobot.

Если вы хотите сделать бота общедоступным, установите `BOT_PRIVATE = False`.
