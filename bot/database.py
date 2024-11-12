from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, PaperCosts

def init_db():
    """
    Инициализирует базу данных и создает все таблицы.
    """
    engine = create_engine('sqlite:///user_data.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Проверяем, существуют ли данные в таблице PaperCosts
    if not session.query(PaperCosts).first():
        # Добавляем начальные данные в таблицу PaperCosts
        paper_costs = PaperCosts()
        session.add(paper_costs)
        session.commit()

    session.close()

if __name__ == '__main__':
    init_db()
