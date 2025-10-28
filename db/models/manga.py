from sqlalchemy import Column, Integer, Sequence, String
from sqlalchemy.orm import relationship

from .base import Base

class Manga(Base):
    __tablename__ = "mangas"

    # Автоінкрементоване цілочисельне ID
    db_id = Column(Integer, Sequence('manga_db_id_seq'), primary_key=True) 
    
    # Оригінальний ID (якщо він використовується для зовнішніх посилань)
    # Якщо він не унікальний для всієї БД, то можна прибрати index=True
    # Якщо це унікальний зовнішній ідентифікатор, то можна зробити его Unique=True
    id = Column(String, index=True, unique=True, nullable=False) 

    url = Column(String, nullable=False)
    name = Column(String, nullable=False)
    rating = Column(String, default="")
    info = Column(String, default="")
    image = Column(String, default="")

    chapters = relationship("Chapter", back_populates="manga", cascade="all, delete-orphan", order_by="Chapter.chapter_num")

    def __repr__(self):
        return f"<Manga(id='{self.id}', name='{self.name}')>"