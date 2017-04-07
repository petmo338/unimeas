__author__ = 'petmo_000'
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decorator import decorator

from measurement_session import MeasurementSession
from user import User
from instrument import Instrument
from measurement_class import MeasurementClass
from base import Base

import ConfigParser

config = ConfigParser.ConfigParser()
logger.info('Config file %s', config.read('preferences.ini'))
if config.has_option('General', 'DSN'):
    DSN = config.get('General', 'DSN')
else:
    DSN = 'sqlite:///:memory:'
logger = logging.getLogger(__name__)
Session = sessionmaker()

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

    def __init__(self, dsn=DSN):
        try:
            self.engine = create_engine(dsn, echo=False)
            Session.configure(bind=self.engine)
            self.session = Session()
            Base.metadata.create_all(self.engine)

        except Exception as e:
            logger.error(e)

    @commit_on_success
    def add_user(self, ifmid, fullname):
        # check ifmname
        if self.session.query(User).filter_by(ifmid=ifmid).first() is None:
            self.session.add(User(ifmid=ifmid, fullname=fullname))

    @commit_on_success
    def add_measurement_class(self, name, spec, nr_of_samples, desc, type_enum):
        if self.session.query(MeasurementClass).filter_by(specification=spec).first() is None:
            self.session.add(MeasurementClass(name=name, specification=spec, number_of_samples=nr_of_samples,
                                              description=desc, measurement_type=type_enum))

    @commit_on_success
    def add_instrument(self, model, serial, desc):
        if self.session.query(Instrument).filter_by(serial=serial).first() is None:
            self.session.add(Instrument(model=model, serial=serial, description=desc))

    def get_users(self):
        return self.session.query(User).order_by(User.id).all()

    def get_measurement_classes(self, **kwargs):
        if kwargs is None:
            return self.session.query(MeasurementClass).order_by(MeasurementClass.id).all()
        return self.session.query(MeasurementClass).order_by(MeasurementClass.id).filter_by(**kwargs)

    def get_instruments(self):
        return self.session.query(Instrument).order_by(Instrument.model).all()

    def get_measurement_sessions(self, **kwargs):
        logger.info('In get_meas_sess, kwargs %s', kwargs)
        filters = dict()
        available_columns = [c.name for c in MeasurementSession.__table__.columns]
        # available_columns = [n.split('.')[1] for n in MeasurementSession.__table__.c]
        for key, value in kwargs.iteritems():
            logger.info('key %s, value, %s, avail_cols: %s', key, value, available_columns)
            if key in available_columns:
                filters[key] = value
        logger.info('filter %s', filters)
        result = self.session.query(MeasurementSession).filter_by(**filters).all() #User, MeasurementSession.user==User.id
        logger.info('result %s, filter %s', result, filters)
        return result

    def open_session(self, sessionId):
        result = self.session.query(MeasurementSession).filter_by(id=sessionId).first()
        if result is None:
            return None
        result.open_data_table(self.engine)
        return result

    def create_session(self, **kwargs):
#        self.session.begin()
        ms = self.session.query(MeasurementSession).filter_by(data_table='NOT SET').first()
        logger.info('ms %s', ms)
        if ms is None:
            try:
                ms = MeasurementSession(engine=self.engine, name=kwargs['name'],
                                        instrument_id=kwargs['instrument'], user=kwargs['user'],
                                        description=kwargs['description'], sensor_id=kwargs['sensor_id'],
                                        gasmixer_system=kwargs['gasmixer_system'],
                                        measurement_class_id=kwargs['measurement_class'])
            except KeyError as k:
                logger.error(k)
                self.session.rollback()
                return None
        else:
            try:
                ms.engine = self.engine
                ms.name = kwargs['name']
                ms.instrument_id = kwargs['instrument']
                ms.user = kwargs['user']
                ms.description = kwargs['description']
                ms.sensor_id = kwargs['sensor_id']
                ms.gasmixer_system = kwargs['gasmixer_system']
                ms.measurement_class_id = kwargs['measurement_class']
            except KeyError as k:
                logger.error(k)
                self.session.rollback()
                return None
        try:
            self.session.add(ms)
            self.session.commit()
        except Exception as e:
            logger.warning(e)
            self.session.rollback()
            return None
        try:
            ms.create_data_table()
            self.session.add(ms)
            self.session.commit()
        except Exception as e:
            logger.warning('Unable to create data table %s', e)
            return None
        return ms