from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

from bot.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def get_session():
    return Session()
