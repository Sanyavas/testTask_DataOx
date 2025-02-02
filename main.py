import asyncio
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import dotenv_values

from src.services.playwright_service import playwright_async_run
from src.utils.dump_db import create_db_dump
from src.utils.py_logger import get_logger

logger = get_logger(__name__)
config = dotenv_values(".env")

MAIN_LINK = "https://www.olx.ua"
EMAIL_OLX = config.get("EMAIL_OLX")
PASSWORD_OLX = config.get("PASSWORD_OLX")


async def scheduler_async():
    scheduler = AsyncIOScheduler()

    # Запуск після старту
    scheduler.add_job(playwright_async_run,
                      trigger='date',
                      run_date=datetime.now() + timedelta(seconds=5),
                      args=[EMAIL_OLX, PASSWORD_OLX, MAIN_LINK])
    # повторюватися кожен день через 1 день
    scheduler.add_job(playwright_async_run,
                      trigger=IntervalTrigger(days=1, timezone="Europe/Kiev"),
                      args=[EMAIL_OLX, PASSWORD_OLX, MAIN_LINK])

    # Створення дампу бази о 12:00
    scheduler.add_job(create_db_dump, CronTrigger(hour=12, minute=0, timezone="Europe/Kiev"))

    scheduler.start()
    logger.info("Scheduler started")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler")
        scheduler.shutdown()


async def main():
    logger.info("Start program", extra={'custom_color': True})
    await scheduler_async()


if __name__ == '__main__':
    asyncio.run(main())
