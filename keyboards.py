"""
Клавиатуры (Reply и Inline) для бота.
"""

from typing import List, Dict
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton("Задачи"), KeyboardButton("Календарь")],
        [KeyboardButton("Мой профиль")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def tasks_menu_inline() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("Мои задачи", callback_data="tasks:list"),
            InlineKeyboardButton("Создать задачу", callback_data="tasks:create"),
        ],
        [
            InlineKeyboardButton("Изменить фильтр", callback_data="tasks:filter"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def calendar_menu_inline() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("Мои мероприятия", callback_data="calendar:list"),
            InlineKeyboardButton("Создать мероприятие", callback_data="calendar:create"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def tasks_pagination_inline(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    if has_prev:
        row.append(InlineKeyboardButton("◀️ Назад", callback_data=f"tasks:page:{page-1}"))
    if has_next:
        row.append(InlineKeyboardButton("▶️ Далее", callback_data=f"tasks:page:{page+1}"))
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Изменить фильтр", callback_data="tasks:filter")])
    return InlineKeyboardMarkup(buttons)


def employees_keyboard(employees: List[Dict], page: int, page_size: int, prefix: str) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора сотрудника/участника.
    prefix - префикс callback_data, например 'task_resp' или 'event_attendee'.
    """
    start = page * page_size
    end = start + page_size
    items = employees[start:end]
    rows = []
    for emp in items:
        label = emp.get("FULL_NAME") or f"{emp.get('NAME', '')} {emp.get('LAST_NAME', '')}".strip()
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"{prefix}:select:{emp['ID']}")]
        )

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"{prefix}:page:{page-1}"))
    if end < len(employees):
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"{prefix}:page:{page+1}"))
    if nav_row:
        rows.append(nav_row)

    return InlineKeyboardMarkup(rows)
