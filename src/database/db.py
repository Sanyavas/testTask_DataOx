import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from utils.py_logger import get_logger


logger = get_logger(__name__)
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession,
                                  expire_on_commit=False)


# Фабрика сесій
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as err:
            logger.error(f"ERROR session DB: {err}")
            await session.rollback()
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncSession:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as err:
            logger.error(f"ERROR session DB: {err}")
            await session.rollback()
        finally:
            await session.close()