# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from measurement_session import MeasurementSession
from user import  User
from instrument import Instrument
from measurement_class import MeasurementClass
from base import Base
from decorator import decorator
import logging
logger = logging.getLogger(__name__)

@decorator
def commit_on_success(fn, *arg, **kw):
    """Decorate any function to commit the session on success, rollback in
    the case of error."""

    try:
        result = fn(*arg, **kw)
        arg[0].session.commit()
    except:
        arg[0].session.rollback()
        raise
    else:
        return result


class SessionManager(object):
    engine = None
    session = None
    def __init__(self, dsn = 'sqlite:///:memory:'):
        try:
            self.engine = create_engine(dsn, echo=True)
            Session = sessionmaker(bind = self.engine)
            self.session = Session()
            Base.metadata.create_all(self.engine)
            #Instrument.metadata.create_all(self.engine)
            #User.metadata.create_all(self.engine)
            #MeasurementClass.metadata.create_all(self.engine)
            #MeasurementSession.metadata.create_all(self.engine)



        except Exception as e:
            logger.error(e)
            return None
    
    @commit_on_success
    def add_user(self, ifmname, fullname):
        # check ifmname
        if self.session.query(User).filter_by(ifmname=ifmname).first() is None:
            self.session.add(User(ifmname = ifmname, fullname = fullname))

    @commit_on_success
    def add_measurement_class(self, name, spec, desc, type_enum):
        if self.session.query(MeasurementClass).filter_by(specification=spec).first() is None:
            self.session.add(MeasurementClass(name = name, specification = spec, description = desc, measurement_type = type_enum))

    @commit_on_success
    def add_instrument(self, model, serial, desc):
        if self.session.query(Instrument).filter_by(serial=serial).first() is None:        
            self.session.add(Instrument(model = model, serial = serial, description = desc))
                                                                        
    def get_users(self):
        return self.session.query(User).order_by(User.id).all()    

    def get_measurement_classes(self):
        return self.session.query(MeasurementClass).order_by(MeasurementClass.id).all()

    def get_instruments(self):
        return self.session.query(Instrument).order_by(Instrument.model).all()
        
    def get_measurement_sessions(self, *args, **kwargs):
        pass
        
    def create_session(self, **kwargs):
        # Make ms local when it works
        self.ms = self.session.query(MeasurementSession).filter_by(data_table='NOT SET').first()
        if self.ms is None:
            try:
                self.ms = MeasurementSession(name = kwargs['name'], instrument = kwargs['instrument'],\
                                                    user = kwargs['user'], description = kwargs['description'],\
                                                    sensor_id = kwargs['sensor_id'], gasmixer_system  = kwargs['gasmixer_system'],\
                                                    measurement_class = kwargs['measurement_class'])
            except KeyError as k:
                logger.error(k)
                return None
        else:
            try:
                self.ms.name = kwargs['name']
                self.instrument = kwargs['instrument']
                self.user = kwargs['user']
                self.description = kwargs['description']
                self.sensor_id = kwargs['sensor_id']
                self.gasmixer_system  = kwargs['gasmixer_system']
                self.measurement_class = kwargs['measurement_class']
            except KeyError as k:
                logger.error(k)
                return None
        try:
            self.session.add(self.ms)
            self.session.commit()
        except Exception as e:
            logger.warning(e)
            self.session.rollback()
            return None
        self.ms.data_table = 'data_table_%d' % self.ms.id
        msh = MeasurementSessionHandler(self.engine, self.ms)
        self.session.commit()
        return msh
            
             
class MeasurementSessionHandler(object):
    
    def __init__(self, engine, measurement_session):
        Session = sessionmaker(bind = engine)
        self.session = Session()
        self.measurement_session = measurement_session
        try:
            from sqlalchemy.sql.expression import text
            from sqlalchemy import Column, DateTime, Table, Integer
            #self.data_table = Table(self.measurement_session.data_table, Base.metadata, Column('id', Integer, primary_key=True),\
            #    Column('created_at', DateTime, server_default=text('NOW()')))
            self.DataTable = type('DataTable', (Base,), {'__tablename__': self.measurement_session.data_table,\
                'id': Column(Integer, primary_key=True), 'created_at': Column(DateTime, server_default=text('NOW()'))})

            #Base.metadata.create_all(tables = [data_table.__table__])
            self.DataTable.__table__.create(engine)
            #self.data_table.create(engine)
            #self.session.add(self.DataTable)
            #self.session.add(self.measurement_session)
            #self.session.commit()          
        except Exception as e:
            logger.warning(e)
            
    def add_data(self, data):
        self.session.add(self.DataTable())
      
#    def next_run(self. names)
#        self.DataTable.XXX = Column(names[0] + '_x', Float)
#        self.DataTable.__table__.append_column(self.DataTable.XXX   )
#        res = self.engine.execute('ALTER TABLE %s') 
                        
                                                                                  
if __name__ is '__main__':
    s = SessionManager(dsn = 'postgresql://petermoller:lotus123@localhost/unimeas')
    s.add_user('petmo', 'Peter Möller')
    s.add_instrument('Sourcemeter 2601B', '12345', 'blabla')
    s.add_measurement_class('first_class', 'blabla_spec', 'bla_desc', 'INTERVAL')
    #s.create_session({'name':'test1_name', 'Instrument':1, 'user':'petmo', 'description':'my_desc', 'sensor_id':'sensor_id_text', 'measurement_class':1, 'gasmixer_system':'GM2'})
    ms = s.create_session(name='test1_name', instrument=1, user=1, description='my_desc', sensor_id='sensor_id_text', measurement_class=1, gasmixer_system='GM2')
    