"""
Обертка над REST API Bitrix24.

Здесь описаны функции:
- get_tasks(...)
- create_task(...)
- get_calendar_events(...)
- create_calendar_event(...)
- get_employees(...)

ВАЖНО:
- Реализация зависит от вашей схемы авторизации в Bitrix24.
- Здесь приведен пример для входящего вебхука.
"""

from typing import List, Dict, Optional
import requests

from config import BITRIX_WEBHOOK_BASE_URL


class BitrixAPIError(Exception):
    pass


def _call(method: str, params: Optional[Dict] = None) -> Dict:
    url = BITRIX_WEBHOOK_BASE_URL.rstrip("/") + "/" + method
    response = requests.post(url, json=params or {})
    if response.status_code != 200:
        raise BitrixAPIError(f"HTTP {response.status_code}: {response.text}")
    data = response.json()
    if "error" in data:
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
    # Пример для метода user.get (проверьте доступность)
    data = _call("user.get", {})
    result = []
    for item in data.get("result", []):
        full_name = item.get("NAME", "") + " " + item.get("LAST_NAME", "")
        result.append(
            {
                "ID": int(item["ID"]),
                "NAME": item.get("NAME", ""),
                "LAST_NAME": item.get("LAST_NAME", ""),
                "FULL_NAME": full_name.strip() or item.get("LOGIN", ""),
            }
        )
    return result


# ======== Задачи ========

def get_tasks(bitrix_user_id: int, role: str, status: str, start: int = 0, limit: int = 5) -> Dict:
    """
    Получение задач по пользователю с фильтрацией и пагинацией.
    role: 'do', 'assist', 'originator', 'observer'
    status: 'active', 'completed', 'all'
    Возвращает:
    {
      'tasks': [ {...}, ... ],
      'total': int
    }
    """
    # Пример фильтра, нужно адаптировать под ваши поля и требования.
    filter_ = {}
    # Фильтр по роли:
    if role == "do":          # Делаю
        filter_["RESPONSIBLE_ID"] = bitrix_user_id
    elif role == "assist":    # Помогаю (соисполнитель)
        filter_["ACCOMPLICE"] = bitrix_user_id
    elif role == "originator":  # Поручил (постановщик)
        filter_["CREATED_BY"] = bitrix_user_id
    elif role == "observer":  # Наблюдаю
        filter_["AUDITOR"] = bitrix_user_id

    # Фильтр по статусу:
    # В Bitrix24 свои статусы (1 - новая, 2 - ждет выполнения и т.д.).
    if status == "active":
        filter_["STATUS"] = [1, 2, 3, 4]  # пример
    elif status == "completed":
        filter_["STATUS"] = [5, 6]        # пример

    params = {
        "filter": filter_,
        "select": ["ID", "TITLE", "DESCRIPTION", "RESPONSIBLE_ID", "CREATED_BY", "DEADLINE", "STATUS"],
        "start": start,
    }
    data = _call("tasks.task.list", params)
    result = data.get("result", {})
    tasks = result.get("tasks", [])
    next_ = result.get("next", None)
    total = len(tasks)
    return {
        "tasks": tasks,
        "total": total,
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
    fields = {
        "TITLE": title,
        "DESCRIPTION": description,
        "RESPONSIBLE_ID": responsible_id,
    }
    if deadline_iso:
        fields["DEADLINE"] = deadline_iso
    if created_by:
        fields["CREATED_BY"] = created_by

    data = _call("tasks.task.add", {"fields": fields})
    task_id = data.get("result", {}).get("task", {}).get("id")
    if not task_id:
        raise BitrixAPIError("Не удалось получить ID созданной задачи")
    return int(task_id)


# ======== Календарь ========

def get_calendar_events(bitrix_user_id: int, limit: int = 10) -> List[Dict]:
    """
    Получение ближайших событий календаря пользователя.
    В Bitrix24 есть несколько вариантов API для календаря.
    Здесь нужно адаптировать под ваш метод (calendar.event.get или др.).
    """
    # TODO: адаптируйте под ваш конкретный метод календаря.
    # Заглушка: возвращаем пустой список.
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
    date_iso в формате 'YYYY-MM-DD'.
    """
    # TODO: реализовать вызов нужного метода календаря Bitrix24.
    # Пример структуры полей (нужно адаптировать):
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
