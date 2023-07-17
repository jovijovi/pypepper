import pytest
from sqlalchemy import Column, select, delete, update
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.sql import functions

from pypepper.helper.db import mysql

Base = declarative_base()


class Animals(Base):
    __tablename__ = "animals"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    color = Column(String)

    def __repr__(self):
        return f"Animals(id={self.id!r}, name={self.name!r}, color={self.color!r})"


cat1 = Animals(
    name='cat',
    color='white',
)

cat2 = Animals(
    name='cat',
    color='black',
)

cat3 = Animals(
    name='cat',
    color='yellow',
)


def test_all():
    # Connect
    engine = mysql.connect(mysql.Config(
        uri="mysql+pymysql://root:example@localhost:3306/mock_pypepper?charset=utf8mb4",
    ))
    assert engine.closed is False

    # Check engine status
    ok = mysql.ping(engine)
    assert ok is True

    # Build a session factory
    session = sessionmaker(engine)

    # Add cat1, cat2
    with session() as session1, session1.begin():
        # inner context calls session.commit(), if there were no exceptions
        # outer context calls session.close()
        session1.add_all([cat1, cat2])
        stmt1 = select(Animals).where(Animals.color.in_(["black"]))
        for cat in session1.scalars(stmt1):
            print("Black cats=", cat)

    # Add cat3
    with Session(engine) as session2:
        # It is automatically closed at the end of the block,
        # this is equivalent to calling the Session.close() method.
        session2.add_all([cat3])
        session2.commit()
        stmt2 = select(Animals).where(Animals.color.in_(["yellow"]))
        for cat in session2.scalars(stmt2):
            print("Yellow cat=", cat)

    # Update
    with session() as session3, session3.begin():
        session3.execute(update(Animals).filter_by(color='black').values(color='white'))

    # Query
    with session() as session4:
        stmt = select(Animals).filter_by(color='white')
        result = session4.scalars(stmt).all()
        print("White cats=", result)
        count = session4.scalars(select(functions.count(1)).select_from(Animals)).all()
        print("Cats count=", count[0])

    # Delete
    with session() as session5, session5.begin():
        session5.execute(delete(Animals).filter_by(color='white'))
        session5.delete(cat3)
        session5.execute(delete(Animals).filter_by(color='yellow'))
        session5.execute(delete(Animals).filter_by(color='white'))

    # Delete not present instance
    with session() as session6:
        session6.begin()
        try:
            session6.delete(cat2)
            session6.commit()
        except Exception as e:
            session6.rollback()
            print("Excepted error=", e)
        finally:
            session6.close()

    engine.close()
    assert engine.closed is True


def test_connect():
    engine = mysql.connect(mysql.Config(
        username='root',
        password='example',
        host='localhost',
        db='mock_pypepper',
    ))
    assert engine.closed is False

    ok = mysql.ping(engine)
    assert ok is True

    engine.close()
    assert engine.closed is True


if __name__ == '__main__':
    pytest.main()
