from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Seller(Base):
    __tablename__ = 'sellers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    rating = Column(String, nullable=True)
    registered_date = Column(String, nullable=True)
    last_active_date = Column(String, nullable=True)
    location = Column(String, nullable=True)
    region = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())

    products = relationship("Product", back_populates="seller")


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=True)
    price = Column(String, nullable=True)
    type = Column(String, nullable=True)
    is_olx_delivery = Column(String, nullable=True)
    info = Column(JSON, nullable=True)
    site_id = Column(String, unique=True, nullable=False)
    views_count = Column(String, nullable=True)
    description = Column(String, nullable=True)
    image_urls = Column(String, nullable=True)
    product_url = Column(String, nullable=True)
    published_date = Column(String, nullable=True)
    seller_id = Column(Integer, ForeignKey('sellers.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())

    seller = relationship("Seller", back_populates="products")
