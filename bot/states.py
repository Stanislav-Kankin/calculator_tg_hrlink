from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    organization_name = State()
    employee_count = State()
    hr_specialist_count = State()
    documents_per_employee = State()
    pages_per_document = State()
    turnover_percentage = State()
    average_hr_salary = State()  # Новое состояние
    courier_delivery_cost = State()
    hr_delivery_percentage = State()
    contact_name = State()
    contact_phone = State()
    contact_email = State()
    contact_preference = State()
