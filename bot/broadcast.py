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

    # Формируем список путей к изображениям
    # image_paths = [
    #     os.path.join(images_dir, '1.jpg'),
    #     os.path.join(images_dir, '2.jpg'),
    #     os.path.join(images_dir, '3.jpg'),
    #     os.path.join(images_dir, '4.jpg')
    # ]

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
        "Уважаемые пользователи!\n\n"
        "Недавно в нашем боте произошел инцидент: злоумышленник получил доступ и рассылал сообщения от его имени.\n\n"
        "<b>Что важно знать:</b>\n"
        "✔️ Утечки личных данных не было – бот не хранит и не обрабатывает конфиденциальную информацию.\n"
        "✔️ Уязвимость устранена – мы оперативно обновили систему и теперь бот полностью безопасен.\n"
        "⚠️ <b>Не переходите по подозрительным ссылкам</b> из прошлых сообщений – они могут быть вредоносными.\n\n"
        "Мы приносим извинения за доставленные неудобства и благодарим за понимание. "
        "Бот снова работает в штатном режиме – вы можете пользоваться им как прежде.\n\n"
        "Если у вас есть вопросы – готовы ответить."
    )

    # Формируем медиагруппу
    media = [InputMediaPhoto(
        media=FSInputFile(image_path)) for image_path in image_paths]
    media[0].caption = message_text
    media[0].parse_mode = 'HTML'

    # Отправляем сообщения каждому пользователю
    for user in users:
        try:
            await bot.send_media_group(chat_id=user.user_id, media=media)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

    session.close()
