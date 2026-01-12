import math
import time
import logging
from typing import Optional
import requests

from db.manager import DBManager
from db.manga_service import get_last_manga_db_id, yield_chapters_in_batches
from mangabuff.reader import process_single_batch 
from mangabuff.scraper import run_scraper
from utils.file import save_txt_data, load_txt_data
from utils.enums import CollectMode, BatchResult
from utils.settings import BASE_URL, LAST_READED, SCRAPER_MANGA_PER_PAGE, BATCH_SIZE, DELAY

class ResourceCollector:
    """
    Універсальний клас для збору ресурсів (цукерок або карток).
    """
    def __init__(self, 
                 session: requests.Session, 
                 db_manager: DBManager, 
                 target_amount: int, 
                 mode: CollectMode = CollectMode.CANDY):
        
        self.session = session
        self.db_manager = db_manager
        self.target_amount = target_amount
        self.mode = mode
        
        self.items_collected: int = 0
        self.last_processed_offset: Optional[str] = None

    @property
    def progress_info(self) -> str:
        """Повертає текстовий опис прогресу залежно від режиму."""
        item_name = "цукерок" if self.mode == CollectMode.CANDY else "карток"
        return f"{self.items_collected}/{self.target_amount} ({item_name})"

    def _load_state(self):
        self.last_processed_offset = load_txt_data(LAST_READED) or None
        logging.info(f"Стан завантажено. Остання позиція: {self.last_processed_offset or 'немає'}")

    def _save_state(self):
        if self.last_processed_offset:
            save_txt_data(self.last_processed_offset, LAST_READED)
            logging.info(f"Стан збережено. Остання позиція: {self.last_processed_offset}")

    def _update_progress(self, result: BatchResult):
        """Оновлює лічильник залежно від обраного режиму."""
        if self.mode == CollectMode.CANDY:
            added = result.candies
            if result.cards_found > 0:
                logging.info(f"Випала картка, але ми шукаємо цукерки. Пропускаємо.")
        else: # CollectMode.CARD
            added = result.cards_found
            if result.candies > 0:
                logging.debug(f"Отримано цукерки ({result.candies}), але ми шукаємо картки.")
        
        self.items_collected += added
        return added

    def _process_chapters_from_db(self) -> bool:
        chapters_found = False
        chapter_generator = yield_chapters_in_batches(
            db_manager=self.db_manager,
            batch_size=BATCH_SIZE,
            start_offset=self.last_processed_offset
        )

        # Початкова затримка (можна брати з конфігу або стандартну)
        current_delay = DELAY

        for batch in chapter_generator:
            chapters_found = True
            
            self.last_processed_offset = batch.get("last_processed_offset")
            batch_payload = batch.get("items", [])
            
            if not batch_payload:
                continue

            # --- ВИКЛИК З ДИНАМІЧНОЮ ЗАТРИМКОЮ ---
            raw_result = process_single_batch(
                self.session, 
                BASE_URL, 
                batch_payload, 
                delay=current_delay  # Передаємо поточну затримку
            )
            
            batch_result = BatchResult(
                candies=raw_result.get('candies', 0),
                cards_found=raw_result.get('cards', 0)
            )

            self._update_progress(batch_result)
            
            # --- ЛОГІКА КЕРУВАННЯ НАСТУПНОЮ ЗАТРИМКОЮ ---
            
            # Якщо ми чекали більше 1.5 годин (5400 с) І знайшли цукерку/гарбуз
            if current_delay >= 5400 and batch_result.candies > 0:
                logging.info("⚡️ Довге очікування принесло цукерку! Наступний запит виконуємо МИТТЄВО.")
                current_delay = 10.0
            else:
                current_delay = DELAY

            logging.info(f"Прогрес: {self.progress_info}. Наступна затримка: {current_delay} с.")

            if self.is_target_reached():
                break
        
        return chapters_found

    def _run_scraping_if_needed(self):
        logging.warning("Всі доступні глави в БД оброблено. Запускаю скрейпер.")
        last_id = get_last_manga_db_id(self.db_manager) or 0
        page_to_scrape = math.ceil((last_id + 1) / SCRAPER_MANGA_PER_PAGE)
        
        run_scraper(self.session, self.db_manager, page_num=page_to_scrape)
        
        logging.info("Скрейпінг завершено. Пауза 10 секунд...")
        time.sleep(10)

    def is_target_reached(self) -> bool:
        return self.items_collected >= self.target_amount

    def run(self):
        self._load_state()
        logging.info(f"--- Запуск. Ціль: зібрати {self.target_amount} "
                     f"{'цукерок' if self.mode == CollectMode.CANDY else 'карток'} ---")

        try:
            while not self.is_target_reached():
                logging.info("="*50)
                logging.info(f"Новий цикл. Прогрес: {self.progress_info}")

                chapters_were_found = self._process_chapters_from_db()

                if self.is_target_reached():
                    break
                
                if not chapters_were_found:
                    self._run_scraping_if_needed()
        finally:
            logging.info("="*50)
            logging.info(f"--- Завершення. Всього зібрано: {self.progress_info} ---")
            self._save_state()
