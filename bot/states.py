from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    user_id = State()
    organization_name = State()
    employee_count = State()
    hr_specialist_count = State()
    license_type = State()  # Новое состояние
    documents_per_employee = State()
    pages_per_document = State()
    turnover_percentage = State()
    average_salary = State()
    courier_delivery_cost = State()
    hr_delivery_percentage = State()
    contact_name = State()
    contact_phone = State()
    contact_email = State()
    contact_preference = State()
    waiting_for_day = State()  # Новое состояние
    waiting_for_week = State()  # Новое состояние
    waiting_for_quarter = State()  # Новое состояние
    waiting_for_year = State()  # Новое состояние
