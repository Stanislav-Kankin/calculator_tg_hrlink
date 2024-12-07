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
            text="Стандартная лицензия 👍", callback_data="standard_license")],
        [InlineKeyboardButton(
            text="Лицензия Lite 😎", callback_data="lite_license"
            )]
    ])
    return keyboard
