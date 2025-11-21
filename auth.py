"""
Модуль авторизации пользователей бота.

Логика:
- У каждого сотрудника есть логин.
- Пароль один общий (хранится в config.COMMON_PASSWORD).
- По логину определяем bitrix_user_id и ФИО.
- Связку telegram_user_id <-> bitrix_user_id храним в SQLite.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict

from config import COMMON_PASSWORD

DB_PATH = Path(__file__).resolve().parent / "bot_data.sqlite3"

# ВНИМАНИЕ: заполните маппинг логинов под ваших сотрудников.
# Ключ: логин, Значение: словарь с bitrix_user_id и именем.
LOGIN_MAP = {
    # Примеры:
    # "ivan": {"bitrix_user_id": 1, "name": "Иван Иванов"},
    # "petr": {"bitrix_user_id": 2, "name": "Петр Петров"},
}


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_user_id INTEGER PRIMARY KEY,
            login TEXT NOT NULL,
            bitrix_user_id INTEGER NOT NULL,
            name TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def validate_credentials(login: str, password: str) -> Optional[Dict]:
    """
    Проверка логина/пароля.
    Возвращает словарь с данными пользователя при успехе или None.
    """
    login = login.strip().lower()
    if password != COMMON_PASSWORD:
        return None
    user_info = LOGIN_MAP.get(login)
    if not user_info:
        return None
    return {
        "login": login,
        "bitrix_user_id": user_info["bitrix_user_id"],
        "name": user_info.get("name") or login,
    }


def bind_telegram_user(telegram_user_id: int, login: str, bitrix_user_id: int, name: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (telegram_user_id, login, bitrix_user_id, name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(telegram_user_id) DO UPDATE SET
            login = excluded.login,
            bitrix_user_id = excluded.bitrix_user_id,
            name = excluded.name
        """,
        (telegram_user_id, login, bitrix_user_id, name),
    )
    conn.commit()
    conn.close()


def get_bound_user(telegram_user_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT login, bitrix_user_id, name FROM users WHERE telegram_user_id = ?",
        (telegram_user_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    login, bitrix_user_id, name = row
    return {
        "login": login,
        "bitrix_user_id": bitrix_user_id,
        "name": name,
    }


def unbind_telegram_user(telegram_user_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE telegram_user_id = ?", (telegram_user_id,))
    conn.commit()
    conn.close()
