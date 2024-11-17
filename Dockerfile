# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в рабочую директорию
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем переменные окружения
ENV BOT_TOKEN=your_bot_token
ENV CHAT_ID=your_chat_id

# Команда для запуска бота
CMD ["python", "tg_bot/bot/main.py"]
