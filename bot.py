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

# Импорт конфигурации
from config import Config

# Настройка логирования (остаётся без изменений)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Очищаем и проверяем текст (остаётся без изменений)
def clean_text(text: str) -> str:
    cleaned = ''.join(
        char for char in text
        if char.isprintable() or char in '\n\r\t'
    )
    return cleaned.strip()

# Отправка email (остаётся почти без изменений)
async def send_email(text: str) -> bool:
    try:
        cleaned_text = clean_text(text)
        if not cleaned_text:
            cleaned_text = "[Пустое сообщение]"

        msg = MIMEText(cleaned_text, 'plain', 'utf-8')
        msg['Subject'] = 'Сообщение из Telegram'
        msg['From'] = Config.EMAIL
        msg['To'] = Config.RECIPIENT
        msg['MIME-Version'] = '1.0'

        smtp_config = {
            'hostname': Config.SMTP_SERVER,
            'port': Config.SMTP_PORT,
            'username': Config.EMAIL,
            'password': Config.PASSWORD,
            'validate_certs': True,
            'timeout': 30
        }

        if Config.SMTP_PORT == 465:
            smtp_config['use_tls'] = True
        elif Config.SMTP_PORT == 587:
            smtp_config['start_tls'] = True
        else:
            smtp_config['use_tls'] = False
            smtp_config['start_tls'] = False

        await aiosmtplib.send(msg, **smtp_config)
        logger.info(f"Письмо отправлено: To={Config.RECIPIENT}, Subject='Сообщение из Telegram'")
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

# Обработчики Telegram (остаются без изменений)
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

    text = text[:10000]
    success = await send_email(text)
    if success:
        await update.message.reply_text("Письмо отправлено!")
    else:
        await update.message.reply_text(
            "Не удалось отправить письмо. Проверьте настройки SMTP и интернет‑соединение."
        )

if __name__ == '__main__':
    # Валидируем настройки перед запуском
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        sys.exit(1)

    app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен. Ожидание сообщений...")
    app.run_polling()
