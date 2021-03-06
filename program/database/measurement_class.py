__author__ = 'petmo_000'
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Enum

from base import Base


class MeasurementClass(Base):
    __tablename__ = 'measurement_classes'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    specification = Column(String)
    number_of_samples = Column(Integer)
    description = Column(String)
    measurement_type = Column(Enum('INTERVAL', 'TIME', name='measurement_type_enum'))

    measurement_sessions = relationship('MeasurementSession', backref='measurement_class')