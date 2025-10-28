# pyright: ignore[reportUnknownArgumentType]
# pyright: ignore[reportUnknownMemberType]
import logging
from typing import Any, Dict, Generator, List, Optional, Type, Union

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from .models import Manga, Chapter
from .manager import DBManager

def get_mangas_stats(db_manager: DBManager) -> List[Dict[str, Any]]:
    """
    Отримує статистику по всіх манхвах.
    
    Оскільки поле `is_read` відсутнє, статистика включає загальну 
    кількість глав для кожної манхви.
    
    Returns:
        Список словників, де кожен словник містить:
        - 'id': зовнішній ID манхви
        - 'name': назва манхви
        - 'total_chapters': загальна кількість глав
    """
    try:
        def _get_stats(session: Session) -> List[Dict[str, Any]]:
            stats_query = (
                session.query(
                    Manga.id,
                    Manga.name,
                    func.count(Chapter.db_id).label("total_chapters"),
                )
                .outerjoin(Chapter, Manga.id == Chapter.manga_id) # outerjoin, щоб включити манхви з 0 глав
                .group_by(Manga.id, Manga.name) # Групуємо, щоб count працював для кожної манхви
                .order_by(Manga.name) # Сортуємо для зручності
                .all()
            )
            
            # Конвертуємо результат (список Row-об'єктів) у список словників
            result = [
                {
                    "id": row.id,
                    "name": row.name,
                    "total_chapters": row.total_chapters,
                }
                for row in stats_query
            ]
            return result
        
        return db_manager.run_readonly(_get_stats)
            
    except Exception as e:
        logging.error(f"Помилка отримання статистики по манхвам: {e}", exc_info=True)
        return []

def get_manga_by_id(db_manager: DBManager, manga_external_id: str) -> Optional[Dict[str, Any]]:
    """
    Отримує дані про конкретну манхву за її зовнішнім ID, використовуючи DBManager.
    """
    try:
        def _get_by_id(session: Session) -> Optional[Dict[str, Any]]:
            manga = session.query(Manga).filter_by(id=manga_external_id).options(joinedload(Manga.chapters)).first()
            
            if not manga:
                return None
            
            chapters_list: list[dict[str, Any]] = []
            for chapter in manga.chapters: # Глави вже відсортовані
                chapters_list.append({
                    "db_id": chapter.db_id,
                    "data_id": chapter.data_id,
                    "volume": chapter.volume,
                    "chapter_num": chapter.chapter_num,
                    "date": chapter.date,
                    "url": chapter.url,
                })
            
            return {
                "db_id": manga.db_id,
                "id": manga.id,
                "url": manga.url,
                "name": manga.name,
                "rating": manga.rating,
                "info": manga.info,
                "image": manga.image,
                "chapters": chapters_list
            }

        return db_manager.run_readonly(_get_by_id)
            
    except Exception as e:
        logging.error(f"Помилка отримання манхви {manga_external_id}: {e}")
        return None

def update_manga(
    db_manager: DBManager,
    manga_external_id: str,
    url: Optional[str] = None,
    name: Optional[str] = None,
    rating: Optional[str] = None,
    info: Optional[str] = None,
    image: Optional[str] = None,
) -> bool:
    """
    Оновлює існуючу манхву в БД за її зовнішнім ID, використовуючи DBManager.
    """
    try:
        def _update(session: Session) -> bool:
            manga = session.query(Manga).filter_by(id=manga_external_id).first()
            if not manga:
                logging.warning(f"Манхву з ID {manga_external_id} не знайдено")
                return False
            
            updated = False
            if url is not None:
                manga.url = url
                updated = True
            if name is not None:
                manga.name = name
                updated = True
            if rating is not None:
                manga.rating = rating
                updated = True
            if info is not None:
                manga.info = info
                updated = True
            if image is not None:
                manga.image = image
                updated = True
            
            if not updated:
                logging.warning("Не передано жодного поля для оновлення")
                return False
            
            logging.info(f"Манхву {manga_external_id} успішно оновлено")
            return True
        
        return db_manager.run_in_tx(_update)
            
    except Exception as e:
        logging.error(f"Помилка оновлення манхви: {e}")
        return False

def add_chapter(
    db_manager: DBManager,
    chapter_external_id: str,
    manga_external_id: str,
    url: str,
    volume: Optional[int] = None,
    chapter_num: Optional[int] = None,
    date: Optional[str] = None,
) -> bool:
    """
    Додає нову главу до БД, використовуючи DBManager.
    """
    try:
        def _add(session: Session) -> bool:
            # Перевіряємо, чи існує манхва за зовнішнім ID
            if not session.query(Manga).filter_by(id=manga_external_id).first():
                logging.error(f"Манхву з ID {manga_external_id} не знайдено. Спочатку додайте манхву.")
                return False
            
            # Перевіряємо, чи не існує вже така глава за зовнішнім ID
            if session.query(Chapter).filter_by(data_id=chapter_external_id).first():
                logging.warning(f"Глава з ID {chapter_external_id} вже існує в БД")
                return False
            
            new_chapter = Chapter(
                data_id=chapter_external_id,
                manga_id=manga_external_id, # Використовуємо зовнішній ID манхви
                volume=volume,
                chapter_num=chapter_num,
                date=date,
                url=url,
            )
            session.add(new_chapter)
            logging.info(f"Главу {chapter_external_id} для манхви {manga_external_id} успішно додано")
            return True
        
        return db_manager.run_in_tx(_add)
            
    except Exception as e:
        logging.error(f"Помилка додавання глави: {e}")
        return False

def delete_manga(db_manager: DBManager, manga_external_id: str) -> bool:
    """
    Видаляє манхву та всі її глави з БД за її зовнішнім ID, використовуючи DBManager.
    """
    try:
        def _delete(session: Session) -> bool:
            manga = session.query(Manga).filter_by(id=manga_external_id).first()
            if not manga:
                logging.warning(f"Манхву з ID {manga_external_id} не знайдено")
                return False
            
            session.delete(manga)
            logging.info(f"Манхву {manga_external_id} успішно видалено (включаючи глави).")
            return True
        
        return db_manager.run_in_tx(_delete)
            
    except Exception as e:
        logging.error(f"Помилка видалення манхви: {e}")
        return False

def delete_chapter(db_manager: DBManager, chapter_external_id: str) -> bool:
    """
    Видаляє главу з БД за її зовнішнім ID, використовуючи DBManager.
    """
    try:
        def _delete(session: Session) -> bool:
            chapter = session.query(Chapter).filter_by(data_id=chapter_external_id).first()
            if not chapter:
                logging.warning(f"Главу з ID {chapter_external_id} не знайдено")
                return False
            
            session.delete(chapter)
            logging.info(f"Главу {chapter_external_id} успішно видалено.")
            return True
        
        return db_manager.run_in_tx(_delete)
            
    except Exception as e:
        logging.error(f"Помилка видалення глави: {e}")
        return False

def get_last_db_id(
    db_manager: DBManager,
    model_class: Type[Union[Manga, Chapter]]
) -> Optional[int]:
    """
    Отримує максимальний (останній) db_id для вказаної моделі (Manhwa або Chapter).
    Це загальна функція, яка працює для будь-якої моделі з полем `db_id`.

    Args:
        db_manager: Екземпляр DBManager.
        model_class: Клас моделі (Manhwa або Chapter), для якої шукаємо ID.

    Returns:
        Максимальний db_id як ціле число, або None, якщо таблиця порожня.
    """
    try:
        def _get_max_id(session: Session) -> Optional[int]:
            # Перевіряємо, чи є у моделі потрібне поле
            if not hasattr(model_class, 'db_id'):
                raise AttributeError(f"Модель {model_class.__name__} не має атрибута 'db_id'.")

            last_id = session.query(func.max(model_class.db_id)).scalar()
            return last_id

        return db_manager.run_readonly(_get_max_id)
            
    except Exception as e:
        logging.error(f"Помилка отримання останнього db_id для {model_class.__name__}: {e}", exc_info=True)
        return None

def get_last_manga_db_id(db_manager: DBManager) -> Optional[int]:
    """
    Зручна функція-обгортка для отримання останнього db_id для таблиці Manhwa.
    """
    return get_last_db_id(db_manager, Manga)

def get_last_chapter_db_id(db_manager: DBManager) -> Optional[int]:
    """
    Зручна функція-обгортка для отримання останнього db_id для таблиці Chapter.
    """
    return get_last_db_id(db_manager, Chapter)

def get_total_mangas_count(db_manager: DBManager) -> int:
    """
    Повертає загальну кількість манг у базі даних.
    """
    try:
        def _count(session: Session) -> int:
            return session.query(Manga).count()
        return db_manager.run_readonly(_count)
    except Exception as e:
        logging.error(f"Помилка підрахунку манг: {e}")
        return 0

def get_manga_by_order_number(db_manager: DBManager, order_num: int) -> Optional[Manga]:
    """
    Повертає манхву за її порядковим номером (db_id), відсортовану за db_id.
    """
    try:
        def _get_manga(session: Session) -> Optional[Manga]:
            # db_id починаються з 1 (або іншого значення, залежить від Sequence), 
            # тому order_num може прямо відповідати db_id, якщо немає видалених записів.
            # Якщо є видалені, то потрібно шукати nth-запис.
            
            # Цей підхід припускає, що db_id послідовні. 
            # Якщо db_id не є послідовними (через видалення), потрібно використовувати offset.
            # Якщо order_num = 1, це перша манхва (db_id=1).
            # Якщо вам потрібен N-й запис незалежно від db_id:
            return session.query(Manga).order_by(Manga.db_id).offset(order_num - 1).limit(1).first()
        return db_manager.run_readonly(_get_manga)
    except Exception as e:
        logging.error(f"Помилка отримання манхви за порядковим номером {order_num}: {e}")
        return None

def get_chapter_by_manga_and_offset(
    db_manager: DBManager, 
    manga_order_num: int, 
    chapter_offset: int
) -> Optional[Chapter]:
    """
    Повертає главу за порядковим номером манхви (db_id) та зміщенням глави.
    chapter_offset - це порядковий номер глави в межах цієї манхви, починаючи з 1.
    """
    try:
        def _get_chapter(session: Session) -> Optional[Chapter]:
            manga = get_manga_by_order_number(db_manager, manga_order_num)
            if not manga:
                return None
            
            # Отримуємо N-у главу для цієї манхви, відсортовану за chapter_num
            chapter = session.query(Chapter).filter_by(manga_id=manga.id).order_by(Chapter.chapter_num).offset(chapter_offset - 1).limit(1).first()
            return chapter
        return db_manager.run_readonly(_get_chapter)
    except Exception as e:
        logging.error(f"Помилка отримання глави для манхви {manga_order_num} зі зміщенням {chapter_offset}: {e}")
        return None

def get_chapter_by_combined_offset(
    db_manager: DBManager, 
    combined_offset: str # Формат "номер_манги.номер_глави"
) -> Optional[Dict[str, Any]]:
    """
    Отримує главу за комбінованим зміщенням у форматі "номер_манги.номер_глави".
    Повертає словник з деталями глави та манхви.
    """
    try:
        parts = combined_offset.split('.')
        if len(parts) != 2:
            raise ValueError("Неправильний формат зміщення. Очікується 'номер_манги.номер_глави'.")
        
        manga_order_num = int(parts[0])
        chapter_offset = int(parts[1])

        def _get_chapter_details(session: Session) -> Optional[Dict[str, Any]]:
            manga_obj = get_manga_by_order_number(db_manager, manga_order_num) # Отримуємо об'єкт Manga
            if not manga_obj:
                logging.warning(f"Манхву за порядковим номером {manga_order_num} не знайдено.")
                return None
            
            chapter_obj = get_chapter_by_manga_and_offset(db_manager, manga_order_num, chapter_offset)
            if not chapter_obj:
                logging.warning(f"Главу за зміщенням {chapter_offset} для манхви {manga_order_num} не знайдено.")
                return None

            return {
                "manga": {
                    "db_id": manga_obj.db_id,
                    "id": manga_obj.id,
                    "name": manga_obj.name,
                    "url": manga_obj.url,
                },
                "chapter": {
                    "db_id": chapter_obj.db_id,
                    "data_id": chapter_obj.data_id,
                    "chapter_num": chapter_obj.chapter_num,
                    "volume": chapter_obj.volume,
                    "date": chapter_obj.date,
                    "url": chapter_obj.url,
                }
            }
        
        return db_manager.run_readonly(_get_chapter_details)

    except (ValueError, IndexError) as ve:
        logging.error(f"Помилка парсингу зміщення '{combined_offset}': {ve}")
        return None
    except Exception as e:
        logging.error(f"Помилка отримання глави за комбінованим зміщенням '{combined_offset}': {e}")
        return None


def get_next_chapter_offset(db_manager: DBManager, current_offset: str) -> Optional[str]:
    """
    Повертає наступне комбіноване зміщення у форматі "номер_манги.номер_глави".
    Якщо поточне зміщення остання глава манхви, повертає першу главу наступної манхви.
    Якщо це остання глава останньої манхви, повертає None.
    """
    try:
        parts = current_offset.split('.')
        if len(parts) != 2:
            raise ValueError("Неправильний формат поточного зміщення. Очікується 'номер_манги.номер_глави'.")
        
        current_manga_order_num = int(parts[0])
        current_chapter_offset = int(parts[1])

        def _get_next(session: Session) -> Optional[str]:
            current_manga = get_manga_by_order_number(db_manager, current_manga_order_num)
            if not current_manga:
                return None
            
            # Спробувати отримати наступну главу в поточній манхві
            next_chapter_in_manga = session.query(Chapter).filter_by(manga_id=current_manga.id).order_by(Chapter.chapter_num).offset(current_chapter_offset).limit(1).first()

            if next_chapter_in_manga:
                return f"{current_manga_order_num}.{current_chapter_offset + 1}"
            else:
                # Якщо це остання глава в поточній манхві, спробувати наступну манхву
                next_manga_order_num = current_manga_order_num + 1
                next_manga = get_manga_by_order_number(db_manager, next_manga_order_num)
                if next_manga:
                    # Повернути першу главу наступної манхви
                    first_chapter_in_next_manga = session.query(Chapter).filter_by(manga_id=next_manga.id).order_by(Chapter.chapter_num).first()
                    if first_chapter_in_next_manga:
                        return f"{next_manga_order_num}.1" # Перша глава
            return None # Немає наступної глави/манхви

        return db_manager.run_readonly(_get_next)

    except (ValueError, IndexError) as ve:
        logging.error(f"Помилка парсингу поточного зміщення '{current_offset}': {ve}")
        return None
    except Exception as e:
        logging.error(f"Помилка отримання наступної глави за зміщенням '{current_offset}': {e}")
        return None


def save_manga_data_incrementally(
    db_manager: DBManager, 
    mangas_data: Dict[str, Dict[str, Any]]
) -> tuple[int, int]:
    """
    ОПТИМІЗОВАНА версія для інкрементного збереження даних, що використовує
    масові (bulk) операції для максимальної продуктивності.
    
    Правила роботи:
    1. Нові манхви додаються разом з усіма їхніми главами.
    2. Існуючі манхви не змінюються.
    3. Для існуючих манг додаються тільки нові глави.
    
    Returns:
        Кортеж (new_mangas_added, new_chapters_added).
    """
    try:
        def _save_bulk_incremental(session: Session) -> tuple[int, int]:
            if not mangas_data:
                return 0, 0

            # --- Етап 1: Отримуємо всі існуючі ID одним запитом (без змін, це ефективно) ---
            
            incoming_manga_ids = list(mangas_data.keys())
            existing_mangas_q = session.query(Manga.id).filter(Manga.id.in_(incoming_manga_ids)).all()
            existing_manga_ids = {row.id for row in existing_mangas_q}

            all_incoming_chapter_ids = [
                chap.get('data_id') for data in mangas_data.values() for chap in data.get('chapters', [])
            ]
            # Фільтруємо None, якщо 'data_id' може бути відсутнім
            all_incoming_chapter_ids = [cid for cid in all_incoming_chapter_ids if cid]
            
            existing_chapters_q = session.query(Chapter.data_id).filter(Chapter.data_id.in_(all_incoming_chapter_ids)).all()
            existing_chapter_ids = {row.data_id for row in existing_chapters_q}

            # --- Етап 2: Готуємо списки словників для масової вставки ---
            
            new_mangas_mappings = []
            new_chapters_mappings = []
            
            for manga_external_id, manga_data in mangas_data.items():
                
                # --- Сценарій 1: Нова манхва ---
                if manga_external_id not in existing_manga_ids:
                    # Готуємо словник для нової манхви
                    new_mangas_mappings.append({
                        "id": manga_external_id,
                        "url": manga_data.get("url", ""),
                        "name": manga_data.get("name", ""),
                        "rating": manga_data.get("rating", ""),
                        "info": manga_data.get("info", ""),
                        "image": manga_data.get("image", "")
                    })
                    
                    # Готуємо словники для ВСІХ її глав
                    for chapter_data in manga_data.get("chapters", []):
                        if chapter_data.get("data_id"):
                            new_chapters_mappings.append({
                                "data_id": chapter_data["data_id"],
                                "manga_id": manga_external_id,
                                "volume": chapter_data.get("volume"),
                                "chapter_num": chapter_data.get("chapter"), # chapter_num - назва поля в моделі
                                "date": chapter_data.get("date"),
                                "url": chapter_data.get("url", "")
                            })
                
                # --- Сценарій 2: Існуюча манхва ---
                else:
                    # Готуємо словники тільки для НОВИХ глав
                    for chapter_data in manga_data.get("chapters", []):
                        chapter_external_id = chapter_data.get("data_id")
                        if chapter_external_id and chapter_external_id not in existing_chapter_ids:
                            new_chapters_mappings.append({
                                "data_id": chapter_external_id,
                                "manga_id": manga_external_id,
                                "volume": chapter_data.get("volume"),
                                "chapter_num": chapter_data.get("chapter"),
                                "date": chapter_data.get("date"),
                                "url": chapter_data.get("url", "")
                            })

            # --- Етап 3: Виконуємо масові вставки (якщо є що вставляти) ---
            
            if new_mangas_mappings:
                session.bulk_insert_mappings(Manga, new_mangas_mappings)
            
            if new_chapters_mappings:
                session.bulk_insert_mappings(Chapter, new_chapters_mappings)

            new_mangas_added = len(new_mangas_mappings)
            new_chapters_added = len(new_chapters_mappings)

            logging.info(f"Оптимізоване збереження завершено. Додано нових манг: {new_mangas_added}, нових глав: {new_chapters_added}.")
            return new_mangas_added, new_chapters_added

        return db_manager.run_in_tx(_save_bulk_incremental)
            
    except Exception as e:
        logging.error(f"Помилка оптимізованого збереження даних у БД: {e}", exc_info=True)
        return 0, 0


def yield_chapters_in_batches(
    db_manager: DBManager, 
    batch_size: int,
    start_offset: Optional[str] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    "Чистий" генератор, який послідовно видає глави порціями (батчами) з БД.
    Не знає нічого про скрейпінг.
    """
    session: Optional[Session] = None
    try:
        session = db_manager.SessionLocal()
        
        start_manga_order = 1
        start_chapter_offset_in_manga = 0

        if start_offset:
            try:
                m_part, c_part = start_offset.split('.')
                start_manga_order = int(m_part)
                start_chapter_offset_in_manga = int(c_part)
            except (ValueError, IndexError):
                logging.warning(f"Неправильний формат зміщення '{start_offset}'. Починаємо з початку.")

        current_manga_order = start_manga_order
        
        while True:
            current_manga = session.query(Manga).order_by(Manga.id).offset(current_manga_order - 1).limit(1).first()
            if not current_manga:
                logging.info("Генератор завершив роботу: всі манхви в БД оброблено.")
                break

            chapter_offset = start_chapter_offset_in_manga if current_manga_order == start_manga_order else 0

            chapters = session.query(Chapter)\
                .filter(Chapter.manga_id == current_manga.id)\
                .order_by(Chapter.chapter_num)\
                .offset(chapter_offset)\
                .all()

            if chapters:
                for i in range(0, len(chapters), batch_size):
                    batch_chapters = chapters[i:i + batch_size]
                    
                    yield {
                        "items": [
                            {"manga_id": ch.manga_id, "chapter_id": ch.data_id}
                            for ch in batch_chapters
                        ],
                        "last_processed_offset": f"{current_manga_order}.{chapter_offset + i + len(batch_chapters)}"
                    }
            
            current_manga_order += 1
            
    except Exception as e:
        logging.error(f"Помилка в генераторі `yield_chapters_in_batches`: {e}", exc_info=True)
    finally:
        if session:
            session.close()