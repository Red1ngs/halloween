# type: ignore
import json
import logging
import time
from typing import Any, Dict, Optional, Union

import requests
from bs4 import BeautifulSoup

from utils.settings import BASE_URL

def get_csrf_from_html(session: requests.Session) -> Optional[str]:
    """
    Виконує GET-запит на вказану URL і витягує CSRF-токен з мета-тегу.
    """
    logging.info(f"Намагаюся отримати CSRF-токен з головної сторінки: {BASE_URL}")
    try:
        response = session.get(BASE_URL, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
        if meta_tag:
            return meta_tag.get('content') 
        logging.warning("Мета-тег 'csrf-token' не знайдено на сторінці.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Не вдалося завантажити сторінку для отримання токена: {e}")
        return None


def create_session(config: dict[str, dict[str, Any]], use_cookie: bool = True) -> Optional[requests.Session]:
    """
    Створює, налаштовує сесію та отримує CSRF-токен.

    1. Завантажує конфігурацію.
    2. Встановлює загальні заголовки та кукі.
    3. Робить запит на головну сторінку, щоб отримати CSRF-токен.
    4. Додає знайдений токен у заголовки сесії для всіх майбутніх запитів.

    Returns:
        Налаштований об'єкт сесії або None у разі невдачі.
    """

    session = requests.Session()
    
    session.config = config
    
    headers = config.get("headers")
    cookies = config.get("cookies")
    
    session.headers.update(headers.get("common", {}))
    if use_cookie:
        session.cookies.update(cookies)
        
    csrf_token = get_csrf_from_html(session)
    if csrf_token:
        logging.info(f"✅ CSRF-токен успішно отримано і додано до сесії.")
        session.headers['X-CSRF-TOKEN'] = csrf_token
    else:
        logging.error("Не вдалося отримати CSRF-токен. POST-запити, ймовірно, не працюватимуть.")
        return None # Можна повернути сесію, але краще позначити помилку

    return session


def make_request(
    session: requests.Session,
    method: str,
    url: str,
    delay: Optional[float] = None,
    data: Optional[Dict[str, Any]] = None,
    referer: Optional[str] = None,
    headers_profile: Optional[str] = None
) -> Optional[Union[str, Dict[str, Any]]]:
    """
    Виконує HTTP-запит, використовуючи профіль заголовків із сесії.
    CSRF-токен вже має бути в сесії.
    """
    if delay and delay > 0:
        logging.info(f"Чекаємо {delay} сек. перед запитом до {url}")
        time.sleep(delay)

    request_headers = session.headers.copy()

    # Застосовуємо профіль заголовків
    if headers_profile:
        profile_headers = session.config["headers"].get(headers_profile, {})
        request_headers.update(profile_headers)
    
    # Встановлюємо динамічний Referer та Origin
    if referer:
        request_headers['Referer'] = referer
        request_headers['Origin'] = session.config.get("base_url")

    log_message = f"--> Надсилання {method.upper()} запиту до {url}"
    logging.debug(log_message)
    logging.debug(f"Фінальні заголовки запиту: {request_headers}")
    logging.debug(f"Данні запиту: {data}")

    try:
        response = session.request(method, url, headers=request_headers, data=data, timeout=15)
        logging.debug(f"<-- Отримано відповідь: Статус {response.status_code}")
        response.raise_for_status()
        
        if 'application/json' in response.headers.get('Content-Type', ''):
            return response.json()
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Помилка запиту до {url}: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Не вдалося декодувати JSON з {url}. Тіло відповіді, яке спричинило помилку:")
        logging.error(response.text)
        return None