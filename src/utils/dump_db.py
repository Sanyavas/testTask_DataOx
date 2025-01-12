import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
from psycopg2 import sql

from src.utils.py_logger import get_logger

logger = get_logger(__name__)

load_dotenv()


async def create_dump():

    connection = psycopg2.connect(
        dbname=os.getenv('POSTGRES_DB_NAME'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_DOMAIN'),
        port=os.getenv('POSTGRES_PORT')
    )

    cursor = connection.cursor()

    dump_dir = os.path.join(os.getcwd(), 'dumps')
    os.makedirs(dump_dir, exist_ok=True)
    dump_file_path = os.path.join(dump_dir, f"db_dump_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv")

    try:
        with open(dump_file_path, 'w', newline='') as dump_file:
            cursor.copy_expert(
                sql.SQL("COPY (SELECT * FROM products) TO STDOUT WITH CSV HEADER"),
                dump_file
            )

    except Exception as e:
        print(f"Error during dump creation: {e}")

    finally:
        cursor.close()
        connection.close()

async def create_db_dump():
    """Функція для створення дампа бази даних"""
    try:
        dump_file_path = await create_dump()
        logger.info(f"Database dump created successfully at {dump_file_path}")
    except Exception as e:
        logger.error(f"Error creating database dump: {e}")


if __name__ == "__main__":
    create_dump()
