import os
import re
import logging
import sys
from typing import Optional, Dict, List

import aiosmtplib
from email.mime.text import MIMEText
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import ldap3

from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

user_states: Dict[int, Dict] = {}

def clean_text(text: str) -> str:
    cleaned = ''.join(
        char for char in text
        if char.isprintable() or char in '\n\r\t'
    )
    return cleaned.strip()

def connect_ldap() -> ldap3.Connection:
    server = ldap3.Server(Config.LDAP_SERVER, port=Config.LDAP_PORT, use_ssl=Config.LDAP_USE_SSL)
    conn = ldap3.Connection(
        server,
        user=Config.LDAP_USER,
        password=Config.LDAP_PASSWORD,
        auto_bind=True
    )
    return conn

async def find_users_by_surname(surname: str) -> List[Dict[str, str]]:
    try:
        conn = connect_ldap()
        search_filter = f"(&(objectClass=person)(sn={surname}))"
        conn.search(
            search_base=Config.LDAP_BASE_DN,
            search_filter=search_filter,
            attributes=['cn', 'mail', 'sn']
        )
        results = []
        for entry in conn.entries:
            results.append({
                'name': str(entry.cn),
                'email': str(entry.mail),
                'surname': str(entry.sn)
            })
        return results
    except ldap3.core.exceptions.LDAPException as e:
        logger.error(f"Ошибка LDAP: {e}")
        return []

async def send_email(text: str, from_email: str) -> bool:
    try:
        cleaned_text = clean_text(text)
        if not cleaned_text:
            cleaned_text = "[Пустое сообщение]"

        msg = MIMEText(cleaned_text, 'plain', 'utf-8')
        msg['Subject'] = 'Сообщение из Telegram'
        msg['From'] = from_email
        msg['To'] = Config.RECIPIENT
        msg['MIME-Version'] = '1.0'

        smtp_config = {
            'hostname': Config.SMTP_SERVER,
            'port': Config.SMTP_PORT,
            'username': from_email,
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
        logger.info(f"Письмо отправлено: From={from_email}, To={Config.RECIPIENT}")
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
        "Чтобы отправить письмо, сначала найдите отправителя:\n"
        "/find <фамилия>\n"
        "Например: /find Иванов\n\n"
        "Доступные команды:\n"
        "/start — начало работы\n"
        "/help — помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бот пересылает текстовые сообщения на указанный email,\n"
        "но ТОЛЬКО после выбора отправителя через /find.\n\n"
        "Как использовать:\n"
        "1. /find Иванов — найти пользователей с фамилией «Иванов»\n"
        "2. Выберите отправителя из списка\n"
        "3. Отправьте текст — он уйдёт с выбранного email"
    )

async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите фамилию для поиска: /find Иванов")
        return

    surname = context.args[0]
    users = await find_users_by_surname(surname)

    if not users:
        await update.message.reply_text(f"Пользователи с фамилией '{surname}' не найдены.")
        return

    if len(users) > 20:
        await update.message.reply_text(
            f"Найдено слишком много пользователей ({len(users)}).\n"
            "Уточните фамилию или используйте инициалы."
        )
        return

    user_id = update.effective_user.id
    user_states[user_id] = {'users': users, 'message_text': None}

    keyboard = [
        [InlineKeyboardButton(f"{u['name']} <{u['email']}>", callback_data=f"select_{i}")]
        for i, u in enumerate(users)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
               f"Найденные пользователи ({len(users)}):",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if not user_states.get(user_id):
        await query.edit_message_text("Сеанс поиска истек. Начните заново с /find.")
        return

    if data.startswith("select_"):
        idx = int(data.split("_")[1])
        selected_user = user_states[user_id]['users'][idx]
        email = selected_user['email']

        # Запрашиваем текст сообщения
        user_states[user_id]['sender_email'] = email
        await query.edit_message_text(
            f"Выбран отправитель: {email}\n"
            "Теперь отправьте текст сообщения для отправки:"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"[DEBUG] Получено сообщение (длина: {len(text)}): {text[:100]}")

    if not text:
        await update.message.reply_text("Пожалуйста, отправьте текстовое сообщение.")
        return

    text = text[:10000]  # Ограничение длины сообщения

    # Если есть сохранённое состояние — используем выбранный отправитель
    if user_states.get(user_id) and 'sender_email' in user_states[user_id]:
        # Отправляем сообщение с выбранным отправителем
        success = await send_email(text, user_states[user_id]['sender_email'])
        if success:
            await update.message.reply_text(
                f"Письмо отправлено от {user_states[user_id]['sender_email']}!"
            )
        else:
            await update.message.reply_text(
                "Не удалось отправить письмо. Проверьте настройки SMTP и интернет‑соединение."
            )

        # Очищаем состояние после отправки
        user_states.pop(user_id, None)

    else:
        # Нет выбранного отправителя — напоминаем про /find
        await update.message.reply_text(
            "Чтобы отправить письмо, сначала найдите отправителя:\n"
            "/find <фамилия>\n"
            "Например: /find Иванов"
        )

# Обработчик отмены выбора (опционально)
async def cancel_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_states.get(user_id):
        user_states.pop(user_id, None)
        await update.message.reply_text("Выбор отменён. Вы можете начать заново с /find.")
    else:
        await update.message.reply_text("Нет активного выбора для отмены.")


if __name__ == '__main__':
    # Валидируем настройки перед запуском
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        sys.exit(1)

    app = Application.builder().token(Config.TELEGRAM_TOKEN).build()


    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("find", find_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("cancel", cancel_selection))  # Опциональная команда отмены


    logger.info("Бот запущен. Ожидание сообщений...")
    app.run_polling()
