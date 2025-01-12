from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.db.models import Seller, Product
from src.utils.py_logger import get_logger

logger = get_logger(__name__)

async def save_data_to_db(data: dict, db: AsyncSession):
    """
    Зберігає дані продавця та продукту в базу даних.
    """
    try:

        seller_data = {
            "name": data['seller'].get('name', None),
            "phone_number": data['seller'].get('phone_number', None),
            "rating": data['seller'].get('rating', None),
            "registered_date": data['seller'].get('registered_date', None),
            "last_active_date": data['seller'].get('last_active_date', None),
            "location": data['seller'].get('location', None),
            "region": data['seller'].get('region', None),
        }


        seller = Seller(**seller_data)
        db.add(seller)
        await db.flush()

        product_data = {
            "title": data['product'].get('title', None),
            "price": data['product'].get('price', None),
            "type": data['product'].get('type_item', None),
            "is_olx_delivery": data['product'].get('olx_delivery', None),
            "info": data['product'].get('info', None),
            "site_id": data['product'].get('site_id', None),
            "views_count": data['product'].get('views_count', None),
            "description": data['product'].get('description', None),
            "image_urls": data['product'].get('images', None),
            "product_url": data['product'].get('link', None),
            "published_date": data['product'].get('date_published', None),
            "seller_id": seller.id,
        }


        product = Product(**product_data)
        db.add(product)

        await db.commit()
        logger.info(f"Дані успішно збережено!", extra={'custom_color': True})
    except Exception as e:
        await db.rollback()
        logger.error(f"Помилка при записі в БД: {e}")
