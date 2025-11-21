from telegram import Update
from telegram.ext import ContextTypes

from auth import get_bound_user
from keyboards import main_menu_keyboard, tasks_menu_inline, calendar_menu_inline


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    bound = get_bound_user(user.id)
    if bound:
        text = (
            f"Здравствуйте, {bound['name']}!\n"
            "Вы авторизованы. Выберите раздел:"
        )
    else:
        text = (
            "Здравствуйте! Это бот для работы с задачами и календарем Битрикс24.\n"
            "Вы пока не авторизованы. Для входа используйте команду /login.\n\n"
            "После авторизации вы увидите свои задачи и мероприятия."
        )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard())


async def show_tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Раздел Задачи. Выберите действие:",
            reply_markup=tasks_menu_inline(),
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "Раздел Задачи. Выберите действие:",
            reply_markup=tasks_menu_inline(),
        )


async def show_calendar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Раздел Календарь. Выберите действие:",
            reply_markup=calendar_menu_inline(),
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "Раздел Календарь. Выберите действие:",
            reply_markup=calendar_menu_inline(),
        )


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    bound = get_bound_user(user.id)
    if not bound:
        await update.message.reply_text(
            "Вы не авторизованы. Используйте команду /login для входа."
        )
        return
    text = (
        f"Вы авторизованы как: {bound['name']}\n"
        f"Логин: {bound['login']}\n"
        "\n"
        "Чтобы выйти, используйте команду /logout."
    )
    await update.message.reply_text(text)
