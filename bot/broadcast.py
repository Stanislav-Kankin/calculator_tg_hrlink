from aiogram import Bot
from aiogram.types import InputMediaPhoto, FSInputFile
from aiogram.enums import ParseMode
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import UserData
import os


async def send_broadcast(bot: Bot):
    # Получаем абсолютный путь к директории с изображениями
    base_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(base_dir, 'images')

    # Формируем список путей к изображениям
    image_paths = [
        os.path.join(images_dir, '1.jpg'),
        os.path.join(images_dir, '2.jpg'),
        os.path.join(images_dir, '3.jpg'),
        os.path.join(images_dir, '4.jpg')
    ]

    # Создаем сессию для работы с базой данных
    engine = create_engine('sqlite:///user_data.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # Получаем всех пользователей из базы данных
    users = session.query(UserData).all()

    # Текст сообщения с HTML-разметкой для ссылки
    message_text = (
        "В прошлом году кадровый ЭДО от HRlink помог компаниям подписать более 25 млн документов онлайн и сэкономить 10 млн рабочих часов кадровых специалистов.\n\n"
        "Хотите также? Чтобы вы могли быстро оцифровать процессы КДП, мы подготовили набор из трех гайдов. Они помогут:\n\n"
        "• обосновать для руководителя необходимость перехода;\n"
        "• сформировать требования к сервису и выбрать идеальный для вас;\n"
        "• определить этапы внедрения и результат на каждом из них;\n"
        "• узнать заранее обо всех рисках и скрытых платежах.\n\n"
        "Подробнее о каждом из гайдов читайте в карточках 👆\n\n"
        '<a href="https://hr-link.ru/give_guides?utm_source=telegram&utm_medium=bot&utm_term=&utm_content=free&utm_campaign=give_guides">Скачивайте гайды по этой ссылке</a>.'
    )

    # Формируем медиагруппу
    media = [InputMediaPhoto(media=FSInputFile(image_path)) for image_path in image_paths]
    media[0].caption = message_text  # Добавляем подпись к первому изображению
    media[0].parse_mode = 'HTML'  # Устанавливаем режим разбора текста для первого изображения

    # Отправляем сообщения каждому пользователю
    for user in users:
        try:
            await bot.send_media_group(chat_id=user.user_id, media=media)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

    session.close()
