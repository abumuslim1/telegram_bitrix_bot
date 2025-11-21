"""
Обертка над REST API Bitrix24.

Здесь описаны функции:
- get_tasks(...)
- create_task(...)
- get_calendar_events(...)
- create_calendar_event(...)
- get_employees(...)

Часть методов (особенно календарь) нужно будет адаптировать под ваш портал.
"""

from typing import List, Dict, Optional, Any
import requests

from config import BITRIX_WEBHOOK_BASE_URL


class BitrixAPIError(Exception):
    pass


def _call(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = BITRIX_WEBHOOK_BASE_URL.rstrip("/") + "/" + method
    response = requests.post(url, json=params or {})
    if response.status_code != 200:
        raise BitrixAPIError(f"HTTP {response.status_code}: {response.text}")
    data = response.json()
    if isinstance(data, dict) and "error" in data:
        raise BitrixAPIError(f"{data['error']}: {data.get('error_description')}")
    return data


# ======== Сотрудники ========

def get_employees() -> List[Dict]:
    """
    Получение списка сотрудников.
    Можно кешировать на стороне бота.
    Возвращаем список словарей:
    { 'ID': int, 'NAME': str, 'LAST_NAME': str, 'FULL_NAME': str }
    """
    data = _call("user.get", {})
    result = data.get("result", [])
    employees: List[Dict] = []
    if isinstance(result, list):
        for item in result:
            full_name = (item.get("NAME", "") + " " + item.get("LAST_NAME", "")).strip()
            employees.append(
                {
                    "ID": int(item["ID"]),
                    "NAME": item.get("NAME", ""),
                    "LAST_NAME": item.get("LAST_NAME", ""),
                    "FULL_NAME": full_name or item.get("LOGIN", ""),
                }
            )
    return employees


# ======== Задачи ========

def get_tasks(bitrix_user_id: int, role: str, status: str, start: int = 0, limit: int = 5) -> Dict:
    """
    Получение задач по пользователю с фильтрацией и простейшей пагинацией по offset.

    role: 'do', 'assist', 'originator', 'observer'
    status: 'active', 'completed', 'all'
    Возвращает:
    {
      'tasks': [ {...}, ... ],
      'total': int,
      'next': Optional[int]
    }
    """
    filter_: Dict[str, Any] = {}

    # Роль
    if role == "do":          # Делаю
        filter_["RESPONSIBLE_ID"] = bitrix_user_id
    elif role == "assist":    # Помогаю (соисполнитель)
        filter_["ACCOMPLICE"] = bitrix_user_id
    elif role == "originator":  # Поручил (постановщик)
        filter_["CREATED_BY"] = bitrix_user_id
    elif role == "observer":  # Наблюдаю
        filter_["AUDITOR"] = bitrix_user_id

    # Статус
    # Набор статусов примерный, при необходимости поправьте под свои статусы.
    if status == "active":
        filter_["STATUS"] = [1, 2, 3, 4]
    elif status == "completed":
        filter_["STATUS"] = [5, 6]

    params = {
        "filter": filter_,
        "select": ["ID", "TITLE", "DESCRIPTION", "RESPONSIBLE_ID", "CREATED_BY", "DEADLINE", "STATUS"],
        "start": start,
    }
    data = _call("tasks.task.list", params)

    tasks: List[Dict] = []
    next_: Optional[int] = None

    # Bitrix может вернуть разные структуры, постараемся отработать все варианты.
    result = data.get("result")
    if isinstance(result, dict):
        # Новый формат: {"result": {"tasks": [...], "next": ..., ...}}
        tasks = result.get("tasks", []) or []
        next_ = result.get("next")
    elif isinstance(result, list):
        # Старый формат: {"result": [ {...}, {...} ], "next": ...}
        tasks = result
        next_ = data.get("next")
    else:
        # На всякий случай
        tasks = data.get("tasks", []) or []
        next_ = data.get("next")

    return {
        "tasks": tasks,
        "total": len(tasks),
        "next": next_,
    }


def create_task(
    title: str,
    description: str,
    deadline_iso: Optional[str],
    responsible_id: int,
    created_by: Optional[int] = None,
) -> int:
    """
    Создание задачи.
    deadline_iso в формате 'YYYY-MM-DDTHH:MM:SS' или None.
    Возвращает ID созданной задачи.
    """
    fields: Dict[str, Any] = {
        "TITLE": title,
        "DESCRIPTION": description,
        "RESPONSIBLE_ID": responsible_id,
    }
    if deadline_iso:
        fields["DEADLINE"] = deadline_iso
    if created_by:
        fields["CREATED_BY"] = created_by

    data = _call("tasks.task.add", {"fields": fields})
    # В разных версиях структура тоже может отличаться
    res = data.get("result", {})
    if isinstance(res, dict) and "task" in res:
        task_id = res["task"].get("id")
    else:
        task_id = res.get("task_id") or res.get("ID")

    if not task_id:
        raise BitrixAPIError("Не удалось получить ID созданной задачи")
    return int(task_id)


# ======== Календарь ========

def get_calendar_events(bitrix_user_id: int, limit: int = 10) -> List[Dict]:
    """
    Получение ближайших событий календаря пользователя.

    ЭТУ ФУНКЦИЮ НУЖНО ДОРАБОТАТЬ под ваш портал:
    - Можно использовать метод calendar.event.get или calendar.events.list и т.п.
    - Сейчас возвращается пустой список, поэтому бот честно пишет:
      "Ближайших мероприятий не найдено."
    """
    # TODO: реализовать конкретный вызов API календаря Bitrix24.
    return []


def create_calendar_event(
    owner_id: int,
    name: str,
    description: str,
    date_iso: str,
    attendees_ids: Optional[List[int]] = None,
) -> Optional[int]:
    """
    Создание события календаря.

    ВАЖНО: эту функцию тоже нужно будет адаптировать под ваш метод Bitrix24.
    Сейчас это заглушка, чтобы бот не падал.
    """
    # Пример структуры полей (КОММЕНТАРИЙ, НЕ РАБОТАЕТ БЕЗ РЕАЛЬНОГО МЕТОДА):
    #
    # fields = {
    #     "NAME": name,
    #     "DESCRIPTION": description,
    #     "DATE_FROM": date_iso + " 09:00:00",
    #     "DATE_TO": date_iso + " 10:00:00",
    #     "OWNER_ID": owner_id,
    #     "ATTENDEES": attendees_ids or [],
    # }
    # data = _call("calendar.event.add", {"fields": fields})
    # return data.get("result")
    return None
