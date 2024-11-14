import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, UserData, PaperCosts, LicenseCosts
from database import init_db
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
init_db()

# Создаем подключение к базе данных
engine = create_engine('sqlite:///user_data.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


class Form(StatesGroup):
    organization_name = State()
    employee_count = State()
    hr_specialist_count = State()
    documents_per_employee = State()
    pages_per_document = State()
    turnover_percentage = State()
    average_salary = State()
    courier_delivery_cost = State()
    hr_delivery_percentage = State()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_text = (
        'Приветствую!\n'
        'Это бот для расчёта выгоды от перехода на КЭДО\n'
        'Как будете готовы, напишите слово "начать".\n'
        'Введите "заново" чтобы начать сначала или "стоп" чтобы прекратить.'
    )
    await message.answer(text=user_text)


@dp.message(lambda message: message.text.lower() == 'начать')
async def start_form(message: Message, state: FSMContext):
    await message.answer("Название организации:")
    await state.set_state(Form.organization_name)


@dp.message(lambda message: message.text.lower() == 'заново')
async def restart_form(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Название организации:")
    await state.set_state(Form.organization_name)


@dp.message(lambda message: message.text.lower() == 'стоп')
async def stop_form(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы прекратили ввод данных.")


@dp.message(Form.organization_name)
async def process_organization_name(message: Message, state: FSMContext):
    await state.update_data(organization_name=message.text)
    await message.answer("Введите число сотрудников:")
    await state.set_state(Form.employee_count)


@dp.message(Form.employee_count)
async def process_employee_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите целое число.")
        return
    await state.update_data(employee_count=int(message.text))
    await message.answer("Введите число кадровых специалистов:")
    await state.set_state(Form.hr_specialist_count)


@dp.message(Form.hr_specialist_count)
async def process_hr_specialist_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите целое число.")
        return
    await state.update_data(hr_specialist_count=int(message.text))
    await message.answer("Сколько в среднем документов в год на сотрудника? (обычно около 30, укажите конкретно по Вашей организации)")
    await state.set_state(Form.documents_per_employee)


@dp.message(Form.documents_per_employee)
async def process_documents_per_employee(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите целое число.")
        return
    await state.update_data(documents_per_employee=int(message.text))
    await message.answer(
        "Сколько в среднем страниц в документе?\n"
        "Обычно это 1.5 документы, введите Ваше значение\n"
        "Для разделения чисел используйте точку."
        )
    await state.set_state(Form.pages_per_document)


@dp.message(Form.pages_per_document)
async def process_pages_per_document(message: Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(pages_per_document=value)
    await message.answer("Какая в Вашей организации текучка в процентах?")
    await state.set_state(Form.turnover_percentage)


@dp.message(Form.turnover_percentage)
async def process_turnover_percentage(message: Message, state: FSMContext):
    try:
        value = float(message.text.replace('%', '').strip())
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(turnover_percentage=value)
    await message.answer("Средняя зарплата сотрудника с учетом НДФЛ и налогов, руб.?")
    await state.set_state(Form.average_salary)


@dp.message(Form.average_salary)
async def process_average_salary(message: Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(average_salary=value)
    await message.answer("Сколько стоит 1 курьерская доставка? Укажите 0 если нет курьерских доставок.")
    await state.set_state(Form.courier_delivery_cost)


@dp.message(Form.courier_delivery_cost)
async def process_courier_delivery_cost(message: Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(courier_delivery_cost=value)
    if value > 0:
        await message.answer("Какой % от общего числа доставок занимает именно отправка кадровых документов?")
        await state.set_state(Form.hr_delivery_percentage)
    else:
        await save_data(message, state)


@dp.message(Form.hr_delivery_percentage)
async def process_hr_delivery_percentage(message: Message, state: FSMContext):
    try:
        value = float(message.text.replace('%', '').strip())
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(hr_delivery_percentage=value)
    await save_data(message, state)


async def save_data(message: Message, state: FSMContext):
    data = await state.get_data()
    session = Session()
    user_data = UserData(
        user_id=message.from_user.id,
        organization_name=data['organization_name'],
        employee_count=data['employee_count'],
        hr_specialist_count=data['hr_specialist_count'],
        documents_per_employee=data['documents_per_employee'],
        pages_per_document=data['pages_per_document'],
        turnover_percentage=data['turnover_percentage'],
        average_salary=data['average_salary'],
        courier_delivery_cost=data['courier_delivery_cost'],
        hr_delivery_percentage=data.get('hr_delivery_percentage', 0)
    )
    session.add(user_data)
    session.commit()
    session.close()

    # Расчеты
    documents_per_year = calculate_documents_per_year(data)
    pages_per_year = calculate_pages_per_year(data)
    total_paper_costs = calculate_total_paper_costs(pages_per_year)
    total_logistics_costs = calculate_total_logistics_costs(data, documents_per_year)
    cost_per_minute = calculate_cost_per_minute(data)
    total_operations_costs = calculate_total_operations_costs(data, documents_per_year, cost_per_minute)

    # Расчет суммы по использованию нашего решения
    session = Session()
    license_costs = session.query(LicenseCosts).first()
    session.close()
    total_license_costs = calculate_total_license_costs(data, license_costs)

    # Вывод результатов
    results = (
        f"Документов в год: {format_number(documents_per_year)}\n"
        f"Страниц в год: {format_number(pages_per_year)}\n"
        f"Итого расходы на бумагу: {format_number(total_paper_costs)} руб.\n"
        f"Итого расходы на логистику: {format_number(total_logistics_costs)} руб.\n"
        f"Стоимость минуты работника: {format_number(cost_per_minute)} руб.\n"
        f"Сумма трат на операции: {format_number(total_operations_costs)} руб.\n"
        f"Сумма текущих трат на КДП на бумаге: {format_number(total_paper_costs + total_logistics_costs + total_operations_costs)} руб.\n"
        f"Сумма по использованию нашего решения: {format_number(total_license_costs)} руб.\n"
        f"Сумма выгоды: {format_number(total_paper_costs + total_logistics_costs + total_operations_costs - total_license_costs)} руб."
    )
    await message.answer(results)

    await state.clear()


def calculate_documents_per_year(data):
    employee_count = data['employee_count']
    documents_per_employee = data['documents_per_employee']
    turnover_percentage = data['turnover_percentage']
    return employee_count * documents_per_employee * (1 + turnover_percentage / 100)


def calculate_pages_per_year(data):
    documents_per_year = calculate_documents_per_year(data)
    pages_per_document = data['pages_per_document']
    return documents_per_year * pages_per_document


def calculate_total_paper_costs(pages_per_year):
    session = Session()
    paper_costs = session.query(PaperCosts).first()
    session.close()
    return pages_per_year * (paper_costs.page_cost + paper_costs.printing_cost + paper_costs.storage_cost + paper_costs.rent_cost)


def calculate_total_logistics_costs(data, documents_per_year):
    courier_delivery_cost = data['courier_delivery_cost']
    hr_delivery_percentage = data.get('hr_delivery_percentage', 0)
    return courier_delivery_cost * hr_delivery_percentage / 100 * documents_per_year


def calculate_cost_per_minute(data):
    average_salary = data['average_salary']
    working_minutes_per_month = data.get('working_minutes_per_month', 10080)
    return average_salary / working_minutes_per_month


def calculate_total_operations_costs(data, documents_per_year, cost_per_minute):
    return cost_per_minute * documents_per_year


def calculate_total_license_costs(data, license_costs):
    employee_count = data['employee_count']
    hr_specialist_count = data['hr_specialist_count']
    if employee_count <= 500:
        employee_license_cost = 1000
    elif employee_count <= 1499:
        employee_license_cost = 900
    elif employee_count <= 5000:
        employee_license_cost = 850
    elif employee_count <= 10000:
        employee_license_cost = 800
    else:
        employee_license_cost = 750
    return (
        license_costs.main_license_cost +
        (license_costs.hr_license_cost * hr_specialist_count) +
        (employee_license_cost * employee_count)
    )


def format_number(value):
    return "{:,.2f}".format(value)


@dp.message()
async def echo(message: Message):
    user_text = (
        'Не могу обработать это\n'
        'Если Вы вводили команду, то повторите ввод\n'
        'Если Вы вводили число, потоврите, число должно быть без пробелов!'
    )
    await message.answer(user_text)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
