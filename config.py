# config.py
import os
import re 
from typing import Optional

class Config:
    # SMTP‑сервер и порт
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))


    # Email отправителя и пароль
    EMAIL: str = os.getenv("EMAIL", "your_email@example.com")
    PASSWORD: str = os.getenv("PASSWORD", "your_password")

    # Email получателя
    RECIPIENT: str = os.getenv("RECIPIENT", "recipient@example.com")

    # Токен Telegram‑бота
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "your_telegram_token")

    # Допустимые порты для предупреждения
    SAFE_PORTS: set[int] = {465, 587}

    @classmethod
    def validate(cls) -> None:
        """Проверяет корректность настроек."""
        errors = []

        # Проверка обязательных полей
        required_fields = ["SMTP_SERVER", "SMTP_PORT", "EMAIL", "PASSWORD", "RECIPIENT", "TELEGRAM_TOKEN"]
        for field in required_fields:
            value = getattr(cls, field)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"{field} не задана или пуста")

        # Валидация email
        if not cls.is_valid_email(cls.EMAIL):
            errors.append("EMAIL имеет некорректный формат")
        if not cls.is_valid_email(cls.RECIPIENT):
            errors.append("RECIPIENT имеет некорректный формат")

        # Проверка порта
        if cls.SMTP_PORT < 1024 and cls.SMTP_PORT not in cls.SAFE_PORTS:
            print(f"Предупреждение: Использование порта {cls.SMTP_PORT} может быть небезопасным")

        if errors:
            raise ValueError("Ошибки конфигурации:\n" + "\n".join(errors))

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Проверяет формат email."""
        if not email or not isinstance(email, str):
            return False
        return re.match(r"^[^@]+@[^@]+\.[^@]+$", email) is not None
