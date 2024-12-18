from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(
            text="Начать расчёт заново ⚙",
            callback_data="restart")],
        [InlineKeyboardButton(text="Стоп ⛔", callback_data="stop")]
    ])
    return keyboard


def get_start_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Приступисть к расчётам 📱", callback_data="start_form")]
    ])
    return keyboard


def get_contact_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(
            text="Свяжитесь со мной 🙋‍♂️🙋‍♀️", callback_data="contact_me"
            )],
        [InlineKeyboardButton(
            text="Начать расчёт заново ⚙",
            callback_data="restart")]
    ])
    return keyboard


def get_license_type_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(
            text="HRlink Lite 👍", callback_data="simple_kedo"
            )],
        [InlineKeyboardButton(
            text="HRlink Standart 😎", callback_data="standard_kedo"
            )]
    ])
    return keyboard


def get_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(text="Данные верны ✔", callback_data="confirm")],
        [InlineKeyboardButton(text="Ввести заново ⚙", callback_data="restart")]
    ])
    return keyboard
