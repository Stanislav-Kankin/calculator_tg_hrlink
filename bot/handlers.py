from aiogram import Dispatcher, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.types.input_file import FSInputFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import UserData, LicenseCosts
from states import Form
from keyboards import (
    get_keyboard, get_start_keyboard,
    get_contact_keyboard, get_license_type_keyboard, get_confirmation_keyboard,
    get_retry_keyboard
)
from calculations import (
    calculate_documents_per_year, calculate_pages_per_year,
    calculate_total_paper_costs, calculate_total_logistics_costs,
    calculate_cost_per_minute, calculate_total_operations_costs,
    calculate_total_license_costs
)
from decouple import Config, RepositoryEnv
from graph import generate_cost_graph
import os
import logging
import re

config = Config(RepositoryEnv('.env'))
BOT_TOKEN = config('BOT_TOKEN')
CHAT_ID = config('CHAT_ID')
bot = Bot(token=BOT_TOKEN)

engine = create_engine('sqlite:///user_data.db')
Session = sessionmaker(bind=engine)


def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())
    dp.callback_query.register(start_form, lambda c: c.data == "start_form")
    dp.message.register(
        restart_form, lambda message: message.text.lower() == 'заново')
    dp.message.register(
        stop_form, lambda message: message.text.lower() == 'стоп')
    dp.callback_query.register(
        process_license_type, lambda c: c.data in [
            "simple_kedo", "standard_kedo"
            ])
    dp.message.register(process_hr_specialist_count, Form.hr_specialist_count)
    dp.message.register(process_organization_name, Form.organization_name)
    dp.message.register(process_employee_count, Form.employee_count)
    dp.message.register(
        process_documents_per_employee, Form.documents_per_employee)
    dp.message.register(process_pages_per_document, Form.pages_per_document)
    dp.message.register(process_turnover_percentage, Form.turnover_percentage)
    dp.message.register(process_average_salary, Form.average_salary)
    dp.message.register(
        process_courier_delivery_cost, Form.courier_delivery_cost)
    dp.message.register(
        process_hr_delivery_percentage, Form.hr_delivery_percentage)
    dp.callback_query.register(contact_me, lambda c: c.data == "contact_me")
    dp.message.register(process_contact_name, Form.contact_name)
    dp.message.register(process_contact_phone, Form.contact_phone)
    dp.message.register(process_contact_email, Form.contact_email)
    dp.message.register(process_contact_preference, Form.contact_preference)
    dp.message.register(echo)
    dp.callback_query.register(
        process_callback, lambda c: c.data in ["restart", "stop", "confirm"])


async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Имя пользователя не задано"

    session = Session()
    user_exists = session.query(UserData).filter_by(user_id=user_id).first()
    session.close()

    if not user_exists:
        try:
            await send_new_user_notification(user_id, username)
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления: {e}")

    user_text = (
        "Здравствуйте!\n"
        "Это бот для расчета финансовой выгоды перехода на КЭДО 💰\n"
        "Ответьте на несколько вопросов о КДП в вашей компании, "
        "и бот посчитает разницу между бумажным и "
        "электронным кадровым документооборотом."
    )
    await message.answer(
        text=user_text, reply_markup=get_start_keyboard(),
        parse_mode=ParseMode.HTML)


async def start_form(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "<b>Сколько сотрудников работает в вашей компании?</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.employee_count)
    await state.update_data(user_id=callback_query.from_user.id)


async def restart_form(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>Сколько сотрудников работает в вашей компании?</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.employee_count)
    await state.update_data(user_id=message.from_user.id)


async def stop_form(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Вы прекратили ввод данных."
        "Напишите /start для начала расчётов."
        )


async def process_employee_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите <b>целое число.</b>",
            parse_mode=ParseMode.HTML)
        return

    employee_count = int(message.text)
    await state.update_data(employee_count=employee_count)

    if 0 < employee_count <= 499:
        await message.answer(
            "Какой вариант КЭДО вам больше подходит:\n"
            "\n"
            "<b><u>HRlink Lite</u> - для простых кадровых процессов:</b>\n"
            "- интеграции с «1С:ЗУП» и «1С:Фреш»;\n"
            "- уведомления через Telegram или почту;\n"
            "- облачное размещение;\n"
            "- сопровождение через службу заботы.\n"
            "\n"
            "<b><u>HRlink Standard</u> - для кадровых процессов </b>"
            "<b>с нетиповыми маршрутами</b> "
            "<b>и большим количеством интеграций:</b>\n"
            "- интеграции с «1С», «Битрикс24», «БОСС-Кадровик», SAP;\n"
            "- уведомления через Telegram, почту и СМС;\n"
            "- возможность доработок после внедрения;\n"
            "- размещение на сервере;\n"
            "- персональное сопровождение.\n"
            "\n"
            "<b>Используйте кнопки внизу сообщения.</b>",
            reply_markup=get_license_type_keyboard(),
            parse_mode=ParseMode.HTML)
        await state.set_state(Form.license_type)
    elif 500 <= employee_count <= 1999:
        await state.update_data(
            license_type="standard", employee_license_cost=700)
        await message.answer(
            "<b>Сколько кадровых специалистов в вашей компании?</b>",
            parse_mode=ParseMode.HTML)
        await state.set_state(Form.hr_specialist_count)
    elif employee_count >= 2000:
        await state.update_data(
            license_type="enterprise", employee_license_cost=600)
        await message.answer(
            "<b>Сколько кадровых специалистов в вашей компании?</b>",
            parse_mode=ParseMode.HTML)
        await state.set_state(Form.hr_specialist_count)
    else:
        await message.answer(
            "Пожалуйста, введите корректное количество сотрудников.",
            parse_mode=ParseMode.HTML)


async def process_license_type(
        callback_query: CallbackQuery, state: FSMContext):
    license_type = "lite" if callback_query.data == "simple_kedo" else "standard"
    await state.update_data(license_type=license_type)

    if license_type == "lite":
        employee_license_cost = 500
        tariff_name = "HRlink Lite"
    else:
        employee_license_cost = 700
        tariff_name = "HRlink Standard"

    await state.update_data(employee_license_cost=employee_license_cost)
    await state.update_data(tariff_name=tariff_name)

    await callback_query.message.answer(
        "<b>Сколько кадровых специалистов в вашей компании?</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.hr_specialist_count)


async def process_hr_specialist_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(
            "Пожалуйста, введите <b>целое число.</b>",
            parse_mode=ParseMode.HTML)
        return
    await state.update_data(hr_specialist_count=int(message.text))
    await message.answer(
        "Сколько в среднем документов подписывает сотрудник за год?\n"
        "Обычно это около 30 документов.\n"
        "Укажите число, актуальное для вашей компании.",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.documents_per_employee)


async def process_documents_per_employee(message: Message, state: FSMContext):
    try:
        value = float(message.text)
        if value <= 0:
            raise ValueError("Число должно быть положительным.")
    except ValueError:
        await message.answer(
            "Пожалуйста, введите положительное число."
        )
        return

    await state.update_data(documents_per_employee=int(value))
    await message.answer(
        "Сколько в среднем страниц в каждом документе?\n"
        "Обычно это 1,5 страницы.  Укажите число, "
        "актуальное для вашей компании.",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(Form.pages_per_document)


async def process_pages_per_document(message: Message, state: FSMContext):
    try:
        # Заменяем запятую на точку, если пользователь ввел запятую
        value = float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer(
            "Пожалуйста, <b>введите число c точкой или запятой.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    await state.update_data(pages_per_document=value)
    await message.answer(
        "Какой <b>процент текучки</b> в вашей организации?\n"
        "Введите целое число, знак «%» указывать не нужно.",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(Form.turnover_percentage)


async def process_turnover_percentage(message: Message, state: FSMContext):
    try:
        value = float(message.text.replace('%', '').strip())
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число.",
            parse_mode=ParseMode.HTML)
        return
    await state.update_data(turnover_percentage=value)
    await message.answer(
        "Какая средняя ежемесячная зарплата сотрудников "
        "отдела кадров с учетом налогов?\n"
        "\n"
        "Данные нужны <b>для точного расчета времени</b>, "
        "которое сотрудники отдела кадров тратят на работу "
        "с бумажными документами, и не будут переданы или "
        "использованы вне этого бота. Вы можете сократить "
        "это время и освободить специалистов для "
        "выполнения других задач.\n"
        "В ответе укажите целое число",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.average_salary)


async def process_average_salary(message: Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число.",
            parse_mode=ParseMode.HTML)
        return
    await state.update_data(average_salary=value)
    await message.answer(
        "Сколько в среднем стоит одна курьерская "
        "доставка документов?\n"
        "Введите 0, если нет курьерских доставок",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.courier_delivery_cost)


async def process_courier_delivery_cost(message: Message, state: FSMContext):
    try:
        value = float(message.text)
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число.",
            parse_mode=ParseMode.HTML)
        return

    await state.update_data(courier_delivery_cost=value)

    if value > 0:
        await message.answer(
            "Какой процент от общего числа "
            "курьерских доставок занимает отправка кадровых документов?\n"
            "Введите целое число, знак «%» указывать не нужно.",
            parse_mode=ParseMode.HTML)
        await state.set_state(Form.hr_delivery_percentage)
    else:
        # Если стоимость доставки равна 0, пропускаем вопрос о проценте отправки
        await state.update_data(hr_delivery_percentage=0)  # Устанавливаем значение по умолчанию
        await save_data(message, state, bot)  # Сохраняем данные


async def process_hr_delivery_percentage(message: Message, state: FSMContext):
    try:
        value = float(message.text.replace('%', '').strip())
    except ValueError:
        await message.answer(
            "Пожалуйста, введите число.",
            parse_mode=ParseMode.HTML)
        return
    await state.update_data(hr_delivery_percentage=value)
    await state.update_data(user_id=message.from_user.id)

    # Вызываем save_data только после ввода всех данных
    await save_data(message, state, bot)


async def save_data(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    session = Session()

    # Проверка на количество записей для одного user_id
    user_data_entries = session.query(UserData).filter_by(
        user_id=message.from_user.id).all()
    if len(user_data_entries) >= 5:
        # Удаление самой старой записи
        oldest_entry = session.query(UserData).filter_by(
            user_id=message.from_user.id).order_by(
                UserData.timestamp.asc()).first()
        session.delete(oldest_entry)

    # Устанавливаем значение по умолчанию для organization_name
    organization_name = data.get('organization_name', 'Не указано')

    user_data = UserData(
        user_id=message.from_user.id,
        organization_name=organization_name,  # Используем значение по умолчанию
        employee_count=data['employee_count'],
        hr_specialist_count=data['hr_specialist_count'],
        license_type=data.get('license_type', 'standard'),
        documents_per_employee=data['documents_per_employee'],
        pages_per_document=data['pages_per_document'],
        turnover_percentage=data['turnover_percentage'],
        average_salary=data['average_salary'],
        courier_delivery_cost=data['courier_delivery_cost'],
        hr_delivery_percentage=data.get('hr_delivery_percentage', 0)
    )

    session.add(user_data)
    session.commit()

    # Проверяем, все ли данные введены
    if 'hr_delivery_percentage' in data:
        # Расчеты
        documents_per_year = calculate_documents_per_year(data)
        pages_per_year = calculate_pages_per_year(data)
        total_paper_costs = calculate_total_paper_costs(pages_per_year)
        total_logistics_costs = calculate_total_logistics_costs(
            data, documents_per_year)
        cost_per_minute = calculate_cost_per_minute(data)
        total_operations_costs = calculate_total_operations_costs(
            data, documents_per_year, cost_per_minute)

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
            f"<b>Число сотрудников:</b> {data['employee_count']}\n"
            f"<b>Число кадровых специалистов:</b> {data['hr_specialist_count']}\n"
            f"<b>Документов в год на сотрудника:</b> {
                data['documents_per_employee']}\n"
            f"<b>Страниц в документе:</b> {data['pages_per_document']}\n"
            f"<b>Текучка в процентах:</b> {data['turnover_percentage']}%\n"
            f"<b>Средняя зарплата:</b> {data['average_salary']} руб.\n"
            f"<b>Стоимость курьерской доставки:</b> {
                data['courier_delivery_cost']} руб.\n"
            f"<b>Процент отправки кадровых документов:</b> {
                data.get('hr_delivery_percentage', 0)}%\n"
            "<b>Подходящий тариф:</b> "
            f"<u>{get_tariff_name(data)}</u>\n"
        )
        await message.answer(
            f"<b>Вы ввели следующие данные:</b>\n{results}",
            reply_markup=get_confirmation_keyboard(),
            parse_mode=ParseMode.HTML)
    else:
        # Если данные ещё не полные, просто сохраняем их
        session.commit()

    session.close()


async def contact_me(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "<b>Как вас зовут?</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.contact_name)
    await state.update_data(user_id=callback_query.from_user.id)


async def process_contact_name(message: Message, state: FSMContext):
    await state.update_data(contact_name=message.text)
    await message.answer(
        "<b>Укажите номер телефона для связи</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.contact_phone)


async def process_contact_phone(message: Message, state: FSMContext):
    await state.update_data(contact_phone=message.text)
    await message.answer(
        "<b>Укажите электронную почту</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.contact_email)


async def process_contact_email(message: Message, state: FSMContext):
    await state.update_data(contact_email=message.text)
    await message.answer(
        "<b>Укажите название вашей компании</b>",
        parse_mode=ParseMode.HTML)
    await state.set_state(Form.organization_name)


async def process_contact_preference(message: Message, state: FSMContext):
    await state.update_data(contact_preference=message.text)
    await message.answer(
        "Спасибо, передали информацию менеджеру, "
        "свяжемся с вами в ближайшее время 💙",
        reply_markup=get_retry_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await send_contact_data(state)
    await state.clear()


async def process_organization_name(message: Message, state: FSMContext):
    await state.update_data(organization_name=message.text)
    await message.answer(
        "<b>Спасибо, данные записали и передали менеджеру, "
        "свяжемся с Вами в ближайшее время❤.</b>",
        reply_markup=get_start_keyboard(), parse_mode=ParseMode.HTML)
    await send_contact_data(state)
    await state.clear()


async def send_contact_data(state: FSMContext):
    data = await state.get_data()
    if 'user_id' not in data:
        raise KeyError("user_id is missing in state data")

    # Проверяем, все ли данные заполнены
    required_fields = [
        'contact_name', 'contact_phone', 'contact_email', 'organization_name'
    ]
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        # Если какие-то поля отсутствуют, уведомляем пользователя
        missing_fields_text = ", ".join(missing_fields)
        await bot.send_message(
            chat_id=data['user_id'],
            text=f"<b>Не заполнены следующие поля:</b> {missing_fields_text}.\n"
                 "Пожалуйста, заполните все поля, чтобы "
                 "оставить заявку на обратный звонок.",
            parse_mode=ParseMode.HTML
        )
        return

    # Получение данных из базы данных
    session = Session()
    user_data_entries = session.query(UserData).filter_by(
        user_id=data['user_id']).order_by(UserData.timestamp.desc()).all()
    session.close()

    # Формирование сообщения с данными из базы данных
    if user_data_entries:
        latest_entry = user_data_entries[0]  # Берем последнюю запись
        user_data_info = (
            f"<b>Тип лицензии:</b> <u>{get_tariff_name(data)}</u>\n"
            f"<b>Число сотрудников:</b> {latest_entry.employee_count}\n"
            f"<b>Число кадровых специалистов:</b> {
                latest_entry.hr_specialist_count}\n"
            f"<b>Документов в год на сотрудника:</b> {
                latest_entry.documents_per_employee}\n"
            f"<b>Страниц в документе:</b> {latest_entry.pages_per_document}\n"
            f"<b>Текучка в процентах:</b> {
                latest_entry.turnover_percentage}%\n"
            f"<b>Средняя зарплата:</b> {latest_entry.average_salary} руб.\n"
            f"<b>Стоимость курьерской доставки:</b> {
                latest_entry.courier_delivery_cost} руб.\n"
            f"<b>Процент отправки кадровых документов:</b> {
                latest_entry.hr_delivery_percentage}%\n"
            f"<b>Сумма текущих трат на КДП на бумаге:</b> {
                format_number(
                    latest_entry.total_paper_costs + latest_entry.total_logistics_costs +
                    latest_entry.total_operations_costs
                    ) if latest_entry.total_paper_costs is not None and latest_entry.total_logistics_costs is not None and latest_entry.total_operations_costs is not None else 'Неизвестно'} руб.\n"
            f"<b>Сумма КЭДО от HRlink:</b> {
                format_number(
                    latest_entry.total_license_costs
                    ) if latest_entry.total_license_costs is not None else 'Неизвестно'} руб.\n"
            f"<b>Время расчета:</b> {latest_entry.timestamp}\n"
        )
    else:
        user_data_info = "<b>Данные о расчетах отсутствуют.</b>"

    # Формирование первого сообщения с контактной информацией
    contact_info = (
        "<b>КЛИЕНТ ОСТАВИЛ ЗАЯВКУ</b>\n"
        f"<b>Имя:</b> {data['contact_name']}\n"
        f"<b>Телефон:</b> <code>+{data['contact_phone']}</code>\n"
        f"<b>Email:</b> <code>{data['contact_email']}</code>\n"
        f"<b>Название компании:</b> {data['organization_name']}\n"
        f"<b>Тип лицензии:</b> <u>{get_tariff_name(data)}</u>\n"
    )

    # Отправка сообщений
    await bot.send_message(
        chat_id=CHAT_ID, text=contact_info,
        parse_mode=ParseMode.HTML)
    await bot.send_message(
        chat_id=CHAT_ID, text=user_data_info,
        parse_mode=ParseMode.HTML)


async def process_callback(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == "restart":
        await restart_form(callback_query.message, state)
    elif callback_query.data == "stop":
        await stop_form(callback_query.message, state)
    elif callback_query.data == "confirm":
        await confirm_data(callback_query.message, state)


async def confirm_data(message: Message, state: FSMContext):
    data = await state.get_data()
    session = Session()

    # Расчеты
    documents_per_year = calculate_documents_per_year(data)
    pages_per_year = calculate_pages_per_year(data)
    total_paper_costs = calculate_total_paper_costs(pages_per_year)
    total_logistics_costs = calculate_total_logistics_costs(
        data, documents_per_year)
    cost_per_minute = calculate_cost_per_minute(data)
    total_operations_costs = calculate_total_operations_costs(
        data, documents_per_year, cost_per_minute)

    # Расчет суммы по использованию нашего решения
    license_costs = session.query(LicenseCosts).first()
    total_license_costs = calculate_total_license_costs(data, license_costs)

    # Вывод результатов
    user_text1 = (
        "<b>ОСНОВНЫЕ ВЫВОДЫ ПО ВВЕДЕННЫМ ДАННЫМ</b>\n"
        "\n"
        f"<b>Ваши расходы на бумажное КДП: {
            format_number(
                total_paper_costs + total_logistics_costs +
                total_operations_costs
                )
                }</b> руб.\n"
        "\n"
        f"Печать и хранение кадровых документов: <b>{
            format_number(total_paper_costs)}</b> руб.\n"
        f"Доставка кадровых документов: <b>{
            format_number(total_logistics_costs)}</b> руб.\n"
        "Оплата времени кадрового специалиста, "
        f"которое он тратит на работу с документами: <b>{
            format_number(total_operations_costs)}</b> руб.\n"
        "\n"
        )

    user_text2 = (
        f"Внедрив КЭДО от HRlink, вы сможете сэкономить <b>{
            format_number(
                total_paper_costs + total_logistics_costs +
                total_operations_costs - total_license_costs)}</b> руб. "
        f"<b>Стоимость HRlink для вашей компании от: {
            format_number(total_license_costs)}</b> руб. \n"
        "<u><i>Стоимость решения КЭДО от HRlink в месяц от:</i></u> "
        f"<b>{format_number(total_license_costs / 12)}</b>руб.\n"
        "\n"
        "Точная цена рассчитывается менеджером индивидуально для каждого клиента."
        "\n"
        "Вы получите:\n"
        "\n"
        "— множество интеграций с учетными системами и не только;\n"
        "— найм и работу с сотрудниками, самозанятыми и по ГПХ;\n"
        "— легитимное подписание и хранение документов;\n"
        "— удобный личный кабинет сотрудника;\n"
        "— гибкие маршруты и процессы;\n"
        "— все виды электронных подписей."
    )

    # Добавляем информацию о тарифе и цене лицензии
    tariff_name = get_tariff_name(data)
    employee_license_cost = data.get("employee_license_cost", 700)
    user_text2 += (
        f"\n\n<b>Рекомендуемый тариф:</b> {tariff_name}\n"
        f"<b>Цена лицензии сотрудника от:</b> {employee_license_cost} руб."
    )

    # Генерация и отправка графика
    graph_path = generate_cost_graph(
        total_paper_costs, total_logistics_costs,
        total_operations_costs, total_license_costs
    )
    await message.answer_photo(FSInputFile(graph_path))

    # Удаление временного файла графика
    os.remove(graph_path)

    # Вывод основных выводов
    await message.answer(user_text1, parse_mode=ParseMode.HTML)
    await message.answer(user_text2, parse_mode=ParseMode.HTML)

    await message.answer(
        "Оставьте <b>заявку</b>, и мы расскажем о возможностях "
        "КЭДО-платформы HRlink, поможем обосновать внедрение "
        "перед руководителем и ответим на ваши вопросы.",
        reply_markup=get_contact_keyboard(),
        parse_mode=ParseMode.HTML
    )

    await state.clear()
    session.close()


async def echo(message: Message):
    user_text = (
        'Не могу обработать это\n'
        'Если Вы вводили команду, то повторите ввод\n'
        'Если Вы вводили число, потоврите, число должно быть без пробелов!'
    )
    await message.answer(
        user_text, reply_markup=get_start_keyboard(),
        parse_mode=ParseMode.HTML)


async def send_new_user_notification(user_id: int, username: str):
    notification_text = (
        f"Новый пользователь начал пользоваться ботом:\n"
        f"ID: {user_id}\n"
        f"Username: {username}"
    )
    await bot.send_message(chat_id=CHAT_ID, text=notification_text)


def format_number(value):
    return "{:,.0f}".format(value).replace(',', ' ')


def get_tariff_name(data):
    license_type = data.get('license_type', 'standard')
    if license_type == 'lite':
        return "HRlink Lite"
    elif license_type == 'standard':
        return "HRlink Standard"
    elif license_type == 'enterprise':
        return "HRlink Enterprise"
    else:
        return "HRlink Standard"  # По умолчанию