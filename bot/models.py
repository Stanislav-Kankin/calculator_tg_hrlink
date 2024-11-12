from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class UserData(Base):
    __tablename__ = 'user_data'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    organization_name = Column(String)
    employee_count = Column(Integer)
    hr_specialist_count = Column(Integer)
    documents_per_employee = Column(Integer)
    turnover_percentage = Column(Float)
    working_minutes_per_month = Column(Integer)
    average_salary = Column(Float)
    courier_delivery_cost = Column(Float)
    hr_delivery_percentage = Column(Float)
    timestamp = Column(DateTime, default=datetime.now())
