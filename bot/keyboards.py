from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2, inline_keyboard=[
        [InlineKeyboardButton(
            text="Начать расчёт заново",
            callback_data="restart")],
        [InlineKeyboardButton(text="Стоп", callback_data="stop")]
    ])
    return keyboard


def get_start_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Приступисть к расчётам", callback_data="start_form")]
    ])
    return keyboard
