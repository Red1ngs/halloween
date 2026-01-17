# type: ignore
import json
import logging
import time
import socket
import requests.packages.urllib3.util.connection as urllib3_conn
from typing import Any, Dict, Optional, Union

import requests
from bs4 import BeautifulSoup

try:
    from .settings import BASE_URL
except ImportError:
    from utils.settings import BASE_URL

def allowed_gai_family():
    return socket.AF_INET

urllib3_conn.allowed_gai_family = allowed_gai_family

def get_csrf_from_html(session: requests.Session, timeout: float) -> Optional[str]:
    """
    Виконує GET-запит на вказану URL, перевіряє авторизацію та витягує CSRF-токен.
    """
    logging.info(f"Намагаюся отримати CSRF-токен та перевірити вхід: {BASE_URL}")
    try:
        response = session.get(BASE_URL, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Перевірка авторизації (чи бачить сайт нас як користувача)
        user_div = soup.find("div", class_="menu__name")
        if user_div:
            user_name = user_div.get_text(strip=True)
            logging.info(f"✅ Успішна автентифікація. Користувач: {user_name}")
        else:
            logging.warning("⚠️ Користувача не знайдено (виглядає як Гість). Перевірте Cookies.")

        # 2. Отримання CSRF
        meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
        if meta_tag:
            return meta_tag.get('content')
            
        logging.warning("Мета-тег 'csrf-token' не знайдено на сторінці.")
        return None

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Не вдалося завантажити сторінку: {e}")
        return None


def create_mangabuff_session(config: Dict[str, Any], use_cookie: bool = True) -> Optional[requests.Session]:
    """
    Створює сесію з проксі, headers та cookies.
    """
    session = requests.Session()
    session.config = config  # Зберігаємо конфіг
    session.trust_env = False  # Ігноруємо системні проксі, використовуємо лише з конфігу
    
    # 1. Налаштування проксі
    proxies = config.get("proxies", {})
    if proxies:
        session.proxies = {
            "http": proxies.get("http"),
            "https": proxies.get("https")
        }
        logging.info(f"🌐 Проксі встановлено: {proxies.get('http')}")

    # 2. Налаштування заголовків та Cookies
    headers = config.get("headers", {}).get("common", {})
    session.headers.update(headers)
    
    if use_cookie:
        cookies = config.get("cookies", {})
        session.cookies.update(cookies)
        logging.info("🍪 Cookies завантажено в сесію.")

    # 3. Спроба підключення та отримання CSRF
    try:
        csrf_token = get_csrf_from_html(session)
        
        if csrf_token:
            session.headers['X-CSRF-TOKEN'] = csrf_token
            logging.info(f"✅ Сесія готова. CSRF отримано.")
            return session
        else:
            logging.error("❌ Не вдалося отримати CSRF-токен. Сесію не створено.")
            
    except Exception as e:
        logging.error(f"❌ Критична помилка при створенні сесії: {e}")
        
        # Блок діагностики проксі (якщо основний запит впав)
        if proxies:
            logging.info("🕵️ Починаю діагностику проксі...")
            try:
                test = session.get("https://www.google.com", timeout=10)
                logging.info(f"Google через проксі доступний (Status: {test.status_code}). Проблема в Mangabuff або Cookies.")
            except Exception as proxy_err:
                logging.error(f"💀 Проксі мертвий. Google недоступний: {proxy_err}")

    return None


def make_request(
    session: requests.Session,
    method: str,
    url: str,
    delay: Optional[float] = None,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    referer: Optional[str] = None,
    headers_profile: Optional[str] = None
) -> Optional[Union[str, Dict[str, Any]]]:
    """
    Універсальна функція запиту з підтримкою профілів заголовків.
    """
    if delay and delay > 0:
        logging.info(f"⏳ Чекаємо {delay} сек. перед запитом до {url}")
        time.sleep(delay)

    request_headers = session.headers.copy()

    # Застосовуємо профіль заголовків (наприклад 'image', 'api' тощо з конфігу)
    if headers_profile:
        profile_headers = session.config.get("headers", {}).get(headers_profile, {})
        request_headers.update(profile_headers)
    
    # Динамічний Referer та Origin
    if referer:
        request_headers['Referer'] = referer
        request_headers['Origin'] = session.config.get("base_url", BASE_URL)

    log_message = f"--> {method.upper()} {url}"
    logging.debug(log_message)

    try:
        response = session.request(
            method, 
            url, 
            headers=request_headers, 
            data=data, 
            params=params, 
            timeout=30  # Збільшено таймаут для проксі
        )
        
        logging.debug(f"<-- Status: {response.status_code}")
        response.raise_for_status()
        
        if 'application/json' in response.headers.get('Content-Type', ''):
            return response.json()
        return response.text

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Помилка запиту до {url}: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"❌ Помилка декодування JSON з {url}.")
        return None