import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.types.input_file import FSInputFile
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext

from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, UserData, PaperCosts, LicenseCosts, TypicalOperations
from database import init_db

from decouple import Config, RepositoryEnv
from states import Form
from keyboards import get_keyboard, get_start_keyboard, get_contact_keyboard

from graph import generate_cost_graph

config = Config(RepositoryEnv('.env'))
BOT_TOKEN = config('BOT_TOKEN')
CHAT_ID = config('CHAT_ID')
# MAIL_P = config('MAIL_P')

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
init_db()

# Создаем подключение к базе данных
engine = create_engine('sqlite:///user_data.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_text = (
        'Приветствую!\n'
        'Это бот для расчёта <b>выгоды от перехода на КЭДО</b>\n'
        'Как будете готовы, нажмите кнопку <b>"Приступисть к расчётам"</b>.'
    )
    await message.answer(
        text=user_text, reply_markup=get_start_keyboard(),
        parse_mode=ParseMode.HTML)


@dp.callback_query(lambda c: c.data == "start_form")
async def start_form(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "<b>Название организации?</b>",
        reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
    await state.set_state(Form.organization_name)
    await state.update_data(user_id=callback_query.from_user.id)


@dp.message(lambda message: message.text.lower() == 'заново')
async def restart_form(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>Название организации?</b>",
        reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
    await state.set_state(Form.organization_name)
    await state.update_data(user_id=message.from_user.id)


@dp.message(lambda message: message.text.lower() == 'стоп')
async def stop_form(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Вы прекратили ввод данных."
        "Напишите /start для начала расчётов."
        )


@dp.message(Form.organization_name)
async def process_organization_name(message: Message, state: FSMContext):
    await state.update_data(organization_name=message.text)
    await message.answer(
        "Введите число сотрудников.",
        reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
    await state.set_state(Form.employee_count)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.employee_count)
async def process_employee_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите <b>целое число.</b>",
            reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
        return
    await state.update_data(employee_count=int(message.text))
    await message.answer(
        "Введите число <b>кадровых специалистов.</b>",
        reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
    await state.set_state(Form.hr_specialist_count)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.hr_specialist_count)
async def process_hr_specialist_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите <b>целое число.</b>",
            reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
        return
    await state.update_data(hr_specialist_count=int(message.text))
    await message.answer(
        "Сколько в среднем документов в год на сотрудника?\n"
        "Обычно около 30, укажите конкретно по Вашей организации.",
        reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
    await state.set_state(Form.documents_per_employee)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.documents_per_employee)
async def process_documents_per_employee(message: Message, state: FSMContext):
    try:
        value = float(message.text)
        if value <= 0:
            raise ValueError("Число должно быть положительным.")
    except ValueError:
        await message.answer(
            "Пожалуйста, введите положительное число.",
            reply_markup=get_keyboard()
        )
        return

    await state.update_data(documents_per_employee=int(value))
    await message.answer(
        "Сколько в среднем страниц в документе?\n"
        "Обычно это 2.1 страницы, введите Ваше значение\n"
        "Для разделения дробной части используйте точку.",
        reply_markup=get_keyboard()
    )
    await state.set_state(Form.pages_per_document)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.pages_per_document)
async def process_pages_per_document(message: Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer(
            "Пожалуйста, <b>введите число.</b>",
            reply_markup=get_keyboard(), parse_mode=ParseMode.HTML
        )
        return

    await state.update_data(pages_per_document=value)
    await message.answer(
        "Какая в Вашей организации <b>текучка в процентах?</b>\n"
        "Введите только целое число, знак <b>%</b> указывать не нужно.",
        reply_markup=get_keyboard(), parse_mode=ParseMode.HTML
    )
    await state.set_state(Form.turnover_percentage)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.turnover_percentage)
async def process_turnover_percentage(message: Message, state: FSMContext):
    try:
        value = float(message.text.replace('%', '').strip())
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число.",
            reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
        return
    await state.update_data(turnover_percentage=value)
    await message.answer(
        "Средняя зарплата сотрудника с учетом НДФЛ и налогов, руб.?",
        reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
    await state.set_state(Form.average_salary)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.average_salary)
async def process_average_salary(message: Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число.",
            reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
        return
    await state.update_data(average_salary=value)
    await message.answer(
        "Сколько стоит 1 курьерская доставка?\n"
        "Укажите 0 если нет курьерских доставок.",
        reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
    await state.set_state(Form.courier_delivery_cost)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.courier_delivery_cost)
async def process_courier_delivery_cost(message: Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число.",
            reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
        return
    await state.update_data(courier_delivery_cost=value)
    if value > 0:
        await message.answer(
            "Какой % от общего числа доставок занимает "
            "именно отправка кадровых документов?",
            reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
        await state.set_state(Form.hr_delivery_percentage)
    else:
        await save_data(message, state)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.hr_delivery_percentage)
async def process_hr_delivery_percentage(message: Message, state: FSMContext):
    try:
        value = float(message.text.replace('%', '').strip())
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число.",
            reply_markup=get_keyboard(), parse_mode=ParseMode.HTML)
        return
    await state.update_data(hr_delivery_percentage=value)
    await save_data(message, state)
    await state.update_data(user_id=message.from_user.id)


async def save_data(message: Message, state: FSMContext):
    data = await state.get_data()
    session = Session()

    # Проверка на количество записей для одного user_id
    user_data_entries = session.query(UserData).filter_by(user_id=message.from_user.id).all()
    if len(user_data_entries) >= 5:
        # Удаление самой старой записи
        oldest_entry = session.query(UserData).filter_by(user_id=message.from_user.id).order_by(UserData.timestamp.asc()).first()
        session.delete(oldest_entry)

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

    # Расчеты
    documents_per_year = calculate_documents_per_year(data)
    pages_per_year = calculate_pages_per_year(data)
    total_paper_costs = calculate_total_paper_costs(pages_per_year)
    total_logistics_costs = calculate_total_logistics_costs(data, documents_per_year)
    cost_per_minute = calculate_cost_per_minute(data)
    total_operations_costs = calculate_total_operations_costs(data, documents_per_year, cost_per_minute)

    # Расчет суммы по использованию нашего решения
    license_costs = session.query(LicenseCosts).first()
    total_license_costs = calculate_total_license_costs(data, license_costs)

    # Сохранение результатов расчетов в базе данных
    user_data.total_paper_costs = total_paper_costs
    user_data.total_logistics_costs = total_logistics_costs
    user_data.total_operations_costs = total_operations_costs
    user_data.total_license_costs = total_license_costs
    session.commit()

    # Вывод результатов
    results = (
        "<b>ЭТО ВАРИАНТ ТЕСТОВОЙ ИНФОРМАЦИИ ДЛЯ РАЗРАБОТКИ</b>\n"
        "\n"
        f"Документов в год: <b>{format_number(documents_per_year)}</b>\n"
        f"Страниц в год: <b>{format_number(pages_per_year)}</b>\n"
        "\n"
        f"Итого расходы на бумагу: <b>{format_number(total_paper_costs)}</b> руб.\n"
        "\n"
        f"Итого расходы на логистику: <b>{format_number(total_logistics_costs)}</b> руб.\n"
        "\n"
        f"Стоимость минуты работника: <b>{format_number(cost_per_minute)}</b> руб.\n"
        "\n"
        f"Сумма трат на операции:<b> {format_number(total_operations_costs)}</b> руб.\n"
        f"Сумма текущих трат на КДП на бумаге: <b>{format_number(total_paper_costs + total_logistics_costs + total_operations_costs)}</b> руб.\n"
        f"<b>Сумма КЭДО от HRlink: {format_number(total_license_costs)}</b> руб. "
        f"Сумма выгоды: <b>{format_number(total_paper_costs + total_logistics_costs + total_operations_costs - total_license_costs)}</b> руб."
    )

    user_text = (
        "<b>ВАРИАНТ ВЫВОДА ДЛЯ ПОЛЬЗОВАТЕЛЯ (КЛИЕНТА)</b>\n"
        "\n"
        f"<b>Сумма текущих трат на КДП на бумаге: {format_number(total_paper_costs + total_logistics_costs + total_operations_costs)}</b> руб.\n"
        "\n"
        f"Распечатывание, хранение документов: <b>{format_number(total_paper_costs)}</b>\n"
        f"Расходы на доставку документов: <b>{format_number(total_logistics_costs)}</b>\n"
        f"Расходы на оплату времени по работе с документами: <b>{format_number(total_operations_costs)}</b>\n"
        "\n"
        f"<b>Сумма КЭДО от HRlink: {format_number(total_license_costs)}</b> руб. \n"
        "\n"
        f"Сумма выгоды: <b>{format_number(total_paper_costs + total_logistics_costs + total_operations_costs - total_license_costs)}</b> руб."
    )

    # await message.answer(results, parse_mode=ParseMode.HTML)
    await message.answer(
        user_text, reply_markup=get_contact_keyboard(),
        parse_mode=ParseMode.HTML)

    # Генерация и отправка графика
    graph_path = generate_cost_graph(total_paper_costs, total_logistics_costs, total_operations_costs, total_license_costs)
    await message.answer_photo(FSInputFile(graph_path))

    # Удаление временного файла графика
    os.remove(graph_path)

    await state.clear()
    session.close()


@dp.callback_query(lambda c: c.data == "contact_me")
async def contact_me(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "<b>Как к вам обращаться?</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.contact_name)
    await state.update_data(user_id=callback_query.from_user.id)


@dp.message(Form.contact_name)
async def process_contact_name(message: Message, state: FSMContext):
    await state.update_data(contact_name=message.text)
    await message.answer(
        "<b>Номер телефона для связи?</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.contact_phone)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.contact_phone)
async def process_contact_phone(message: Message, state: FSMContext):
    await state.update_data(contact_phone=message.text)
    await message.answer(
        "<b>Электронная почта?</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.contact_email)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.contact_email)
async def process_contact_email(message: Message, state: FSMContext):
    await state.update_data(contact_email=message.text)
    await message.answer(
        "<b>Какой канал связи предпочитаете? Почта, мессенджер, звонок.</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.contact_preference)
    await state.update_data(user_id=message.from_user.id)


@dp.message(Form.contact_preference)
async def process_contact_preference(message: Message, state: FSMContext):
    await state.update_data(contact_preference=message.text)
    await message.answer(
        "<b>Спасибо, данные записали и передали менеджеру, с Вами скоро свяжутся.</b>",
        reply_markup=get_start_keyboard(), parse_mode=ParseMode.HTML)
    await send_contact_data(state)
    await state.clear()


def calculate_documents_per_year(data):
    employee_count = data['employee_count']
    documents_per_employee = data['documents_per_employee']
    turnover_percentage = data['turnover_percentage']
    return employee_count * (documents_per_employee * (1 + turnover_percentage / 100))


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
    return courier_delivery_cost * (hr_delivery_percentage / 100 * documents_per_year)


def calculate_cost_per_minute(data):
    average_salary = data['average_salary']
    working_minutes_per_month = data.get('working_minutes_per_month', 10080)
    return average_salary / working_minutes_per_month


def calculate_total_operations_costs(data, documents_per_year, cost_per_minute):
    session = Session()
    typical_operations = session.query(TypicalOperations).first()
    session.close()

    if not typical_operations:
        raise ValueError("Нет данных.")

    # Стоимость каждой операции в минутах
    time_of_printing = typical_operations.time_of_printing
    time_of_signing = typical_operations.time_of_signing
    time_of_archiving = typical_operations.tome_of_archiving

    # Общая стоимость всех операций за год
    total_operations_costs = (
        (time_of_printing + time_of_signing + time_of_archiving) *
        cost_per_minute * documents_per_year
    )

    return total_operations_costs


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


async def send_contact_data(state: FSMContext):
    data = await state.get_data()
    if 'user_id' not in data:
        raise KeyError("user_id is missing in state data")

    # Получение данных из базы данных
    session = Session()
    user_data_entries = session.query(UserData).filter_by(user_id=data['user_id']).all()
    session.close()

    # Формирование сообщения с данными из базы данных
    user_data_info = "\n".join([
        f"<b>Организация:</b> {entry.organization_name}\n"
        f"<b>Число сотрудников:</b> {entry.employee_count}\n"
        f"<b>Число кадровых специалистов:</b> {entry.hr_specialist_count}\n"
        f"<b>Документов в год на сотрудника:</b> {entry.documents_per_employee}\n"
        f"<b>Страниц в документе:</b> {entry.pages_per_document}\n"
        f"<b>Текучка в процентах:</b> {entry.turnover_percentage}\n"
        f"<b>Средняя зарплата:</b> {entry.average_salary}\n"
        f"<b>Стоимость курьерской доставки:</b> {entry.courier_delivery_cost}\n"
        f"<b>Процент отправки кадровых документов:</b> {entry.hr_delivery_percentage}\n"
        "\n"
        f"<b>Сумма текущих трат на КДП на бумаге:</b> {format_number(entry.total_paper_costs + entry.total_logistics_costs + entry.total_operations_costs) if entry.total_paper_costs is not None and entry.total_logistics_costs is not None and entry.total_operations_costs is not None else 'Неизвестно'} руб.\n"
        f"<b>Сумма КЭДО от HRlink:</b> {format_number(entry.total_license_costs) if entry.total_license_costs is not None else 'Неизвестно'} руб.\n"
        "\n"
        f"<b>Время расчета:</b> {entry.timestamp}\n"
        "______________________________\n"
        for entry in user_data_entries
    ])

    # Разделение сообщения на части
    max_message_length = 4096  # Максимальная длина сообщения в Telegram
    messages = [user_data_info[i:i + max_message_length] for i in range(0, len(user_data_info), max_message_length)]

    contact_info = (
        "<b>КЛИЕНТ ОСТАВИЛ ЗАЯВКУ</b>\n"
        f"<b>Имя:</b> {data['contact_name']}\n"
        f"<b>Телефон:</b> <code>+{data['contact_phone']}</code>\n"
        f"<b>Email:</b> <code>{data['contact_email']}</code>\n"
        f"<b>Предпочтительный канал связи:</b> {data['contact_preference']}\n"
    )

    await bot.send_message(chat_id=CHAT_ID, text=contact_info, parse_mode=ParseMode.HTML)
    for message in messages:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.HTML)

@dp.message()
async def echo(message: Message):
    user_text = (
        'Не могу обработать это\n'
        'Если Вы вводили команду, то повторите ввод\n'
        'Если Вы вводили число, потоврите, число должно быть без пробелов!'
    )
    await message.answer(
        user_text, reply_markup=get_start_keyboard(),
        parse_mode=ParseMode.HTML)


@dp.callback_query(lambda c: c.data in ["restart", "stop"])
async def process_callback(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "restart":
        await restart_form(callback_query.message, state)
    elif callback_query.data == "stop":
        await stop_form(callback_query.message, state)


def format_number(value):
    return "{:,.0f}".format(value).replace(',', ' ')


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
