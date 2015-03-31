from sqlalchemy import Column, Integer, String 
from sqlalchemy.orm import relationship
from base import Base

class Instrument(Base):
    __tablename__ = 'instruments'

    id = Column(Integer, primary_key=True)
    model = Column(String(256))
    serial = Column(String(256), unique = True)
    description = Column(String(256))

    measurement_sessions = relationship('MeasurementSession', backref='instrument')