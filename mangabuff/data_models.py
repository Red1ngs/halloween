# data_models.py
from typing import List, Optional, TypedDict

class ChapterData(TypedDict):
    data_id: str
    url: str
    volume: Optional[int]
    chapter: Optional[int]
    date: Optional[str]

class MangaData(TypedDict):
    id: str
    url: str
    name: str
    rating: str
    info: str
    image: str
    chapters: List[ChapterData] # Глави будуть додані сюди