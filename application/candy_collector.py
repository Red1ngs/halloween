import math
import time
import logging
import requests
from typing import Optional

from db.manager import DBManager
from db.manga_service import get_last_manga_db_id, yield_chapters_in_batches
from mangabuff.reader import process_single_batch
from mangabuff.scraper import run_scraper
from utils.file import save_txt_data, load_txt_data
from utils.settings import BASE_URL, LAST_READED, SCRAPER_MANGA_PER_PAGE, BATCH_SIZE

class CandyCollector:
    """
    Керує процесом збору "цукерок", інкапсулюючи всю пов'язану логіку:
    - Управління станом (прогрес, ціль).
    - Обробка глав з бази даних.
    - Прийняття рішень про запуск скрейпера.
    """
    def __init__(self, session: requests.Session, db_manager: DBManager, target_candies: int):
        self.session = session
        self.db_manager = db_manager
        self.target_candies = target_candies
        
        self.candies_collected: int = 0
        self.last_processed_offset: Optional[str] = None

    def _load_state(self):
        """Завантажує останню збережену позицію з файлу."""
        self.last_processed_offset = load_txt_data(LAST_READED) or None
        logging.info(f"Стан завантажено. Остання позиція: {self.last_processed_offset or 'немає'}")

    def _save_state(self):
        """Зберігає поточну позицію у файл."""
        if self.last_processed_offset:
            save_txt_data(self.last_processed_offset, LAST_READED)
            logging.info(f"Стан збережено. Остання позиція: {self.last_processed_offset}")

    def _process_chapters_from_db(self) -> bool:
        """
        Відповідає за читання та обробку глав з бази даних.
        Повертає True, якщо хоча б одна глава була знайдена та оброблена, інакше False.
        """
        chapters_found = False
        chapter_generator = yield_chapters_in_batches(
            db_manager=self.db_manager,
            batch_size=BATCH_SIZE,
            start_offset=self.last_processed_offset
        )

        for batch in chapter_generator:
            chapters_found = True
            
            self.last_processed_offset = batch.get("last_processed_offset")
            batch_payload = batch.get("items", [])
            
            if not batch_payload:
                continue

            candies_from_batch = process_single_batch(self.session, BASE_URL, batch_payload)
            self.candies_collected += candies_from_batch
            
            logging.info(f"Оброблено батч. Отримано: {candies_from_batch}. Загальний прогрес: {self.candies_collected}/{self.target_candies}")

            if self.is_target_reached():
                break
        
        return chapters_found

    def _run_scraping_if_needed(self):
        """Запускає скрейпер для поповнення бази даних новими главами."""
        logging.warning("Всі доступні глави в БД оброблено. Запускаю скрейпер.")
        
        last_id = get_last_manga_db_id(self.db_manager) or 0
        # Розраховуємо, з якої сторінки сайту починати скрейпінг
        page_to_scrape = math.ceil((last_id + 1) / SCRAPER_MANGA_PER_PAGE)
        
        run_scraper(self.session, self.db_manager, page_num=page_to_scrape)
        
        logging.info("Скрейпінг завершено. Пауза 10 секунд перед продовженням читання...")
        time.sleep(10)

    def is_target_reached(self) -> bool:
        """Перевіряє, чи досягнуто цілі по збору."""
        return self.candies_collected >= self.target_candies

    def run(self):
        """Головний метод, що запускає цикл збору."""
        self._load_state()
        logging.info(f"--- Запуск. Ціль: зібрати {self.target_candies} цукерок ---")

        try:
            while not self.is_target_reached():
                logging.info("="*50)
                logging.info(f"Новий цикл читання. Прогрес: {self.candies_collected}/{self.target_candies}. Позиція: {self.last_processed_offset or 'початок'}")

                chapters_were_found = self._process_chapters_from_db()

                if self.is_target_reached():
                    break
                
                # Якщо база даних вичерпана, запускаємо скрейпер
                if not chapters_were_found:
                    self._run_scraping_if_needed()
        finally:
            logging.info("="*50)
            logging.info(f"--- Завершення роботи. Всього зібрано: {self.candies_collected}/{self.target_candies} ---")
            self._save_state()