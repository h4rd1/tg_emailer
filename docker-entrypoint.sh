#!/bin/sh
set -e

echo "Проверяем переменные окружения..."

# Список обязательных переменных (через пробел)
REQUIRED_ENV="SMTP_SERVER SMTP_PORT EMAIL PASSWORD RECIPIENT TELEGRAM_TOKEN"

# Функция для проверки существования переменной
is_set() {
    eval "test -n \"\${$1+\"var_is_set\"}\""
}

for VAR in $REQUIRED_ENV; do
    if ! is_set "$VAR"; then
        echo "Ошибка: переменная окружения $VAR не задана!"
        exit 1
    fi
done

# Проверка SMTP_PORT на числовой формат
if ! echo "$SMTP_PORT" | grep -qE '^[0-9]+$'; then
    echo "Ошибка: SMTP_PORT должен быть числом!"
    exit 1
fi

echo "Все переменные окружения проверены. Запускаем бота..."

# Выполняем команду из CMD
exec "$@"
