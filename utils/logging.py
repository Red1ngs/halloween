import logging
import sys

from .settings import LOG_FILE

def setup_logging():
    """Налаштовує логування для виводу в консоль та у файл."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )