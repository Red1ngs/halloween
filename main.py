# file: main.py

import logging
import requests

from application.collector import ResourceCollector, CollectMode
from db.manager import DBManager
from mangabuff.register import get_valide_config
from utils.logging import setup_logging
from utils.network_utils import create_mangabuff_session
from utils.settings import DB_URL, TARGET_COUNT, MODE

def setup_dependencies() -> tuple[DBManager, requests.Session]:
    """
    Ініціалізує та налаштовує всі необхідні залежності:
    - З'єднання з БД.
    - HTTP-сесію з валідною конфігурацією.
    """
    db_manager = DBManager(DB_URL)
    db_manager.init_models()
    
    config = get_valide_config()
    if not config:
        raise RuntimeError("Не вдалося отримати конфігурацію.")
    
    session = create_mangabuff_session(config)
    if not session:
        raise RuntimeError("Не вдалося ініціалізувати HTTP сесію.")
        
    return db_manager, session

def main():
    """Головна функція, точка входу в програму."""
    setup_logging()
    db_manager = None
    session = None
    
    try:
        db_manager, session = setup_dependencies()
        
        collector = ResourceCollector(
            session=session, 
            db_manager=db_manager, 
            target_amount=TARGET_COUNT,
            mode=CollectMode(MODE)
        )
        collector.run()

    except KeyboardInterrupt:
        logging.warning("Роботу зупинено користувачем.")
    except Exception as e:
        logging.critical(f"Виникла критична помилка: {e}", exc_info=True)
    finally:
        if session:
            session.close()
        if db_manager:
            db_manager.dispose()
        logging.info("Скрипт завершив роботу.")

if __name__ == "__main__":
    main()
