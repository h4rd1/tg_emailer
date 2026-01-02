# Используем официальный образ Python Alpine
FROM python:3.11-alpine

# Метаданные
LABEL description="Telegram bot for forwarding messages to email"
LABEL version="1.0.0"

WORKDIR /app

# Копируем файлы
COPY bot.py ./
COPY config.py ./
COPY requirements.txt ./
COPY docker-entrypoint.sh ./

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Настраиваем права ДО смены пользователя
RUN chmod +x docker-entrypoint.sh

# Создаём непривилегированного пользователя
RUN adduser -D botuser
USER botuser

# Точка входа
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "bot.py"]
