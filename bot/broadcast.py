from aiogram import Bot
from aiogram.types import InputMediaPhoto, FSInputFile
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import UserData
import os


async def send_broadcast(bot: Bot):
    # Получаем абсолютный путь к директории с изображениями
    base_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(base_dir, 'images')

    image_paths = [
        os.path.join(images_dir, 'march12.jpg')
    ]

    # Создаем сессию для работы с базой данных
    engine = create_engine('sqlite:///user_data.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # Получаем всех пользователей из базы данных
    users = session.query(UserData).all()

    message_text = (
        "Здравствуйте!\n\n"
        "Вчера наш бот подвергся атаке. Злоумышленники получили доступ к отправке сообщений и рассылали материалы неподобающего характера. "
        "Нам искренне жаль, что вам пришлось столкнуться с неудобствами.\n\n"
        "Киберпреступления сегодня — глобальная проблема. Пожалуйста, будьте внимательны и не переходите по подозрительным ссылкам.\n\n"
        "Сейчас все под контролем. Мы усилили меры безопасности и восстановили нормальную работу. "
        "А также сделали <a href='https://t.me/hrl_calcbot'>нового бота</a> для вашего удобства.\n\n"
        "Благодарим за понимание."
    )

    # Формируем медиагруппу
    # media = [InputMediaPhoto(
    #     media=FSInputFile(image_path)) for image_path in image_paths]
    # media[0].caption = message_text
    # media[0].parse_mode = 'HTML'

    # Отправляем сообщения каждому пользователю
    # for user in users:
    #     try:
    #         await bot.send_media_group(chat_id=user.user_id, media=media)
    #     except Exception as e:
    #         print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

    # session.close()

    # Отправляем текстовые сообщения каждому пользователю
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.user_id,
                text=message_text,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

    session.close()
