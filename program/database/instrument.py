__author__ = 'petmo_000'
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from base import Base


class Instrument(Base):
    __tablename__ = 'instruments'

    id = Column(Integer, primary_key=True)
    model = Column(String)
    serial = Column(String, unique=True)
    description = Column(String)

    measurement_sessions = relationship('MeasurementSession', backref='instrument')