# -*- coding: utf-8 -*-

"""
Модуль скрейпера для збору даних про манхви та їхні глави з сайту.
"""

import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag
from tqdm import tqdm

from utils.settings import BASE_URL
from utils.network_utils import make_request
from db.manager import DBManager
from db.manga_service import save_manga_data_incrementally, get_mangas_stats
from .data_models import MangaData, ChapterData

# ==============================================================================
# 1. ДОПОМІЖНІ ФУНКЦІЇ ПАРСИНГУ (HELPERS)
# ==============================================================================

def _parse_single_manga_item(item: Tag) -> Optional[MangaData]:
    """Парсить дані однієї манхви з HTML-тегу <a>."""
    if not (data_id := item.get("data-id")) or not (url := item.get("href")):
        return None
    
    try:
        img_tag = item.select_one(".cards__img")
        img_url = ""
        if img_tag and 'style' in img_tag.attrs and "url(" in (style_attr := img_tag["style"]):
            img_url = style_attr.split("url(")[1].split(")")[0].strip("'\"")

        return {
            "id": str(data_id),
            "url": url,
            "name": item.select_one(".cards__name").text.strip(),
            "rating": item.select_one(".cards__rating").text.strip(),
            "info": item.select_one(".cards__info").text.strip(),
            "image": img_url,
            "chapters": []
        }
    except AttributeError as e:
        logging.warning(f"Не вдалося розпарсити елемент манхви (id: {data_id}): {e}")
        return None

def _parse_vol_chap_from_url(url: str) -> Tuple[Optional[int], Optional[int]]:
    """Витягує номер тому та глави з URL."""
    try:
        path_parts = urlparse(url).path.strip("/").split("/")
        # Припускаємо, що структура /.../volume/chapter
        return int(path_parts[-2]), int(path_parts[-1])
    except (ValueError, IndexError):
        logging.debug(f"Не вдалося визначити том/главу з URL: {url}")
        return None, None

def _parse_single_chapter_item(item: Tag) -> Optional[ChapterData]:
    """Парсить дані однієї глави з HTML-тегу <a>."""
    if not (href := item.get("href")):
        return None

    like_button = item.select_one("button.favourite-send-btn[data-id]")
    if not like_button or not (chapter_data_id := like_button.get("data-id")):
        return None
        
    volume, chapter = _parse_vol_chap_from_url(href)
    
    date_tag = item.select_one(".chapters__add-date")
    date = item.get("data-chapter-date") or (date_tag.get_text(strip=True) if date_tag else None)
    
    return {
        "data_id": chapter_data_id,
        "url": href,
        "volume": volume, 
        "chapter": chapter, 
        "date": date, 
    }

# ==============================================================================
# 2. ОСНОВНІ ФУНКЦІЇ ПАРСИНГУ ТА ЗАВАНТАЖЕННЯ
# ==============================================================================

def parse_manga_list(html: str) -> Dict[str, MangaData]:
    """Парсить список манхв з HTML-коду головної сторінки."""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("a.cards__item")
    
    mangas: Dict[str, MangaData] = {}
    for item in items:
        if isinstance(item, Tag) and (manga_data := _parse_single_manga_item(item)):
            mangas[manga_data["id"]] = manga_data
            
    return mangas

def parse_chapters_from_html(html: str) -> List[ChapterData]:
    """Парсить список глав з наданого HTML-коду."""
    soup = BeautifulSoup(html, "html.parser")
    chapters: List[ChapterData] = []
    
    for item in soup.select("a.chapters__item"):
        if isinstance(item, Tag) and (chapter_data := _parse_single_chapter_item(item)):
            chapters.append(chapter_data)
    
    return chapters

def fetch_chapters_for_manga(session: requests.Session, manga: MangaData, delay: float) -> List[ChapterData]:
    """Завантажує та парсить всі глави для однієї манхви."""
    # 1. Отримуємо глави, видимі на сторінці манхви
    page_html = make_request(session, 'GET', manga['url'], delay=delay)
    if not isinstance(page_html, str):
        logging.error(f"Не вдалося завантажити сторінку для манхви '{manga['name']}'.")
        return []

    # 2. Робимо POST-запит, щоб завантажити решту глав
    load_more_url = f"{BASE_URL}/chapters/load"
    post_data = {"manga_id": manga['id']}
    more_chapters_response = make_request(session, 'POST', load_more_url, delay=delay, data=post_data)
    
    more_chapters_html = ""
    if isinstance(more_chapters_response, dict) and "content" in more_chapters_response:
        more_chapters_html = more_chapters_response["content"]
    
    # 3. Об'єднуємо HTML і парсимо все разом
    full_html = page_html + more_chapters_html
    return parse_chapters_from_html(full_html)

# ==============================================================================
# 3. КЕРУЮЧІ ФУНКЦІЇ (ORCHESTRATORS)
# ==============================================================================

def fetch_manga_list_page(session: requests.Session, page_num: int) -> Optional[str]:
    """Завантажує HTML-код сторінки зі списком манг."""
    url_to_scrape = f"{BASE_URL}/manga?page={page_num}"
    logging.info(f"Завантаження списку манг з: {url_to_scrape}")
    
    main_page_html = make_request(session, 'GET', url_to_scrape, delay=0)
    if not isinstance(main_page_html, str):
        logging.error("Не вдалося завантажити головну сторінку. Скрейпінг зупинено.")
        return None
    return main_page_html

def enrich_manga_with_chapters(session: requests.Session, mangas: Dict[str, MangaData], delay: float):
    """Послідовно завантажує глави для кожної манхви та додає їх до словника."""
    logging.info(f"Починаємо завантаження глав для {len(mangas)} манг...")

    for manga_id, manga_data in tqdm(mangas.items(), desc="Завантаження глав манг"):
        try:
            chapters = fetch_chapters_for_manga(session, manga_data, delay)
            if chapters:
                manga_data["chapters"] = chapters
            else:
                logging.warning(f"Для '{manga_data['name']}' не знайдено жодної глави.")
        except Exception as e:
            # Загальний Exception, щоб скрипт не падав при помилці на одній манзі
            logging.error(f"Критична помилка при завантаженні глав для {manga_id}: {e}", exc_info=True)

def save_data_to_db(db: DBManager, data: Dict[str, MangaData]) -> Tuple[int, int]:
    """Зберігає зібрані дані в базу даних."""
    logging.info("Збереження даних в БД...")
    return save_manga_data_incrementally(db, data)

def display_db_stats(db: DBManager):
    """Виводить статистику по манхвам з бази даних."""
    logging.info("\n" + "="*50 + "\nСТАТИСТИКА ПО МАНХВАМ:\n" + "="*50)
    stats = get_mangas_stats(db) 
    for stat in stats:
        logging.info(f"- {stat['name']}: всього {stat['total_chapters']} глав.")
    logging.info("="*50)

def run_scraper(session: requests.Session, db: DBManager, page_num: int = 1, limit: Optional[int] = None, delay: float = 3, stats: bool = False):
    """
    Головна функція, що керує повним циклом роботи скрейпера.
    """
    # 1. Отримуємо список манг зі сторінки
    main_page_html = fetch_manga_list_page(session, page_num)
    if not main_page_html:
        return

    mangas = parse_manga_list(main_page_html)
    
    # 2. Застосовуємо ліміт, якщо він встановлений
    if limit:
        mangas = {k: v for i, (k, v) in enumerate(mangas.items()) if i < limit}
    
    # 3. Збагачуємо дані главами
    if mangas:
        enrich_manga_with_chapters(session, mangas, delay)
    else:
        logging.warning("На сторінці не знайдено жодної манхви. Подальша обробка неможлива.")
        return

    # 4. Зберігаємо дані в БД
    added_mangas, added_chapters = save_data_to_db(db, mangas)
    logging.info(f"Збереження завершено. Додано нових манг: {added_mangas}, нових глав: {added_chapters}.")
    
    # 5. Виводимо статистику, якщо потрібно
    if stats:
        display_db_stats(db)