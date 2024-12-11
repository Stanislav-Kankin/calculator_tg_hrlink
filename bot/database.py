from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, PaperCosts, LicenseCosts, TypicalOperations


def init_db():
    engine = create_engine('sqlite:///user_data.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    if not session.query(PaperCosts).first():
        paper_costs = PaperCosts()
        session.add(paper_costs)
        session.commit()

    if not session.query(LicenseCosts).first():
        license_costs = LicenseCosts()
        session.add(license_costs)
        session.commit()

    if not session.query(TypicalOperations).first():
        typical_operations = TypicalOperations()
        session.add(typical_operations)
        session.commit()

    session.close()
