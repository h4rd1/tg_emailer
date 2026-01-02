import os
import re
import logging
import sys
from typing import Optional

import aiosmtplib
from email.mime.text import MIMEText
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# Валидация email
def is_valid_email(email: str) -> bool:
    if not email or not isinstance(email, str):
        return False
    return re.match(r"^[^@]+@[^@]+\.[^@]+$", email) is not None

# Чтение и валидация переменных окружения
def get_env_var(var_name: str, default: Optional[str] = None) -> str:
    value = os.getenv(var_name, default)
    if not value or not value.strip():
        raise ValueError(f"{var_name} не задана или пуста")
    return value.strip()

try:
    SMTP_SERVER = get_env_var("SMTP_SERVER")
    SMTP_PORT = int(get_env_var("SMTP_PORT"))
    EMAIL = get_env_var("EMAIL")
    PASSWORD = get_env_var("PASSWORD")
    RECIPIENT = get_env_var("RECIPIENT")
    TELEGRAM_TOKEN = get_env_var("TELEGRAM_TOKEN")

    # Дополнительная валидация email
    if not is_valid_email(EMAIL):
        raise ValueError("EMAIL имеет некорректный формат")
    if not is_valid_email(RECIPIENT):
        raise ValueError("RECIPIENT имеет некорректный формат")

    # Проверка портов
    if SMTP_PORT < 1024 and SMTP_PORT not in [465, 587]:
        logger.warning(f"Использование порта {SMTP_PORT} может быть небезопасным")

except ValueError as e:
    logger.error(f"Ошибка конфигурации: {e}")
    sys.exit(1)

def clean_text(text: str) -> str:
    """Оставляет печатаемые символы + переводы строк, убирает лишние пробелы."""
    cleaned = ''.join(
        char for char in text
        if char.isprintable() or char in '\n\r\t'
    )
    return cleaned.strip()

async def send_email(text: str) -> bool:
    try:
        # Очищаем и проверяем текст
        cleaned_text = clean_text(text)
        if not cleaned_text:
            cleaned_text = "[Пустое сообщение]"

        # Создаём MIME‑сообщение
        msg = MIMEText(cleaned_text, 'plain', 'utf-8')
        msg['Subject'] = 'Сообщение из Telegram'
        msg['From'] = EMAIL
        msg['To'] = RECIPIENT
        msg['MIME-Version'] = '1.0'

        # Настройки SMTP
        smtp_config = {
            'hostname': SMTP_SERVER,
            'port': SMTP_PORT,
            'username': EMAIL,
            'password': PASSWORD,
            'validate_certs': True,
            'timeout': 30
        }

        if SMTP_PORT == 465:
            smtp_config['use_tls'] = True
        elif SMTP_PORT == 587:
            smtp_config['start_tls'] = True
        else:
            smtp_config['use_tls'] = False
            smtp_config['start_tls'] = False

        # Отправка
        await aiosmtplib.send(msg, **smtp_config)
        logger.info(f"Письмо отправлено: To={RECIPIENT}, Subject='Сообщение из Telegram'")
        return True

    except aiosmtplib.SMTPAuthenticationError:
        logger.error("Ошибка аутентификации SMTP: неверные EMAIL или PASSWORD")
        return False
    except (aiosmtplib.SMTPException, OSError) as e:
        logger.error(f"SMTP ошибка: {type(e).__name__}: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке email: {type(e).__name__}: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправьте текстовое сообщение — оно будет отправлено на почту!\n"
        "Доступные команды:\n"
        "/start — начало работы\n"
        "/help — помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бот пересылает текстовые сообщения на указанный email.\n"
        "Просто напишите текст — и он будет отправлен."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"[DEBUG] Получено сообщение (длина: {len(text)}): {text[:100]}")

    if not text:
        await update.message.reply_text("Пожалуйста, отправьте текстовое сообщение.")
        return

    # Ограничение длины
    text = text[:10000]

    success = await send_email(text)
    if success:
        await update.message.reply_text("Письмо отправлено!")
    else:
        await update.message.reply_text(
            "Не удалось отправить письмо. Проверьте настройки SMTP и интернет‑соединение."
        )

if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Хендлеры
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен. Ожидание сообщений...")
    app.run_polling()
