# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, Table
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
            self.engine = create_engine(dsn, echo = True)
            Session = sessionmaker(bind = self.engine)
            self.session = Session()
            Base.metadata.create_all(self.engine)

        except Exception as e:
            logger.error(e)
            return None
    
    @commit_on_success
    def add_user(self, **kwargs):
        # check ifmname
        if self.session.query(User).filter_by(ifmname = kwargs['ifmname']).first() is None:
            self.session.add(User(ifmname = kwargs['ifmname'], fullname = kwargs['fullname']))

    @commit_on_success
    def add_measurement_class(self, **kwargs):
        if self.session.query(MeasurementClass).filter_by(specification=kwargs['specification']).first() is None:
            if kwargs['type_enum'] is 'INTERVAL':
                if kwargs['nr_of_samples'] < 1:
                    return False
                self.session.add(MeasurementClass(name = kwargs['name'], specification = kwargs['specification'],\
                    number_of_samples = kwargs['nr_of_samples'], description = kwargs['description'],\
                    measurement_type = kwargs['type_enum']))                
            if kwargs['type_enum'] is 'TIME':
                if len(kwargs['data_columns']) < 1:
                    return False
                self.session.add(MeasurementClass(name = kwargs['name'], specification = kwargs['specification'],\
                    data_columns = kwargs['data_columns'], description = kwargs['description'],\
                    measurement_type = kwargs['type_enum']))                
        else:
            return False

    @commit_on_success
    def add_instrument(self, **kwargs):
        if self.session.query(Instrument).filter_by(serial=kwargs['serial']).first() is None:        
            self.session.add(Instrument(model = kwargs['model'], serial = kwargs['serial'],\
                description = kwargs['description']))
                                                                        
    def get_users(self):
        return self.session.query(User).order_by(User.id).all()    

    def get_measurement_classes(self):
        return self.session.query(MeasurementClass).order_by(MeasurementClass.id).all()

    def get_instruments(self):
        return self.session.query(Instrument).order_by(Instrument.model).all()
        
    def get_measurement_sessions(self, **kwargs):
        ms = self.session.query(MeasurementSession).filter_by(**kwargs).all()
        return ms
        
    def get_measurement(self, uid):
        ms = self.session.query(MeasurementSession).filter_by(id = uid).first()
        ms.measurement_data = Table(ms.data_table, Base.metadata, autoload = True, autoload_with = self.engine)
        return ms

    def create_session(self, **kwargs):
        ms = self.session.query(MeasurementSession).filter_by(data_table='NOT SET').first()
        if ms is None:
            try:
                ms = MeasurementSession(name = kwargs['name'], instrument_id = kwargs['instrument'],\
                                                    user = kwargs['user'], description = kwargs['description'],\
                                                    sensor_id = kwargs['sensor_id'], gasmixer_system  = kwargs['gasmixer_system'],\
                                                    measurement_class_id = kwargs['measurement_class'])
            except KeyError as k:
                logger.error(k)
                return None
        else:
            try:
                ms.name = kwargs['name']
                ms.instrument_id = kwargs['instrument']
                ms.user = kwargs['user']
                ms.description = kwargs['description']
                ms.sensor_id = kwargs['sensor_id']
                ms.gasmixer_system  = kwargs['gasmixer_system']
                ms.measurement_class_id = kwargs['measurement_class']
            except KeyError as k:
                logger.error(k)
                return None
        try:
            self.session.add(ms)
            self.session.commit()
        except Exception as e:
            logger.warning(e)
            self.session.rollback()
            return None

        ms.engine = self.engine
        ms.create_data_table()
        self.session.commit()
        return ms            
                                                                                  
if __name__ is '__main__':
    s = SessionManager(dsn = 'postgresql://sensor:sensor@localhost/unimeas')
    #s = SessionManager()
    data_cols = ['sample_nr', 'ai00', 'ai01', 'ai02', 'time']
    s.add_user(ifmname = 'petmo', fullname = u'Peter Möller')
    s.add_instrument(model = 'Sourcemeter 2601B', serial = '12345', description = 'blabla')
    s.add_measurement_class(name = 'first_class', specification = 'blabla_spec3', nr_of_samples = 20, description = 'bla_desc', type_enum = 'INTERVAL')
    s.add_measurement_class(name = 'second_class', specification = 'blabla_spec5', description = 'bla_desc2', type_enum = 'TIME',\
        data_columns = ','.join(data_cols))
    ms = s.create_session(name='test1_name', instrument=1, user=1, description='my_desc', sensor_id='sensor_id_text', measurement_class=1, gasmixer_system='GM2')
    ms2 = s.create_session(name='test2_name', instrument=1, user=1, description='my_desc2', sensor_id='sensor_id_text', measurement_class=5, gasmixer_system='GM2')
    ms.new_run(['x_volt2', 'y_current2'])
    ms.add_data({'sample_nr': 2, 'x_volt2': 0.1233, 'y_current2': 123.32})
    ms2.add_data({'sample_nr': 1, 'ai00':1.23, 'ai01':3.45, 'ai02':0.23, 'time':4.32})