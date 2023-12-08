from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class FuturesDataBase(Base):
    __tablename__ = 'futures'

    pair = Column(String, primary_key=True)

    leverage = Column(Integer)
    value_usd = Column(Float)

    make_long = Column(Float)
    close_long = Column(Float)

    make_short = Column(Float)
    close_short = Column(Float)

    work = Column(Boolean)

    #
    # @classmethod
    # def get_all_symbols(cls, session):
    #     return [item.symbol for item in session.query(cls).all()]
    #
    # @classmethod
    # def delete_by_symbol(cls, session, symbol):
    #     session.query(cls).filter(cls.symbol == symbol).delete()
    #     session.commit()
