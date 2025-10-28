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

def process_single_batch(session: requests.Session, base_url: str, chapters_batch: list[dict[str, Any]]) -> int:
    """
    Обробляє одну порцію глав: відправляє історію, отримує і збирає цукерку.
    Повертає кількість зібраних цукерок (0, 1 або 3).
    """
    url = f"{base_url}{ADD_HISTORY_PATH}"
    
    payload = {}
    for i, item in enumerate(chapters_batch):
        for key, value in item.items():
            payload[f"items[{i}][{key}]"] = value
    
    history_response = make_request(
        session, 
        'POST', 
        url, 
        delay=180.0,
        data=payload, 
        headers_profile="ajax_post"
    )
    
    if not history_response or not isinstance(history_response, dict):
        logging.error("Не отримано валідної відповіді від сервера /addHistory.")
        return 0

    candy_token = history_response.get("token")
    if not candy_token:
        logging.info(f"Кенді-токен не знайдено у відповіді: {history_response}")
        return 0

    take_candy(session, base_url, candy_token)
        
    candy_type = history_response.get("type")
    candies_collected = 0
    if candy_type == "pumpkin":
        candies_collected = 3
        logging.info(f"✅ УСПІХ! Знайдено гарбуз! +{candies_collected} цукерки.")
    elif candy_type == "candy":
        candies_collected = 1
        logging.info(f"✅ УСПІХ! Взято нову цукерку. +{candies_collected} цукерка.")

    return candies_collected