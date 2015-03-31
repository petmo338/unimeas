__author__ = 'petmo_000'
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.sql import functions, text
from sqlalchemy.ext.compiler import compiles
from database.base import Base
import logging

logger = logging.getLogger(__name__)


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
    data_table = Column(String, unique=True, default='NOT SET')
    description = Column(String)
    sensor_id = Column(String)
    gasmixer_system = Column(String)
    measurement_class_id = Column(Integer, ForeignKey('measurement_classes.id'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow())
    measurement_data = Table()
    engine = None

    def open_data_table(self, engine):
        self.engine = engine
        self.measurement_data = Table(self.data_table, Base.metadata, autoload_with=self.engine, autoload=True, extend_existing=True)

    def create_data_table(self):
        table = 'data_table_%d' % self.id
        table_exist = self.engine.has_table(table)
        with self.engine.begin() as conn:
            if table_exist:
                    logger.error('Data table already exist. Strange!')
                    query = 'DROP TABLE ' + table
                    conn.execute(query)
            self.data_table = table
            if self.measurement_class.measurement_type.find('INTERVAL') is 0:
                tmp_table = Table(table, Base.metadata, Column('id', Integer, primary_key=True), autoload=True,
                                  extend_existing=True)
                try:
                    tmp_table.create(conn)
                except Exception as e:
                    logger.error(e)
                    return
                else:
                    query = 'INSERT INTO ' + table + ' VALUES(default)'
                    for row in xrange(self.measurement_class.number_of_samples):
                        conn.execute(query)

            elif self.measurement_class.measurement_type.find('TIME') is 0:
#                self.data_table = table
                columns = self.measurement_class.specification.split(',')
                query = 'CREATE TABLE public.'\
                        + table + ' (id serial, created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(), '\
                        + ' double precision, '.join(columns) + ' double precision) '\
                        + 'WITH (OIDS = FALSE)'
                conn.execute(query)


    def new_run(self, columns):
        if self.measurement_class.measurement_type.find('INTERVAL') is 0:
            for column in columns:
                query = text('ALTER TABLE :tbl ADD COLUMN :clm double precision')
                try:
                    self.engine.execute(query, tbl=self.data_table, clm=column)
                except Exception as e:
                    logger.error(e)
                    return False
            self.measurement_data = Table(self.data_table, Base.metadata, autoload=True, autoload_with=self.engine)
            self.measurement_data.active_columns = columns
            return True

    def _check_column_names(self, columns):
        for column in columns:
            if hasattr(self.measurement_data, column):
                return False
        return True

    def add_data(self, data):
        if self.measurement_class.measurement_type.find('INTERVAL') is 0:
            with self.engine.begin() as conn:
                for column in self.measurement_data.active_columns:
                    query = self.measurement_data.update().where(self.measurement_data.id == data['sample_nr']).\
                        values(column=data[column])
                    conn.execute(query)
        elif self.measurement_class.measurement_type.find('TIME') is 0:
            query = self.measurement_data.insert(data)
            logger.info(query)
            self.engine.execute(query)

