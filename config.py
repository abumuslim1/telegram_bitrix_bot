"""
Конфигурация бота.

ПЕРЕД ЗАПУСКОМ:
1. Заполните TELEGRAM_BOT_TOKEN токеном вашего бота.
2. Укажите данные доступа к Bitrix24 (домен и вебхук).
3. Задайте общий пароль для авторизации сотрудников.
"""

TELEGRAM_BOT_TOKEN = "PASTE_YOUR_TELEGRAM_BOT_TOKEN_HERE"

# Общий пароль для всех сотрудников (согласно ТЗ)
COMMON_PASSWORD = "CHANGE_ME_COMMON_PASSWORD"

# Конфигурация Bitrix24
# Вариант с входящим вебхуком:
# Пример: https://my-domain.bitrix24.ru/rest/1/xxxxxxxxxx/
BITRIX_WEBHOOK_BASE_URL = "https://your-bitrix-domain/rest/1/WEBHOOK_CODE/"

# Часовой пояс, можно использовать в будущем
TIMEZONE = "Europe/Moscow"
