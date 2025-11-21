from enum import IntEnum
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from auth import get_bound_user
from bitrix_api import get_calendar_events, get_employees, create_calendar_event
from keyboards import employees_keyboard


class CalendarCreateStates(IntEnum):
    TITLE = 1
    DESCRIPTION = 2
    DATE = 3
    ATTENDEES = 4
    CONFIRM = 5


EMPLOYEES_PAGE_SIZE = 10


def _ensure_authorized(update: Update) -> Dict:
    user = update.effective_user
    bound = get_bound_user(user.id)
    return bound


async def handle_calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    bound = _ensure_authorized(update)
    if not bound:
        await query.edit_message_text(
            "Вы не авторизованы. Используйте /login для входа."
        )
        return

    if data == "calendar:list":
        await _show_events(query, context, page=0)
    elif data == "calendar:create":
        await _create_event_start(query, context)


async def _show_events(query, context, page: int):
    bound = _ensure_authorized(query)
    if not bound:
        await query.edit_message_text(
            "Вы не авторизованы. Используйте /login для входа."
        )
        return

    events = get_calendar_events(bound["bitrix_user_id"], limit=10)
    if not events:
        await query.edit_message_text("Ближайших мероприятий не найдено.")
        return

    # Простая реализация без постраничного вывода, так как Bitrix календарь
    # требует доработки под ваш кейс.
    lines = ["Ближайшие мероприятия:"]
    for ev in events:
        name = ev.get("NAME") or ev.get("TITLE") or "(без названия)"
        date = ev.get("DATE_FROM") or ev.get("DATE") or ""
        lines.append(f"- {name} ({date})")

    await query.edit_message_text("\n".join(lines))


# ======== Создание мероприятия (диалог) ========

async def _create_event_start(query, context) -> int:
    await query.edit_message_text("Создание мероприятия. Введите название:")
    return CalendarCreateStates.TITLE


async def calendar_create_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["calendar_create"] = {
        "title": update.message.text.strip(),
    }
    await update.message.reply_text("Введите описание мероприятия (или '-' если без описания):")
    return CalendarCreateStates.DESCRIPTION


async def calendar_create_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    desc = update.message.text.strip()
    if desc == "-":
        desc = ""
    context.user_data["calendar_create"]["description"] = desc
    await update.message.reply_text("Введите дату мероприятия в формате dd.mm.yyyy:")
    return CalendarCreateStates.DATE


def _parse_date_ddmmyyyy(value: str):
    from datetime import datetime
    try:
        return datetime.strptime(value, "%d.%m.%Y")
    except ValueError:
        return None


async def calendar_create_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    dt = _parse_date_ddmmyyyy(text)
    if not dt:
        await update.message.reply_text(
            "Дата в неправильном формате. Введите в виде dd.mm.yyyy, например 25.12.2025:"
        )
        return CalendarCreateStates.DATE

    # Сохраним ISO дату YYYY-MM-DD
    date_iso = dt.date().isoformat()
    context.user_data["calendar_create"]["date_iso"] = date_iso

    employees = get_employees()
    context.user_data["employees_cache"] = employees
    context.user_data["employees_page"] = 0
    context.user_data["attendees_selected"] = set()

    if not employees:
        await update.message.reply_text(
            "Не удалось получить список сотрудников из Bitrix24. Обратитесь к администратору."
        )
        return ConversationHandler.END

    kb = _attendees_keyboard(employees, context, prefix="event_att")
    await update.message.reply_text(
        "Выберите участников (нажимайте на кнопки). Когда закончите, нажмите 'Готово'.",
        reply_markup=kb,
    )
    return CalendarCreateStates.ATTENDEES


def _attendees_keyboard(employees: List[Dict], context, prefix: str) -> InlineKeyboardMarkup:
    page = context.user_data.get("employees_page", 0)
    from keyboards import employees_keyboard as base_emp_keyboard

    kb = base_emp_keyboard(employees, page=page, page_size=EMPLOYEES_PAGE_SIZE, prefix=prefix)

    # Добавим кнопки "Готово" и "Отмена"
    rows = kb.inline_keyboard.copy()
    rows.append(
        [
            InlineKeyboardButton("Готово", callback_data=f"{prefix}:done"),
            InlineKeyboardButton("Отмена", callback_data=f"{prefix}:cancel"),
        ]
    )
    return InlineKeyboardMarkup(rows)


async def calendar_attendees_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    employees: List[Dict] = context.user_data.get("employees_cache", [])
    page = context.user_data.get("employees_page", 0)
    selected = context.user_data.get("attendees_selected", set())

    if data.startswith("event_att:page:"):
        page = int(data.split(":")[-1])
        context.user_data["employees_page"] = page
        kb = _attendees_keyboard(employees, context, prefix="event_att")
        await query.edit_message_text(
            "Выберите участников (нажимайте на кнопки). Когда закончите, нажмите 'Готово'.",
            reply_markup=kb,
        )
        return CalendarCreateStates.ATTENDEES

    if data.startswith("event_att:select:"):
        emp_id = int(data.split(":")[-1])
        if emp_id in selected:
            selected.remove(emp_id)
        else:
            selected.add(emp_id)
        context.user_data["attendees_selected"] = selected
        kb = _attendees_keyboard(employees, context, prefix="event_att")
        await query.edit_message_text(
            "Выберите участников (нажимайте на кнопки). Когда закончите, нажмите 'Готово'.",
            reply_markup=kb,
        )
        return CalendarCreateStates.ATTENDEES

    if data == "event_att:cancel":
        await query.edit_message_text("Создание мероприятия отменено.")
        return ConversationHandler.END

    if data == "event_att:done":
        # Переход к подтверждению
        payload = context.user_data.get("calendar_create", {})
        title = payload.get("title", "")
        description = payload.get("description", "")
        date_iso = payload.get("date_iso", "")
        attendees_ids = list(selected)

        payload["attendees_ids"] = attendees_ids
        context.user_data["calendar_create"] = payload

        # Формируем текст подтверждения
        lines = [
            "Проверьте данные мероприятия:",
            f"Название: {title}",
            f"Описание: {description or '(нет)'}",
            f"Дата: {date_iso}",
            f"Количество участников: {len(attendees_ids)}",
            "",
            "Создать мероприятие?",
        ]
        buttons = [
            [
                InlineKeyboardButton("Создать", callback_data="event_create:confirm"),
                InlineKeyboardButton("Отмена", callback_data="event_create:cancel"),
            ]
        ]
        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return CalendarCreateStates.CONFIRM

    return CalendarCreateStates.ATTENDEES


async def calendar_create_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "event_create:cancel":
        await query.edit_message_text("Создание мероприятия отменено.")
        return ConversationHandler.END

    if data == "event_create:confirm":
        bound = _ensure_authorized(update)
        if not bound:
            await query.edit_message_text(
                "Вы не авторизованы. Используйте /login для входа."
            )
            return ConversationHandler.END

        payload = context.user_data.get("calendar_create", {})
        try:
            event_id = create_calendar_event(
                owner_id=bound["bitrix_user_id"],
                name=payload.get("title", ""),
                description=payload.get("description", ""),
                date_iso=payload.get("date_iso", ""),
                attendees_ids=payload.get("attendees_ids", []),
            )
        except Exception as e:
            await query.edit_message_text(
                f"Ошибка при создании мероприятия: {e}"
            )
            return ConversationHandler.END

        await query.edit_message_text(
            f"Мероприятие создано (ID: {event_id})."
        )
        return ConversationHandler.END

    return ConversationHandler.END


async def calendar_create_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Создание мероприятия отменено.")
    return ConversationHandler.END
