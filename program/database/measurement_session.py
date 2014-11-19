from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import functions
from sqlalchemy.ext.compiler import compiles
from base import Base
#from . import User, Instrument, MeasurementClass

class utcnow(functions.FunctionElement):
    key = 'utcnow'
    type = DateTime(timezone=True)

@compiles(utcnow)
def _default_utcnow(element, compiler, **kw):
    """default compilation handler.

    Note that there is no SQL "utcnow()" function; this is a
    "fake" string so that we can produce SQL strings that are dialect-agnostic,
    such as within tests.

    """
    return "utcnow()"

@compiles(utcnow, 'postgresql')
def _pg_utcnow(element, compiler, **kw):
    """Postgresql-specific compilation handler."""

    return "(CURRENT_TIMESTAMP AT TIME ZONE 'utc')::TIMESTAMP WITH TIME ZONE"


class MeasurementSession(Base):
    __tablename__ = 'measurement_session'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    instrument = Column(Integer, ForeignKey('instruments.id'))
    user = Column(Integer, ForeignKey('users.id'))
    data_table = Column(String, unique = True, default='NOT SET')
    description = Column(String)
    sensor_id = Column(String)
    gasmixer_system = Column(String)                    
    measurement_class = Column(Integer, ForeignKey('measurement_classes.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow())
    
        