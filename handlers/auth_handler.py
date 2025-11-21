from enum import IntEnum

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from auth import validate_credentials, bind_telegram_user, unbind_telegram_user


class AuthStates(IntEnum):
    LOGIN = 1
    PASSWORD = 2


async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ваш логин:")
    return AuthStates.LOGIN


async def login_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    login = update.message.text.strip()
    context.user_data["login_attempt"] = login
    await update.message.reply_text("Введите общий пароль:")
    return AuthStates.PASSWORD


async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text.strip()
    login = context.user_data.get("login_attempt")

    user_info = validate_credentials(login, password)
    if not user_info:
        await update.message.reply_text(
            "Неверный логин или пароль. Попробуйте ещё раз с /login."
        )
        return ConversationHandler.END

    bind_telegram_user(
        telegram_user_id=update.effective_user.id,
        login=user_info["login"],
        bitrix_user_id=user_info["bitrix_user_id"],
        name=user_info["name"],
    )
    await update.message.reply_text(
        f"Успешный вход. Вы авторизованы как: {user_info['name']}."
    )
    return ConversationHandler.END


async def login_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Авторизация отменена.")
    return ConversationHandler.END


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    unbind_telegram_user(update.effective_user.id)
    await update.message.reply_text(
        "Вы вышли из аккаунта. Для повторного входа используйте /login."
    )
