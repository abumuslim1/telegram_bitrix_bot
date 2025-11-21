from enum import IntEnum
from typing import List, Dict

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from auth import get_bound_user
from bitrix_api import get_tasks, get_employees, create_task
from keyboards import tasks_pagination_inline, employees_keyboard


class TaskCreateStates(IntEnum):
    TITLE = 1
    DESCRIPTION = 2
    DEADLINE = 3
    RESPONSIBLE_SELECT = 4
    CONFIRM = 5


TASKS_PAGE_SIZE = 5
EMPLOYEES_PAGE_SIZE = 10


def _ensure_authorized(update: Update) -> Dict:
    user = update.effective_user
    bound = get_bound_user(user.id)
    return bound


async def handle_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback'ов из меню задач."""
    query = update.callback_query
    await query.answer()
    data = query.data

    bound = _ensure_authorized(update)
    if not bound:
        await query.edit_message_text(
            "Вы не авторизованы. Используйте /login для входа."
        )
        return

    if data == "tasks:list":
        # сбросим пагинацию и фильтры по умолчанию
        context.user_data.setdefault("tasks_filter", {})
        context.user_data["tasks_filter"].setdefault("role", "do")       # делаю
        context.user_data["tasks_filter"].setdefault("status", "active") # активные
        await _show_tasks_page(query, context, page=0)
    elif data.startswith("tasks:page:"):
        page = int(data.split(":")[-1])
        await _show_tasks_page(query, context, page=page)
    elif data == "tasks:filter":
        await _show_filter_menu(query, context)
    elif data.startswith("tasks:filter:role:"):
        role_key = data.split(":")[-1]
        context.user_data.setdefault("tasks_filter", {})
        context.user_data["tasks_filter"]["role"] = role_key
        await _show_filter_menu(query, context, message="Роль обновлена.")
    elif data.startswith("tasks:filter:status:"):
        status_key = data.split(":")[-1]
        context.user_data.setdefault("tasks_filter", {})
        context.user_data["tasks_filter"]["status"] = status_key
        await _show_filter_menu(query, context, message="Статус обновлен.")


async def _show_filter_menu(query, context, message: str = ""):
    filt = context.user_data.get("tasks_filter", {"role": "do", "status": "active"})
    role = filt.get("role", "do")
    status = filt.get("status", "active")

    text_lines = []
    if message:
        text_lines.append(message)
    text_lines.append("Текущий фильтр задач:")
    role_map = {
        "do": "Делаю",
        "assist": "Помогаю",
        "originator": "Поручил",
        "observer": "Наблюдаю",
    }
    status_map = {
        "active": "Активные",
        "completed": "Завершенные",
        "all": "Все",
    }
    text_lines.append(f"Роль: {role_map.get(role, role)}")
    text_lines.append(f"Статус: {status_map.get(status, status)}")
    text_lines.append("")
    text_lines.append("Выберите, что изменить:")

    buttons = [
        [
            InlineKeyboardButton("Роль", callback_data="tasks:filter_role_menu"),
            InlineKeyboardButton("Статус", callback_data="tasks:filter_status_menu"),
        ],
        [
            InlineKeyboardButton("Показать задачи", callback_data="tasks:list"),
        ],
    ]

    await query.edit_message_text(
        "\n".join(text_lines),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_tasks_filter_submenus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    filt = context.user_data.get("tasks_filter", {"role": "do", "status": "active"})

    if data == "tasks:filter_role_menu":
        role = filt.get("role", "do")
        text = "Выберите роль:"
        buttons = [
            [InlineKeyboardButton(("✅ " if role == "do" else "") + "Делаю", callback_data="tasks:filter:role:do")],
            [InlineKeyboardButton(("✅ " if role == "assist" else "") + "Помогаю", callback_data="tasks:filter:role:assist")],
            [InlineKeyboardButton(("✅ " if role == "originator" else "") + "Поручил", callback_data="tasks:filter:role:originator")],
            [InlineKeyboardButton(("✅ " if role == "observer" else "") + "Наблюдаю", callback_data="tasks:filter:role:observer")],
            [InlineKeyboardButton("Назад", callback_data="tasks:filter")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data == "tasks:filter_status_menu":
        status = filt.get("status", "active")
        text = "Выберите статус:"
        buttons = [
            [InlineKeyboardButton(("✅ " if status == "active" else "") + "Активные", callback_data="tasks:filter:status:active")],
            [InlineKeyboardButton(("✅ " if status == "completed" else "") + "Завершенные", callback_data="tasks:filter:status:completed")],
            [InlineKeyboardButton(("✅ " if status == "all" else "") + "Все", callback_data="tasks:filter:status:all")],
            [InlineKeyboardButton("Назад", callback_data="tasks:filter")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def _show_tasks_page(query, context, page: int):
    bound = _ensure_authorized(query)
    if not bound:
        await query.edit_message_text(
            "Вы не авторизованы. Используйте /login для входа."
        )
        return

    filt = context.user_data.get("tasks_filter", {"role": "do", "status": "active"})
    role = filt.get("role", "do")
    status = filt.get("status", "active")

    start = page * TASKS_PAGE_SIZE
    data = get_tasks(
        bitrix_user_id=bound["bitrix_user_id"],
        role=role,
        status=status,
        start=start,
        limit=TASKS_PAGE_SIZE,
    )
    tasks = data.get("tasks", [])
    if not tasks:
        await query.edit_message_text("По выбранному фильтру задач не найдено.")
        return

    lines = ["Список задач:"]
    for t in tasks:
        deadline = t.get("deadline") or t.get("DEADLINE") or ""
        if deadline:
            # Обрезаем до даты
            date_part = deadline.split("T")[0] if "T" in deadline else deadline
        else:
            date_part = "-"
        lines.append(f"#{t.get('id') or t.get('ID')} - {t.get('title') or t.get('TITLE')} (до {date_part})")

    # Проверяем есть ли следующая страница (по полю next)
    has_next = bool(data.get("next") is not None)
    has_prev = page > 0

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=tasks_pagination_inline(page, has_prev, has_next),
    )


# ======== Создание задачи (диалог) ========

async def create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    bound = _ensure_authorized(update)
    if not bound:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "Вы не авторизованы. Используйте /login для входа."
        )
        return ConversationHandler.END

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Создание задачи. Введите название:")
    else:
        await update.message.reply_text("Создание задачи. Введите название:")

    return TaskCreateStates.TITLE


async def task_create_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["task_create"] = {
        "title": update.message.text.strip(),
    }
    await update.message.reply_text("Введите описание задачи (или '-' если без описания):")
    return TaskCreateStates.DESCRIPTION


async def task_create_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    desc = update.message.text.strip()
    if desc == "-":
        desc = ""
    context.user_data["task_create"]["description"] = desc
    await update.message.reply_text("Введите крайний срок в формате dd.mm.yyyy (или '-' если без срока):")
    return TaskCreateStates.DEADLINE


def _parse_date_ddmmyyyy(value: str):
    from datetime import datetime
    try:
        return datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        return None


async def task_create_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from datetime import datetime, time

    text = update.message.text.strip()
    if text == "-":
        deadline_iso = None
    else:
        dt = _parse_date_ddmmyyyy(text)
        if not dt:
            await update.message.reply_text(
                "Дата в неправильном формате. Введите в виде dd.mm.yyyy, например 25.12.2025:"
            )
            return TaskCreateStates.DEADLINE
        # Делаем ISO-строку, например до 18:00 этого дня
        dt_full = datetime.combine(dt.date(), time(hour=18, minute=0))
        deadline_iso = dt_full.isoformat()

    context.user_data["task_create"]["deadline_iso"] = deadline_iso

    # Выбор ответственного
    employees = get_employees()
    context.user_data["employees_cache"] = employees
    context.user_data["employees_page"] = 0

    if not employees:
        await update.message.reply_text(
            "Не удалось получить список сотрудников из Bitrix24. Обратитесь к администратору."
        )
        return ConversationHandler.END

    kb = employees_keyboard(employees, page=0, page_size=EMPLOYEES_PAGE_SIZE, prefix="task_resp")
    await update.message.reply_text("Выберите ответственного:", reply_markup=kb)
    return TaskCreateStates.RESPONSIBLE_SELECT


async def task_create_responsible_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    employees: List[Dict] = context.user_data.get("employees_cache", [])
    page = context.user_data.get("employees_page", 0)

    if data.startswith("task_resp:page:"):
        page = int(data.split(":")[-1])
        context.user_data["employees_page"] = page
        kb = employees_keyboard(employees, page=page, page_size=EMPLOYEES_PAGE_SIZE, prefix="task_resp")
        await query.edit_message_text("Выберите ответственного:", reply_markup=kb)
        return TaskCreateStates.RESPONSIBLE_SELECT

    if data.startswith("task_resp:select:"):
        emp_id = int(data.split(":")[-1])
        emp = next((e for e in employees if int(e["ID"]) == emp_id), None)
        if not emp:
            await query.edit_message_text("Ошибка выбора сотрудника. Попробуйте ещё раз.")
            return TaskCreateStates.RESPONSIBLE_SELECT

        context.user_data["task_create"]["responsible_id"] = emp_id
        context.user_data["task_create"]["responsible_name"] = emp.get("FULL_NAME") or (
            (emp.get("NAME", "") + " " + emp.get("LAST_NAME", "")).strip()
        )

        data_ = context.user_data["task_create"]
        summary_lines = [
            "Проверьте данные задачи:",
            f"Название: {data_['title']}",
            f"Описание: {data_['description'] or '(нет)'}",
            f"Крайний срок: {data_['deadline_iso'] or '(без срока)'}",
            f"Ответственный: {data_['responsible_name']}",
            "",
            "Создать задачу?",
        ]
        buttons = [
            [
                InlineKeyboardButton("Создать", callback_data="task_create:confirm"),
                InlineKeyboardButton("Отмена", callback_data="task_create:cancel"),
            ]
        ]
        await query.edit_message_text(
            "\n".join(summary_lines),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return TaskCreateStates.CONFIRM

    return TaskCreateStates.RESPONSIBLE_SELECT


async def task_create_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "task_create:cancel":
        await query.edit_message_text("Создание задачи отменено.")
        return ConversationHandler.END

    if data == "task_create:confirm":
        bound = _ensure_authorized(update)
        if not bound:
            await query.edit_message_text(
                "Вы не авторизованы. Используйте /login для входа."
            )
            return ConversationHandler.END

        payload = context.user_data.get("task_create", {})
        try:
            task_id = create_task(
                title=payload.get("title", ""),
                description=payload.get("description", ""),
                deadline_iso=payload.get("deadline_iso"),
                responsible_id=payload.get("responsible_id"),
                created_by=bound["bitrix_user_id"],
            )
        except Exception as e:
            await query.edit_message_text(
                f"Ошибка при создании задачи: {e}"
            )
            return ConversationHandler.END

        await query.edit_message_text(
            f"Задача успешно создана. ID: {task_id}."
        )
        return ConversationHandler.END

    return ConversationHandler.END


async def task_create_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Создание задачи отменено.")
    return ConversationHandler.END
