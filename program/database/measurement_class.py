from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Enum
from base import Base

class MeasurementClass(Base):
    __tablename__ = 'measurement_classes'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    specification = Column(String, unique = True)
    description = Column(String)
    measurement_type = Column(Enum('INTERVAL', 'TIME', name = 'measurement_type_enum'))