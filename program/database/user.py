from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from base import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    ifmname = Column(String(256), unique = True)
    fullname = Column(String(256))
    measurement_sessions = relationship('MeasurementSession', backref='users')