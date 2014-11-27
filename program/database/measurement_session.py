from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, DDL, Float
from sqlalchemy.sql import functions
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
    name = Column(String(256))
    instrument_id = Column(Integer, ForeignKey('instruments.id'))
    user = Column(Integer, ForeignKey('users.id'))
    data_table = Column(String(256), unique = True, default='NOT SET')
    description = Column(String(256))
    sensor_id = Column(String(256))
    gasmixer_system = Column(String(256))                    
    measurement_class_id = Column(Integer, ForeignKey('measurement_classes.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow())
    
    def create_data_table(self):
        if hasattr(self, 'engine'):
            table = 'data_table_%d' % self.id
            if self.engine.has_table(table):
                    logger.error('Data table already exist. Strange! Dropping table.')
                    query = 'DROP TABLE ' + table 
                    self.engine.execute(query)
            if self.measurement_class.measurement_type.find('INTERVAL') is 0:
                self.measurement_data = Table(table, Base.metadata, Column('id', Integer, primary_key=True))
                try:
                    self.measurement_data.create(self.engine) 
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
                self.measurement_data = Table(table, Base.metadata, Column('id', Integer, primary_key=True), \
                    Column('created_at', DateTime(timezone=True), nullable=False, default=utcnow()))
                for column in  self.measurement_class.data_columns.split(','):
                    self.measurement_data.append_column(Column(column, Float))
                try:
                    self.measurement_data.create(self.engine) 
                except Exception as e:
                    logger.error(e)
                    return
    
    def new_run(self, columns):
        if hasattr(self, 'engine'):
            if self.measurement_class.measurement_type.find('INTERVAL') is 0:
                for column in columns:
                    stmt = DDL('ALTER TABLE %(table)s ADD COLUMN %(clm)s double precision', context = {'table':self.data_table,'clm':column})
                    try:
                        stmt.execute(self.engine)
                    except Exception as e:
                        logger.error(e)
                        return False
                    self.measurement_data.append_column(Column(column, Float))

                self.measurement_data.active_columns = columns
                return True

    def add_data(self, data):
        if hasattr(self, 'engine'):
            if self.measurement_class.measurement_type.find('INTERVAL') is 0:
                with self.engine.begin() as conn:
                    d = dict()
                    for column in self.measurement_data.active_columns:
                        d[column] = data[column]
                    stmt = self.measurement_data.update().where(self.measurement_data.c.id == data['sample_nr']).values(d)
                    conn.execute(stmt)
            elif self.measurement_class.measurement_type.find('TIME') is 0:
                stmt = self.measurement_data.insert().values(data)
                self.engine.execute(stmt)
                    
        