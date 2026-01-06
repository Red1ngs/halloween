import logging
from typing import Any, Dict, Optional

import requests

from utils.settings import TAKE_CANDY_PATH, ADD_HISTORY_PATH
from utils.network_utils import make_request

def take_candy(session: requests.Session, base_url: str, candy_token: str) -> Optional[Dict[str, Any]]:
    """
    Виконує запит для отримання цукерки, використовуючи наданий токен.
    """
    url = f"{base_url}{TAKE_CANDY_PATH}?r=776"
    payload = {"token": candy_token}
    logging.info(f"Намагаюся взяти цукерку з токеном: {candy_token}")

    result = make_request(
        session, 
        'POST', 
        url, 
        delay=3.0,
        data=payload, 
        headers_profile="ajax_post"
    )
    return result if isinstance(result, dict) else None

def process_single_batch(
    session: requests.Session, 
    base_url: str, 
    chapters_batch: list[dict[str, Any]], 
    delay: float = 180.0  # <--- ДОДАНО АРГУМЕНТ ТУТ
) -> Dict[str, int]:
    """
    Обробляє одну порцію глав: відправляє історію.
    Приймає динамічний delay.
    Повертає словник: {'candies': int, 'cards': int}
    """
    url = f"{base_url}{ADD_HISTORY_PATH}"
    
    payload: dict[str, Any] = {}
    for i, item in enumerate(chapters_batch):
        for key, value in item.items():
            payload[f"items[{i}][{key}]"] = value
    
    # Виконуємо запит з переданим delay
    history_response = make_request(
        session, 
        'POST', 
        url, 
        delay=delay,  # <--- ПЕРЕДАЄМО ЙОГО В ЗАПИТ
        data=payload, 
        headers_profile="ajax_post"
    )
    
    result = {'candies': 0, 'cards': 0}

    if not history_response or not isinstance(history_response, dict):
        logging.error("Не отримано валідної відповіді від сервера /addHistory.")
        return result

    # 1. Перевірка на ЦУКЕРКУ
    candy_token = history_response.get("token")
    if candy_token:
        # Забираємо цукерку
        take_candy(session, base_url, candy_token)
        
        candy_type = history_response.get("type")
        if candy_type == "pumpkin":
            result['candies'] = 3
            logging.info(f"✅ УСПІХ! Знайдено гарбуз! +3.")
        else:
            result['candies'] = 1
            logging.info(f"✅ УСПІХ! Взято нову цукерку. +1.")
            
        return result

    # 2. Перевірка на КАРТКУ
    # Перевіряємо наявність ID та Name, щоб точно знати, що це картка
    if 'id' in history_response and 'name' in history_response:
        card_name = history_response.get('name')
        logging.info(f"🃏 ЗНАЙДЕНО КАРТКУ: '{card_name}' (ID: {history_response.get('id')})")
        result['cards'] = 1
        return result

    return result
