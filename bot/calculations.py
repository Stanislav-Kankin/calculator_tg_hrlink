from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import PaperCosts, TypicalOperations
import logging

engine = create_engine('sqlite:///user_data.db')
Session = sessionmaker(bind=engine)


def calculate_documents_per_year(data):
    employee_count = data['employee_count']
    documents_per_employee = data['documents_per_employee']
    turnover_percentage = data['turnover_percentage']
    result = employee_count * (
        documents_per_employee * (
            1 + turnover_percentage / 100))
    logging.debug(f"Calculated documents per year: {result}")
    return result


def calculate_pages_per_year(data):
    documents_per_year = calculate_documents_per_year(data)
    pages_per_document = data['pages_per_document']
    result = documents_per_year * pages_per_document
    logging.debug(f"Calculated pages per year: {result}")
    return result


def calculate_total_paper_costs(pages_per_year):
    session = Session()
    paper_costs = session.query(PaperCosts).first()
    session.close()
    result = pages_per_year * (
        paper_costs.page_cost + paper_costs.printing_cost +
        paper_costs.storage_cost + paper_costs.rent_cost)
    logging.debug(f"Calculated total paper costs: {result}")
    return result


def calculate_total_logistics_costs(data, documents_per_year):
    courier_delivery_cost = data['courier_delivery_cost']
    hr_delivery_percentage = data.get('hr_delivery_percentage', 0)
    total_logistics_costs = courier_delivery_cost * (
        hr_delivery_percentage / 100 * documents_per_year)
    logging.debug(f"Calculated total logistics costs: {total_logistics_costs}")
    return total_logistics_costs


def calculate_cost_per_minute(data):
    average_salary = data['average_salary']
    working_minutes_per_month = data.get('working_minutes_per_month', 10080)
    logging.debug(f"Calculated cost per minute: {average_salary / working_minutes_per_month}")
    return average_salary / working_minutes_per_month


def calculate_total_operations_costs(data, documents_per_year, cost_per_minute):
    session = Session()
    typical_operations = session.query(TypicalOperations).first()
    session.close()
    time_of_printing = typical_operations.time_of_printing
    time_of_signing = typical_operations.time_of_signing
    time_of_archiving = typical_operations.tome_of_archiving
    total_operations_costs = (
        (time_of_printing * cost_per_minute) +
        (time_of_archiving * cost_per_minute) +
        (time_of_signing * cost_per_minute)) * documents_per_year
    logging.debug(f"Calculated total operations costs: {total_operations_costs}")
    return total_operations_costs


def calculate_total_license_costs(data, license_costs):
    hr_specialist_count = data['hr_specialist_count']
    employee_count = data['employee_count']
    license_type = data.get('license_type', 'standard')  # Получаем тип лицензии

    # Стоимость лицензии для сотрудников
    if license_type == 'standard':
        employee_license_cost = license_costs.employee_license_cost  # 700 руб.
    elif license_type == 'lite':
        employee_license_cost = 500  # Lite лицензия стоит 500 руб.

    total_license_costs = (
        license_costs.main_license_cost +
        (license_costs.hr_license_cost * hr_specialist_count) +
        (employee_license_cost * employee_count)
    )
    logging.debug(f"Calculated total license costs: {total_license_costs}")
    return total_license_costs
