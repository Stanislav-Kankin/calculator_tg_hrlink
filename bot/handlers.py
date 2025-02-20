from aiogram import Dispatcher, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.types.input_file import FSInputFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import UserData, LicenseCosts
from states import Form
from keyboards import (
    get_start_keyboard, get_contact_keyboard,
    get_license_type_keyboard, get_confirmation_keyboard,
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
import aiohttp
import re
from datetime import datetime, timedelta
from broadcast import send_broadcast
import logging

config = Config(RepositoryEnv('.env'))
BOT_TOKEN = config('BOT_TOKEN')
CHAT_ID = config('CHAT_ID')
bot = Bot(token=BOT_TOKEN)

engine = create_engine('sqlite:///user_data.db')
Session = sessionmaker(bind=engine)


def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_users, Command("users"))
    dp.message.register(cmd_broadcast, Command("broadcast"))

    dp.callback_query.register(
        process_users_day, lambda c: c.data == "users_day"
        )
    dp.callback_query.register(
        process_users_week, lambda c: c.data == "users_week"
        )
    dp.callback_query.register(
        process_users_month, lambda c: c.data == "users_month"
        )
    dp.callback_query.register(
        process_users_quarter, lambda c: c.data == "users_quarter"
        )
    dp.callback_query.register(
        process_users_year, lambda c: c.data == "users_year"
        )

    dp.message.register(process_day_input, StateFilter(
        Form.waiting_for_day))
    dp.message.register(process_week_input, StateFilter(
        Form.waiting_for_week))
    dp.message.register(process_month_input, StateFilter(
        Form.waiting_for_month))
    dp.message.register(process_quarter_input, StateFilter(
        Form.waiting_for_quarter))
    dp.message.register(process_year_input, StateFilter(
        Form.waiting_for_year))
    dp.callback_query.register(start_form, lambda c: c.data == "start_form")
    dp.message.register(
        restart_form, lambda message: message.text.lower() == 'заново')
    dp.message.register(
        stop_form, lambda message: message.text.lower() == 'стоп')
    dp.callback_query.register(
        process_license_type, lambda c: c.data in [
            "simple_kedo", "standard_kedo"
            ])
    dp.message.register(
        process_hr_specialist_count, StateFilter(Form.hr_specialist_count))
    dp.message.register(
        process_organization_name, StateFilter(Form.organization_name))
    dp.message.register(process_employee_count, StateFilter(
        Form.employee_count))
    dp.message.register(
        process_documents_per_employee, StateFilter(
            Form.documents_per_employee))
    dp.message.register(process_pages_per_document, StateFilter(
        Form.pages_per_document))
    dp.message.register(process_turnover_percentage, StateFilter(
        Form.turnover_percentage))
    dp.message.register(process_average_salary, StateFilter(
        Form.average_salary))
    dp.message.register(
        process_courier_delivery_cost, StateFilter(
            Form.courier_delivery_cost))
    dp.message.register(
        process_hr_delivery_percentage, StateFilter(
            Form.hr_delivery_percentage))
    dp.callback_query.register(contact_me, lambda c: c.data == "contact_me")
    dp.message.register(process_contact_name, StateFilter(Form.contact_name))
    dp.message.register(process_contact_phone, StateFilter(Form.contact_phone))
    dp.message.register(process_contact_email, StateFilter(Form.contact_email))
    dp.message.register(process_contact_preference, StateFilter(
        Form.contact_preference))
    dp.message.register(echo)
    dp.callback_query.register(
        process_callback, lambda c: c.data in ["restart", "stop", "confirm"])


async def cmd_broadcast(message: Message):
    await send_broadcast(bot)  # Передаем экземпляр bot напрямую


async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Имя пользователя не задано"
    print(
        f"Пользователь нажал /start. user_id: {user_id}, username: {username}"
        )
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
        "Ответьте на несколько вопросов о КДП в вашей компании, и"
        " бот посчитает разницу между бумажным и электронным "
        "кадровым документооборотом 💰\n"
    )
    await message.answer(
        text=user_text, reply_markup=get_start_keyboard(),
        parse_mode=ParseMode.HTML)


async def cmd_users(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="День", callback_data="users_day")],
        [InlineKeyboardButton(text="Неделя", callback_data="users_week")],
        [InlineKeyboardButton(text="Месяц", callback_data="users_month")],
        [InlineKeyboardButton(text="Квартал", callback_data="users_quarter")],
        [InlineKeyboardButton(text="Год", callback_data="users_year")]
    ])

    await message.answer(
        "Выберите период для отображения статистики:",
        reply_markup=keyboard
    )


async def process_users_day(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Введите дату в формате ДД.ММ.ГГГГ:")
    await state.set_state(Form.waiting_for_day)


async def process_day_input(message: Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(selected_date=date)

        session = Session()
        users_count = session.query(UserData).filter(
            UserData.timestamp >= date,
            UserData.timestamp < date + timedelta(days=1)
        ).distinct(UserData.user_id).count()
        session.close()

        await message.answer(
            f"Количество уникальных пользователей за {
                date.strftime('%d.%m.%Y')
                }: {users_count}"
            )
        await state.clear()
    except ValueError:
        await message.answer(
            "Некорректный формат даты. Введите дату в формате ДД.ММ.ГГГГ:"
            )


async def process_users_week(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Введите номер недели и год в формате НН.ГГГГ:"
        )
    await state.set_state(Form.waiting_for_week)


async def process_week_input(message: Message, state: FSMContext):
    try:
        week, year = map(int, message.text.split('.'))
        start_of_week = datetime.fromisocalendar(year, week, 1)
        end_of_week = start_of_week + timedelta(weeks=1)

        session = Session()
        users_count = session.query(UserData).filter(
            UserData.timestamp >= start_of_week,
            UserData.timestamp < end_of_week
        ).distinct(UserData.user_id).count()
        session.close()

        await message.answer(
            f"Количество уникальных пользователей за {week} "
            f"неделю {year} года: {users_count}"
            )
        await state.clear()
    except (ValueError, IndexError):
        await message.answer(
            "Некорректный формат. Введите номер "
            "недели и год в формате НН.ГГГГ:"
            )


async def process_users_month(
        callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "Введите месяц и год в формате ММ.ГГГГ:")
    await state.set_state(Form.waiting_for_month)


async def process_month_input(message: Message, state: FSMContext):
    try:
        month, year = map(int, message.text.split('.'))
        if month < 1 or month > 12:
            raise ValueError("Номер месяца должен быть от 1 до 12.")

        start_of_month = datetime(year, month, 1)
        end_of_month = datetime(
            year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

        session = Session()
        users_count = session.query(UserData).filter(
            UserData.timestamp >= start_of_month,
            UserData.timestamp < end_of_month
        ).distinct(UserData.user_id).count()
        session.close()

        await message.answer(
            f"Количество уникальных пользователей за {month} "
            f"месяц {year} года: {users_count}"
            )
        await state.clear()
    except (ValueError, IndexError):
        await message.answer(
            "Некорректный формат. Введите месяц и год в формате ММ.ГГГГ:"
            )


async def process_users_quarter(
        callback_query: CallbackQuery,
        state: FSMContext):
    await callback_query.message.answer(
        "Введите номер квартала и год в формате К.ГГГГ (например, 1.2023):"
        )
    await state.set_state(Form.waiting_for_quarter)


async def process_quarter_input(message: Message, state: FSMContext):
    try:
        quarter, year = map(int, message.text.split('.'))
        if quarter < 1 or quarter > 4:
            raise ValueError("Номер квартала должен быть от 1 до 4.")

        start_of_quarter = datetime(year, 3 * (quarter - 1) + 1, 1)
        end_of_quarter = datetime(
            year, 3 * quarter + 1, 1
            ) if quarter < 4 else datetime(year + 1, 1, 1)

        session = Session()
        users_count = session.query(UserData).filter(
            UserData.timestamp >= start_of_quarter,
            UserData.timestamp < end_of_quarter
        ).distinct(UserData.user_id).count()
        session.close()

        await message.answer(
            f"Количество уникальных пользователей за {quarter} "
            f"квартал {year} года: {users_count}"
            )
        await state.clear()
    except (ValueError, IndexError):
        await message.answer(
            "Некорректный формат. Введите номер квартала и "
            "год в формате К.ГГГГ (например, 1.2023):"
            )


async def process_users_year(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Введите год в формате ГГГГ:")
    await state.set_state(Form.waiting_for_year)


async def process_year_input(message: Message, state: FSMContext):
    try:
        year = int(message.text)
        start_of_year = datetime(year, 1, 1)
        end_of_year = datetime(year + 1, 1, 1)

        session = Session()
        users_count = session.query(UserData).filter(
            UserData.timestamp >= start_of_year,
            UserData.timestamp < end_of_year
        ).distinct(UserData.user_id).count()
        session.close()

        await message.answer(
            f"Количество уникальных пользователей за {year} год: {users_count}"
            )
        await state.clear()
    except ValueError:
        await message.answer(
            "Некорректный формат. Введите год в формате ГГГГ:"
            )


async def send_new_user_notification(user_id: int, username: str):
    """
    Отправляет уведомление о новом пользователе в указанный чат.

    :param user_id: ID пользователя в Telegram
    :param username: Имя пользователя в Telegram
    """
    notification_text = (
        "🚀 <b>Новый пользователь!</b>\n"
        f"<b>ID:</b> {user_id}\n"
        f"<b>Имя пользователя:</b> @{username}\n"
        f"<b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=notification_text,
            parse_mode=ParseMode.HTML
        )
        logging.info(f"Уведомление о новом пользователе отправлено: {user_id}")
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления: {e}")


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
            license_type="standard",
            employee_license_cost=700,
            tariff_name="HRlink Standard")
        await message.answer(
            "<b>Сколько кадровых специалистов в вашей компании?</b>",
            parse_mode=ParseMode.HTML)
        await state.set_state(Form.hr_specialist_count)
    elif employee_count >= 2000:
        await state.update_data(
            license_type="enterprise",
            employee_license_cost=600,
            tariff_name="HRlink Enterprise")
        await message.answer(
            "<b>Сколько кадровых специалистов в вашей компании?</b>",
            parse_mode=ParseMode.HTML)
        await state.set_state(Form.hr_specialist_count)
    else:
        await message.answer(
            "Пожалуйста, введите корректное количество сотрудников.",
            parse_mode=ParseMode.HTML)


async def process_license_type(
        callback_query: CallbackQuery, state: FSMContext
        ):
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
        # Если доставка равна 0, пропускаем вопрос о проценте
        await state.update_data(hr_delivery_percentage=0)
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

    # Проверяем, существует ли запись для данного user_id
    user_data = session.query(UserData).filter_by(
        user_id=message.from_user.id).first()

    if user_data:
        # Если запись существует, обновляем её
        user_data.organization_name = data.get(
            'organization_name', 'Не указано')
        user_data.employee_count = data.get(
            'employee_count', None)
        user_data.hr_specialist_count = data.get('hr_specialist_count', None)
        user_data.license_type = data.get('license_type', 'standard')
        user_data.tariff_name = data.get('tariff_name', 'HRlink Standard')
        user_data.documents_per_employee = data.get(
            'documents_per_employee', None)
        user_data.pages_per_document = data.get('pages_per_document', None)
        user_data.turnover_percentage = data.get('turnover_percentage', None)
        user_data.average_salary = data.get('average_salary', None)
        user_data.courier_delivery_cost = data.get(
            'courier_delivery_cost', None)
        user_data.hr_delivery_percentage = data.get(
            'hr_delivery_percentage', 0)
        user_data.timestamp = datetime.now()  # Обновляем время
    else:
        # Если записи нет, создаем новую
        user_data = UserData(
            user_id=message.from_user.id,
            organization_name=data.get('organization_name', 'Не указано'),
            employee_count=data.get('employee_count', None),
            hr_specialist_count=data.get('hr_specialist_count', None),
            license_type=data.get('license_type', 'standard'),
            tariff_name=data.get('tariff_name', 'HRlink Standard'),
            documents_per_employee=data.get('documents_per_employee', None),
            pages_per_document=data.get('pages_per_document', None),
            turnover_percentage=data.get('turnover_percentage', None),
            average_salary=data.get('average_salary', None),
            courier_delivery_cost=data.get('courier_delivery_cost', None),
            hr_delivery_percentage=data.get('hr_delivery_percentage', 0),
            timestamp=datetime.now()  # Устанавливаем текущее время
        )
        session.add(user_data)

    # Сохраняем изменения в базе данных
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
        total_license_costs = calculate_total_license_costs(
            data, license_costs)

        # Обновляем результаты расчетов в базе данных
        user_data.total_paper_costs = total_paper_costs
        user_data.total_logistics_costs = total_logistics_costs
        user_data.total_operations_costs = total_operations_costs
        user_data.total_license_costs = total_license_costs
        session.commit()

        # Добавляем результаты расчетов в data
        data['total_paper_costs'] = total_paper_costs
        data['total_logistics_costs'] = total_logistics_costs
        data['total_operations_costs'] = total_operations_costs
        data['total_license_costs'] = total_license_costs
        data['timestamp'] = datetime.now()  # Добавляем текущее время

        # Вывод результатов
        results = (
            f"<b>Число сотрудников:</b> {data.get(
                'employee_count', 'Не указано')}\n"
            f"<b>Число кадровых специалистов:</b> {data.get(
                'hr_specialist_count', 'Не указано')}\n"
            f"<b>Документов в год на сотрудника:</b> {data.get(
                'documents_per_employee', 'Не указано')}\n"
            f"<b>Страниц в документе:</b> {data.get(
                'pages_per_document', 'Не указано')}\n"
            f"<b>Текучка в процентах:</b> {data.get(
                'turnover_percentage', 'Не указано')}%\n"
            f"<b>Средняя зарплата:</b> {data.get(
                'average_salary', 'Не указано')} руб.\n"
            f"<b>Стоимость курьерской доставки:</b> {data.get(
                'courier_delivery_cost', 'Не указано')} руб.\n"
            f"<b>Процент отправки кадровых документов:</b> {data.get(
                'hr_delivery_percentage', 'Не указано')}%\n"
            "<b>Подходящий тариф:</b> "
            f"<u>{get_tariff_name(data)}</u>\n"
        )
        await message.answer(
            f"<b>Вы ввели следующие данные:</b>\n{results}",
            reply_markup=get_confirmation_keyboard(),
            parse_mode=ParseMode.HTML)

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
    session = Session()

    # Получаем последнюю запись из БД
    user_data_entries = session.query(UserData).filter_by(
        user_id=data['user_id']).order_by(UserData.timestamp.desc()).all()
    session.close()

    if not user_data_entries:
        await bot.send_message(
            chat_id=data['user_id'],
            text="<b>Ошибка: данные не найдены в базе данных.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    latest_entry = user_data_entries[0]  # Берем последнюю запись

    # Формируем комментарии с данными из БД
    comments = (
        f"<b>Тип лицензии:</b> <u>{latest_entry.tariff_name}</u>\n"
        f"<b>Число сотрудников:</b> {latest_entry.employee_count}\n"
        f"<b>Число кадровых специалистов:</b> {
            latest_entry.hr_specialist_count}\n"
        f"<b>Документов в год на сотрудника:</b> {
            latest_entry.documents_per_employee}\n"
        f"<b>Страниц в документе:</b> {latest_entry.pages_per_document}\n"
        f"<b>Текучка в процентах:</b> {latest_entry.turnover_percentage}%\n"
        f"<b>Средняя зарплата:</b> {latest_entry.average_salary} руб.\n"
        f"<b>Стоимость курьерской доставки:</b> {
            latest_entry.courier_delivery_cost} руб.\n"
        f"<b>Процент отправки кадровых документов:</b> {
            latest_entry.hr_delivery_percentage}%\n"
        f"<b>Сумма текущих трат на КДП на бумаге:</b> {format_number(
            latest_entry.total_paper_costs +
            latest_entry.total_logistics_costs +
            latest_entry.total_operations_costs
        ) if latest_entry.total_paper_costs is not None and latest_entry.total_logistics_costs is not None and latest_entry.total_operations_costs is not None else 'Неизвестно'} руб.\n"
        f"<b>Сумма КЭДО от HRlink:</b> {format_number(latest_entry.total_license_costs) if latest_entry.total_license_costs is not None else 'Неизвестно'} руб.\n"
        f"<b>Время расчета:</b> {latest_entry.timestamp}\n"
    )

    # Формируем первое сообщение с контактной информацией
    contact_info = (
        "<b>КЛИЕНТ ОСТАВИЛ ЗАЯВКУ</b>\n"
        f"<b>Имя:</b> {data['contact_name']}\n"
        f"<b>Телефон:</b> <code>{data['contact_phone']}</code>\n"
        f"<b>Email:</b> <code>{data['contact_email']}</code>\n"
        f"<b>Название компании:</b> {data['organization_name']}\n"
        f"<b>Тип лицензии:</b> <u>{latest_entry.tariff_name}</u>\n"
    )

    # Отправляем сообщения
    await bot.send_message(
        chat_id=CHAT_ID, text=contact_info,
        parse_mode=ParseMode.HTML)
    await bot.send_message(
        chat_id=CHAT_ID, text=comments,
        parse_mode=ParseMode.HTML)

    # Создаем лид в Битрикс
    await create_bitrix_lead(data, comments)


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

    # Формирование текста сообщения
    user_text1 = (
        "<b>ОСНОВНЫЕ ВЫВОДЫ ПО ВВЕДЕННЫМ ДАННЫМ</b>\n"
        "\n"
        f"<b>Ваши расходы на бумажное КДП: {format_number(
            total_paper_costs + total_logistics_costs + total_operations_costs
            )}</b> рублей в год\n"
        "\n"
        f"Печать и хранение кадровых документов: <b>{format_number(
            total_paper_costs
            )}</b> рублей в год\n"
        f"Доставка кадровых документов: <b>{format_number(
            total_logistics_costs
            )}</b> рублей в год\n"
        "Оплата времени кадрового специалиста, которое "
        f"он тратит на работу с документами: <b>{
            format_number(total_operations_costs)}</b> рублей в год\n"
        "\n"
    )

    user_text2 = (
        f"Внедрив КЭДО от HRlink, вы <b>сможете сэкономить: {format_number(total_paper_costs + total_logistics_costs + total_operations_costs - total_license_costs)}</b> рублей в год.\n"
        f"<b>Стоимость HRlink для вашей компании:</b> от {format_number(total_license_costs)} рублей в год.\n"
        f"<b>Цена лицензии сотрудника:</b> от {data.get('employee_license_cost', 700)} рублей в год.\n"
        "\n"
        "Точная цена рассчитывается менеджером индивидуально для каждого клиента.\n"
        "Вы получите:\n"
        "\n"
        "— множество интеграций с учетными системами и не только;\n"
        "— найм и работу с сотрудниками, самозанятыми и по ГПХ;\n"
        "— легитимное подписание и хранение документов;\n"
        "— удобный личный кабинет сотрудника;\n"
        "— гибкие маршруты и процессы;\n"
        "— все виды электронных подписей.\n"
    )

    # Генерация и отправка графика
    graph_path = generate_cost_graph(
        total_paper_costs,
        total_logistics_costs,
        total_operations_costs,
        total_license_costs
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

    await state.clear()  # Очищаем состояние
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


async def create_bitrix_lead(data, comments):
    bitrix_webhook_url = (
        "https://b24.hrlk.ru/rest/7414/d6bo0kujd1cm2owi/crm.lead.add.json"
    )

    # Проверка email
    email = data.get("contact_email", "").strip()
    if not is_valid_email(email):
        email = ""  # Если email невалидный, передаем пустое значение

    # Формирование данных для лида
    lead_data = {
        "fields": {
            "TITLE": "Лид с калькулятора в боте",
            "NAME": data.get("contact_name", "Не указано"),
            "PHONE": [{"VALUE": data.get("contact_phone", "Не указано"), "VALUE_TYPE": "WORK"}],
            "EMAIL": [{"VALUE": email, "VALUE_TYPE": "WORK"}] if email else [],  # Передаем email, только если он валидный
            "COMMENTS": comments,  # Используем комментарии, сформированные из БД
            "SOURCE_ID": "32",  # Телеграмм-бот / продукт
            "SOURCE_DESCRIPTION": "Телеграмм-бот / продукт"  # Дополнительно об источнике
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(bitrix_webhook_url, json=lead_data) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get("result"):
                        print("Лид успешно создан в Битрикс24")
                    else:
                        print(
                            f"Ошибка при создании лида: {response_data.get('error_description')}"
                        )
                else:
                    print(f"Ошибка HTTP: {response.status}")
                    print(f"Ответ сервера: {await response.text()}")
    except Exception as e:
        print(f"Ошибка при отправке запроса в Битрикс24: {e}")


def format_number(value):
    return "{:,.0f}".format(value).replace(',', ' ')


def is_valid_email(email):
    """
    Проверяет, является ли email валидным.
    """
    if not email:
        return False
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email) is not None


def get_tariff_name(data):
    license_type = data.get('license_type', 'standard')
    if license_type == 'lite':
        return "HRlink Lite"
    elif license_type == 'standard':
        return "HRlink Standard"
    elif license_type == 'enterprise':
        return "HRlink Enterprise"
    else:
        return "HRlink Standard"  # По умолчаниюы
