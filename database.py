import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# The connection string to our Docker PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/order_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Define the "orders" table
class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    item_id = Column(String)
    quantity = Column(Integer)
    status = Column(String, default="Processing")
    created_at = Column(DateTime, default=datetime.utcnow)

# This function creates the tables in the database if they don't exist yet
def init_db():
    Base.metadata.create_all(bind=engine)