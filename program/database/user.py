__author__ = 'petmo_000'
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from base import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    ifmid = Column(String, unique=True)
    fullname = Column(String)
    measurement_sessions = relationship('MeasurementSession', backref='users')