import os
import re
from typing import Optional



class Config:
    # --- SMTP-настройки ---
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))

    # Email отправителя и пароль
    EMAIL: str = os.getenv("EMAIL", "your_email@example.com")
    PASSWORD: str = os.getenv("PASSWORD", "your_password")

    # Email получателя
    RECIPIENT: str = os.getenv("RECIPIENT", "recipient@example.com")

    # --- Telegram-настройки ---
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "your_telegram_token")

    # --- LDAP-настройки ---
    LDAP_SERVER: str = os.getenv("LDAP_SERVER", "ldap.example.com")
    LDAP_PORT: int = int(os.getenv("LDAP_PORT", 636))
    LDAP_USE_SSL: bool = bool(os.getenv("LDAP_USE_SSL", True))
    LDAP_BASE_DN: str = os.getenv("LDAP_BASE_DN", "dc=example,dc=com")
    LDAP_USER: str = os.getenv("LDAP_USER", "cn=admin,dc=example,dc=com")
    LDAP_PASSWORD: str = os.getenv("LDAP_PASSWORD", "your_ldap_password")

    # --- Дополнительные параметры ---
    # Допустимые порты для предупреждения
    SAFE_PORTS: set[int] = {465, 587}

    @classmethod
    def validate(cls) -> None:
        """Проверяет корректность настроек."""
        errors = []

        # Проверка обязательных полей
        required_fields = [
            "SMTP_SERVER", "SMTP_PORT", "EMAIL", "PASSWORD",
            "RECIPIENT", "TELEGRAM_TOKEN",
            "LDAP_SERVER", "LDAP_PORT", "LDAP_BASE_DN",
            "LDAP_USER", "LDAP_PASSWORD"
        ]
        for field in required_fields:
            value = getattr(cls, field)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"{field} не задана или пуста")

        # Валидация email
        if not cls.is_valid_email(cls.EMAIL):
            errors.append("EMAIL имеет некорректный формат")
        if not cls.is_valid_email(cls.RECIPIENT):
            errors.append("RECIPIENT имеет некорректный формат")

        # Проверка порта SMTP
        if cls.SMTP_PORT < 1 or cls.SMTP_PORT > 65535:
            errors.append("SMTP_PORT должен быть в диапазоне 1–65535")
        elif cls.SMTP_PORT not in cls.SAFE_PORTS:
            print(f"Предупреждение: Использование порта {cls.SMTP_PORT} может быть небезопасным")

        # Проверка порта LDAP
        if cls.LDAP_PORT < 1 or cls.LDAP_PORT > 65535:
            errors.append("LDAP_PORT должен быть в диапазоне 1–65535")

        if errors:
            raise ValueError("Ошибки конфигурации:\n" + "\n".join(errors))

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Проверяет формат email."""
        if not email or not isinstance(email, str):
            return False
        # Улучшенное регулярное выражение для email
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None
