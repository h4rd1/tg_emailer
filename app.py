import os
import aiosmtplib
from email.mime.text import MIMEText
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Чтение переменных окружения
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
RECIPIENT = os.getenv("RECIPIENT")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def clean_text(text: str) -> str:
    """Оставляет все печатаемые символы + переводы строк (поддержка Unicode)."""
    return ''.join(
        char for char in text
        if char.isprintable() or char in '\n\r\t'
    )

async def send_email(text: str):
    try:
        # 1. Очищаем текст
        cleaned_text = clean_text(text)
        if not cleaned_text:
            cleaned_text = "[Пустое сообщение]"

        # 2. Создаём MIME‑сообщение
        msg = MIMEText(cleaned_text, 'plain', 'utf-8')
        msg['Subject'] = 'Сообщение из Telegram'
        msg['From'] = EMAIL
        msg['To'] = RECIPIENT
        msg['MIME-Version'] = '1.0'

        # 3. Настройки SMTP (исправлено: убираем конфликт TLS)
        smtp_config = {
            'hostname': SMTP_SERVER,
            'port': SMTP_PORT,
            'username': EMAIL,
            'password': PASSWORD,
            'validate_certs': True,
        }

        # Определяем режим шифрования по порту
        if SMTP_PORT == 465:
            smtp_config['use_tls'] = True  # Для порта 465 (SSL/TLS)
        elif SMTP_PORT == 587:
            smtp_config['start_tls'] = True  # Для порта 587 (STARTTLS)
        else:
            # Для других портов (например, 25) — без шифрования (не рекомендуется)
            smtp_config['use_tls'] = False
            smtp_config['start_tls'] = False

        # 4. Отправка через aiosmtplib
        await aiosmtplib.send(
            msg,
            **smtp_config
        )
        logger.info("Письмо отправлено успешно")

    except Exception as e:
        logger.error(f"Ошибка при отправке email: {type(e).__name__}: {e}")
        logger.error(f"Исходный текст: {text[:200]}...")
        logger.error(f"Очищенный текст: {clean_text(text)[:200]}...")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отправьте сообщение — оно будет отправлено на почту!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    logger.info(f"[DEBUG] Получено сообщение (длина: {len(text)}): {text}")
    if text:
        logger.info(f"[DEBUG] Первые 100 символов: {text[:100]}")
        logger.info(f"[DEBUG] Коды первых 20 символов: {[ord(c) for c in text[:20]]}")

    try:
        await send_email(text)
        await update.message.reply_text("Письмо отправлено!")
    except Exception as e:
        error_msg = f"Ошибка при отправке: {str(e)}"
        logger.error(error_msg)
        await update.message.reply_text(error_msg)

def validate_env():
    errors = []
    for var in ['EMAIL', 'PASSWORD', 'RECIPIENT', 'TELEGRAM_TOKEN']:
        value = os.getenv(var)
        if not value:
            errors.append(f"{var} не задана")
        elif not isinstance(value, str):
            errors.append(f"{var} имеет неверный тип")
        elif not value.strip():
            errors.append(f"{var} пуста")


    # Проверка email
    if EMAIL and '@' not in EMAIL:
        errors.append("EMAIL не содержит @")
    if RECIPIENT and '@' not in RECIPIENT:
        errors.append("RECIPIENT не содержит @")

    if errors:
        for error in errors:
            logger.error(error)
        exit(1)

if __name__ == '__main__':
    validate_env()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен. Ожидание сообщений...")
    app.run_polling()
