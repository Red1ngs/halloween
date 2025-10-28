# database/manager.py
from __future__ import annotations

from contextlib import contextmanager
from typing import (
    Iterator, Callable, TypeVar
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

T = TypeVar("T")

class DBManager:
    def __init__(
        self,
        url: str,
        *,
        echo: bool = False,
        pool_pre_ping: bool = True,
        expire_on_commit: bool = False,
    ) -> None:
        self.engine = create_engine(
            url,
            echo=echo,
            pool_pre_ping=pool_pre_ping,
        )
        self.SessionLocal: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=expire_on_commit,
        )

    # --- Ініціалізація / завершення ---
    def init_models(self) -> None:
        from . import models
        models.Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()

    # --- Сесії ---
    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def readonly(self) -> Iterator[Session]:
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def run_in_tx(
        self,
        fn: Callable[[Session], T],
    ) -> T:
        with self.session() as s:
            res = fn(s)
            return res

    def run_readonly(
        self,
        fn: Callable[[Session], T],
    ) -> T:
        with self.readonly() as s:
            res = fn(s)
            return res