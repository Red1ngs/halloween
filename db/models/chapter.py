from sqlalchemy import Column, Sequence, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base

class Chapter(Base):
    __tablename__ = "chapters"

    # Автоінкрементоване цілочисельне ID
    db_id = Column(Integer, Sequence('chapter_db_id_seq'), primary_key=True)

    # Оригінальний data_id (якщо він використовується для зовнішніх посилань)
    # Якщо це унікальний зовнішній ідентифікатор, то можна зробити его Unique=True
    data_id = Column(String, index=True, unique=True, nullable=False) 
    
    manga_id = Column(String, ForeignKey("mangas.id", ondelete="CASCADE"), nullable=False) # Змінено на manga.id
    
    # Номер глави, який буде використовуватись для сортування та "зміщення"
    chapter_num = Column(Integer, nullable=True) 
    
    volume = Column(Integer, nullable=True) # Залишаємо для інформації, але сортуватимемо за chapter_num
    date = Column(String, nullable=True) 
    url = Column(String, nullable=False)

    manga = relationship("Manga", back_populates="chapters")

    def __repr__(self):
        return f"<Chapter(db_id={self.db_id}, data_id='{self.data_id}', manga_id='{self.manga_id}', chapter_num='{self.chapter_num}')>"