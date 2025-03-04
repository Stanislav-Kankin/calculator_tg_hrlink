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

    # Текст сообщения с HTML-разметкой для ссылки
    message_text = (
        "👥 Во время кризиса на рынке труда особенно важно относиться к сотруднику "
        "как к клиенту, создавать комфортные условия на всех этапах его "
        "пути в компании. Как и какие инструменты автоматизации "
        "применять для этого в 2025 году?\n\n" 

"Расскажем <b>12 марта в 11:00 МСК на бесплатной онлайн-конференции «Сотрудники как клиенты в 2025 году»</b>"
" с ведущими экспертами рынка.\n\n"

"— Как решения от HRlink, Skillaz и Trivio упрощают каждый этап Employee Journey Map.\n"
"— Какие инструменты ИИ могут помочь в HR в ежедневных задачах и как применять их на практике.\n"
"— Как выстраивать работу с управленческими командами и оценивать результаты.\n\n"

"3 доклада, 2 мастер-класса, ответы на ваши вопросы и более 700 участников для нетворкинга.\n\n"

"<b>Каждый участник получит диплом о прохождении обучения — добавьте его в резюме на hh.ru и станьте более заметным для работодателей.</b>\n\n"

"Регистрируйтесь и получите гайд «Инструменты ИИ для решения повседневных задач HR и рекрутеров», а также подарки от «Яндекс Практикум», «Литрес» и «Ясно»\n\n"
        '➡️<a href="https://hr-link.ru/employees_2025?utm_source=telegram&utm_medium=bot&utm_term=calculator&utm_content=free%7C&utm_campaign=employees_2025"><b>Учавствовать</b></a>👈'
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
