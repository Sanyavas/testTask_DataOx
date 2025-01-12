import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import uvicorn
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import dotenv_values

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.db.session import get_db
from src.services.playwright_service import playwright_async_run_main
from src.utils.dump_db import create_db_dump
from src.utils.py_logger import get_logger

logger = get_logger(__name__)
config = dotenv_values(".env")

MAIN_LINK = "https://www.olx.ua"
EMAIL_OLX = config.get("EMAIL_OLX")
PASSWORD_OLX = config.get("PASSWORD_OLX")

app = FastAPI()

origins = [
    "http://localhost"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Функція для запуску планувальника."""

    scheduler = AsyncIOScheduler()
    try:
        logger.info("Scheduler started", extra={'custom_color': True})

        # Запуск Playwright один раз відразу після старту
        scheduler.add_job(print("Hello World"),
                          trigger='date',
                          run_date=datetime.now() + timedelta(seconds=5))

        scheduler.add_job(playwright_async_run_main,
                          trigger=IntervalTrigger(days=1, timezone="Europe/Kiev"),
                          args=[EMAIL_OLX, PASSWORD_OLX, MAIN_LINK])

        # Створення дампу бази даних о 12:00
        scheduler.add_job(create_db_dump, CronTrigger(hour=12, minute=0, timezone="Europe/Kiev"))

        scheduler.start()
        yield
        logger.info("Scheduler stopped", extra={'custom_color': True})
        scheduler.shutdown(wait=False)
    except Exception as e:
        logger.error(f"Error: {e}")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def healthchecker_db(db: AsyncSession = Depends(get_db)):
    """Функція для перевірки з'єднання з базою даних."""
    try:
        result = await db.execute(text("SELECT 1"))
        if result is None:
            raise HTTPException(status_code=500, detail="Database is not configured correctly")
        return {"message": "Database is working! Welcome to FastAPI!"}
    except Exception as e:
        logger.error(f"Error connecting to the DATABASE. {e}")
        raise HTTPException(status_code=500, detail="Error connecting to the db")


if __name__ == '__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8003, reload=True)
