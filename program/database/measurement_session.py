from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.sql import functions, text
from sqlalchemy.ext.compiler import compiles
from base import Base
import logging
logger = logging.getLogger(__name__)
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
    __tablename__ = 'measurement_sessions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    instrument_id = Column(Integer, ForeignKey('instruments.id'))
    user = Column(Integer, ForeignKey('users.id'))
    data_table = Column(String, unique = True, default='NOT SET')
    description = Column(String)
    sensor_id = Column(String)
    gasmixer_system = Column(String)                    
    measurement_class_id = Column(Integer, ForeignKey('measurement_classes.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow())
    
    def create_data_table(self):
        if hasattr(self, 'engine'):
            table = 'data_table_%d' % self.id
            if self.engine.has_table(table):
                    logger.error('Data table already exist. Strange!')
                    query = 'DROP TABLE ' + table 
                    self.engine.execute(query)
            if self.measurement_class.measurement_type.find('INTERVAL') is 0:
                tmp_table = Table(table, Base.metadata, Column('id', Integer, primary_key=True))

                #query = text('CREATE TABLE :tbl (id serial)')
                try:
                    tmp_table.create(self.engine) 
                    #self.engine.execute(query, tbl = table)
                except Exception as e:
                    logger.error(e)
                    return
                else:
                    self.data_table = table
                    with self.engine.begin() as conn:
                        query = 'INSERT INTO ' + table + ' VALUES(default)'
                        for row in xrange(self.measurement_class.number_of_samples):
                            conn.execute(query)

            elif self.measurement_class.measurement_type.find('TIME') is 0:
                table = 'data_table_%d' % self.id
                query = 'CREATE TABLE public.' + table + '(id serial, created_at time with time zone NOT NULL DEFAULT \
                    (CURRENT_TIMESTAMP AT TIME ZONE \'utc\')::TIMESTAMP WITH TIME ZONE) WITH (OIDS = FALSE)'
    
    def new_run(self, columns):
        if hasattr(self, 'engine'):
            if self.measurement_class.measurement_type.find('INTERVAL') is 0:
                for column in columns:
                    query = text('ALTER TABLE public.:tbl ADD COLUMN :clm double precision')
                    try:
                        self.engine.execute(query, tbl = self.data_table, clm = column)
                    except Exception as e:
                        logger.error(e)
                        return False

                self.measurement_data = Table(self.data_table, Base.metadata, autoload = True, autoload_with = self.engine)
                self.measurement_data.active_columns = columns
                return True

    def add_data(self, data):
        if hasattr(self, 'engine'):
            if self.measurement_class.measurement_type.find('INTERVAL') is 0:
                with self.engine.begin() as conn:
                    for column in self.measurement_data.active_columns:
                        stmt = self.measurement_data.update().where(self.measurement_data.id == data['sample_nr']).values(column = data[column])
                        conn.execute(query)

                    
        