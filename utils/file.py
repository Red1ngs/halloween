import json
import logging
import os
from typing import Any, Dict

def load_json_data(path: str) -> Dict[str, Any]:
    """
    Безпечно завантажує дані з JSON-файлу.
    Повертає дані з файлу або None у разі помилки.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.error(f"Файл {path} не знайдено або він пошкоджений.")
        raise

def save_json_data(data: Any, path: str) -> bool:
    """
    Безпечно зберігає дані у JSON-файл.
    Повертає True у разі успіху, False у разі помилки.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except IOError as e:
        logging.error(f"Не вдалося записати у файл {path}: {e}")
        return False
    
def load_txt_data(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logging.warning(f"Файл {path} не знайдено. Створюю порожній файл.")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            pass
        return ""
    except Exception as e:
        logging.error(f"Помилка при читанні файлу {path}: {e}")
        return ""

def save_txt_data(data: str, path: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        return True
    except IOError as e:
        logging.error(f"Не вдалося записати у файл {path}: {e}")
        return False
    