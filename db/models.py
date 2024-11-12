from sqlalchemy import Column, Integer, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UserData(Base):
    __tablename__ = 'user_data'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    input_value = Column(Float)
