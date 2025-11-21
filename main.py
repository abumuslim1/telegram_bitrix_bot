import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from auth import init_db, get_bound_user
from handlers.start import start, show_tasks_menu, show_calendar_menu, show_profile
from handlers.auth_handler import (
    login_start,
    login_login,
    login_password,
    login_cancel,
    logout,
    AuthStates,
)
from handlers.tasks import (
    handle_tasks_callback,
    handle_tasks_filter_submenus,
    create_task_start,
    task_create_title,
    task_create_description,
    task_create_deadline,
    task_create_responsible_callback,
    task_create_confirm_callback,
    task_create_cancel,
    TaskCreateStates,
)
from handlers.calendar_handler import (
    calendar_list_callback,
    calendar_create_entry,
    calendar_create_title,
    calendar_create_description,
    calendar_create_date,
    calendar_attendees_callback,
    calendar_create_confirm_callback,
    calendar_create_cancel,
    CalendarCreateStates,
)
from keyboards import main_menu_keyboard


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def text_router(update, context):
    """Обработчик текстовых сообщений с главного меню."""
    if not update.message:
        return
    text = update.message.text.strip()

    if text == "Задачи":
        if not get_bound_user(update.effective_user.id):
            await update.message.reply_text(
                "Вы не авторизованы. Используйте /login для входа."
            )
            return
        await show_tasks_menu(update, context)
    elif text == "Календарь":
        if not get_bound_user(update.effective_user.id):
            await update.message.reply_text(
                "Вы не авторизованы. Используйте /login для входа."
            )
            return
        await show_calendar_menu(update, context)
    elif text == "Мой профиль":
        await show_profile(update, context)
    else:
        await update.message.reply_text(
            "Я вас не понял. Используйте кнопки меню или команды /start, /login.",
            reply_markup=main_menu_keyboard(),
        )


def main():
    init_db()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # /start
    application.add_handler(CommandHandler("start", start))

    # Авторизация /login
    login_conv = ConversationHandler(
        entry_points=[CommandHandler("login", login_start)],
        states={
            AuthStates.LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_login)],
            AuthStates.PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler("cancel", login_cancel)],
    )
    application.add_handler(login_conv)
    application.add_handler(CommandHandler("logout", logout))

    # Создание задач (диалог)
    task_create_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_task_start, pattern="^tasks:create$")
        ],
        states={
            TaskCreateStates.TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_create_title)],
            TaskCreateStates.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_create_description)],
            TaskCreateStates.DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_create_deadline)],
            TaskCreateStates.RESPONSIBLE_SELECT: [
                CallbackQueryHandler(task_create_responsible_callback, pattern="^task_resp:")
            ],
            TaskCreateStates.CONFIRM: [
                CallbackQueryHandler(task_create_confirm_callback, pattern="^task_create:")
            ],
        },
        fallbacks=[CommandHandler("cancel", task_create_cancel)],
    )
    application.add_handler(task_create_conv)

    # Создание мероприятий (диалог)
    calendar_create_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(calendar_create_entry, pattern="^calendar:create$")
        ],
        states={
            CalendarCreateStates.TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_create_title)],
            CalendarCreateStates.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_create_description)],
            CalendarCreateStates.DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_create_date)],
            CalendarCreateStates.ATTENDEES: [
                CallbackQueryHandler(calendar_attendees_callback, pattern="^event_att:")
            ],
            CalendarCreateStates.CONFIRM: [
                CallbackQueryHandler(calendar_create_confirm_callback, pattern="^event_create:")
            ],
        },
        fallbacks=[CommandHandler("cancel", calendar_create_cancel)],
    )
    application.add_handler(calendar_create_conv)

    # Callback'и задач: список/фильтр
    application.add_handler(CallbackQueryHandler(handle_tasks_callback, pattern=r"^tasks:(list|page:.*|filter$|filter:role:.*|filter:status:.*)$"))
    application.add_handler(CallbackQueryHandler(handle_tasks_filter_submenus, pattern=r"^tasks:filter_(role_menu|status_menu)$"))

    # Callback'и календаря: список мероприятий
    application.add_handler(CallbackQueryHandler(calendar_list_callback, pattern=r"^calendar:list$"))

    # Текстовые сообщения (главное меню)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    application.run_polling()


if __name__ == "__main__":
    main()
