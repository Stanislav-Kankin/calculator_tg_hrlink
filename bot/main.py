import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, UserData

from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Создаем подключение к базе данных
engine = create_engine('sqlite:///user_data.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


class Form(StatesGroup):
    organization_name = State()
    employee_count = State()
    hr_specialist_count = State()
    documents_per_employee = State()
    turnover_percentage = State()
    working_minutes_per_month = State()
    average_salary = State()
    courier_delivery_cost = State()
    hr_delivery_percentage = State()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_text = (
        'Приветствую!\n'
        'Это бот для расчёта выгоды от перехода на КЭДО\n'
        'Как будете готовы, напишите слово "начать".'
    )
    await message.answer(text=user_text)


@dp.message(lambda message: message.text.lower() == 'начать')
async def start_form(message: Message, state: FSMContext):
    await message.answer("Название организации:")
    await state.set_state(Form.organization_name)


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
    await message.answer("Сколько рабочих минут в месяце? (обычно это 10080 минут)")
    await state.set_state(Form.working_minutes_per_month)


@dp.message(Form.working_minutes_per_month)
async def process_working_minutes_per_month(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите целое число.")
        return
    await state.update_data(working_minutes_per_month=int(message.text))
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
        turnover_percentage=data['turnover_percentage'],
        working_minutes_per_month=data['working_minutes_per_month'],
        average_salary=data['average_salary'],
        courier_delivery_cost=data['courier_delivery_cost'],
        hr_delivery_percentage=data.get('hr_delivery_percentage', 0)
    )
    session.add(user_data)
    session.commit()
    session.close()
    await message.answer("Спасибо за предоставленные данные!")
    await state.clear()


@dp.message()
async def echo(message: Message):
    await message.answer('Это неизвестная команда.')


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
