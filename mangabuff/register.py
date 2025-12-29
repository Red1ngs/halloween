import logging
from typing import Any, Dict, Optional
import requests

from utils.settings import CONFIG_FILE, BASE_URL, COOKIE_TTL
from utils.network_utils import create_mangabuff_session, make_request
from utils.file import load_json_data, save_json_data
from utils.time import get_current_timestamp, has_time_elapsed


def perform_login(session: requests.Session, auth_data: Dict[str, str]):
    """Виконує POST-запит для входу в систему."""
    login_url = f"{BASE_URL}/login"
    
    logging.info(f"Виконання входу на {login_url}")
    make_request(
        session, "POST", login_url,
        data=auth_data,
        headers_profile="ajax_post",
        referer=login_url
    )

def extract_and_update_cookies(session: requests.Session, config: Dict[str, Any]) -> bool:
    cookie_config = config.get("cookies", {})
    updated_cookies: Dict[str, str] = {}
    
    for name, config_value in cookie_config.items():
        fetched_value = session.cookies.get(name)
        
        if fetched_value:
            updated_cookies[name] = fetched_value
            continue

        if name == 'theme':
            updated_cookies[name] = config_value
            logging.warning(f"Cookie 'theme' не знайдено на сайті, використано значення за замовчуванням: '{config_value}'.")
        else:
            logging.error(f"Обов'язковий cookie '{name}' не було отримано. Перевірте правильність логіну та пароля.")
            return False

    logging.debug(updated_cookies)
    
    config["cookies"] = updated_cookies
    return True

def login_and_get_updated_config(config: Dict[str, Any], auth_data: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Оркеструє процес входу: створює сесію, виконує вхід, оновлює конфігурацію."""
    auth_session = create_mangabuff_session(config, use_cookie=False)
    if not auth_session:
        return None
        
    perform_login(auth_session, auth_data)
    
    if not extract_and_update_cookies(auth_session, config):
        return None
        
    config["timestamp"] = get_current_timestamp()
    save_json_data(config, CONFIG_FILE)
    return config

def get_auth_credentials(config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Отримує дані для входу з конфігурації або від користувача."""
    auth_data = config.get("auth_data")
    
    if auth_data and auth_data.get("email") and auth_data.get("password"):
        logging.info("Використання даних для входу з файлу конфігурації.")
        return auth_data
        
    try:
        email = input("Введіть email для акаунту: ")
        password = input("Введіть пароль: ")
        new_auth_data = {"email": email, "password": password}
        config["auth_data"] = new_auth_data
        return new_auth_data
    except KeyboardInterrupt:
        logging.info("Введення скасовано. Роботу припинено.")
    
def get_valide_config() -> dict[str,  dict[str, Any]] | None:
    config = load_json_data(CONFIG_FILE)
    if not config:
        logging.critical("Неможливо продовжити роботу без конфігурації.")
        return
        
    session_expired = not config.get("timestamp") or has_time_elapsed(config["timestamp"], COOKIE_TTL)
    
    if session_expired:
        logging.warning("Сесія застаріла або відсутня. Необхідно виконати вхід.")
        
        auth_data = get_auth_credentials(config)
        if not auth_data:
            return
            
        updated_config = login_and_get_updated_config(config, auth_data)
        if not updated_config:
            logging.critical("Не вдалося оновити сесію. Подальша робота неможлива.")
            return
        return updated_config
    else:
        logging.info("✅ Активна сесія є дійсною.")
        return config