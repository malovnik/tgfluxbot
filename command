#!/bin/bash

# Получаем абсолютный путь к текущему скрипту
SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)"

# Переходим в директорию проекта
cd "$SCRIPT_PATH"

# Используем системный Python, но добавляем путь к библиотекам виртуального окружения
export PYTHONPATH="$SCRIPT_PATH:$SCRIPT_PATH/.venv/lib/python3.9/site-packages:$PYTHONPATH"

# Запускаем программу
/usr/bin/python3 "$SCRIPT_PATH/bot.py" 