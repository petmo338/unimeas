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
        self.session.add(User(ifmname = ifmname, fullname = fullname))

    @commit_on_success
    def add_measurement_class(self, name, spec, desc, type_enum):
        self.session.add(MeasurementClass(name = name, specification = spec, description = desc, measurement_type = type_enum))

    @commit_on_success
    def add_instrument(self, model, serial, desc):
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
        try:
            ms = MeasurementSession(name = kwargs['name'], instrument = kwargs['instrument'],\
                                                user = kwargs['user'], description = kwargs['description'],\
                                                sensor_id = kwargs['sensor_id'], gasmixer_system  = kwargs['gasmixer_system '],\
                                                measurement_class = kwargs['measurement_class'])
        except KeyError:
            return None
        try:
            self.session.add(ms)
            self.session.commit()
        except:
            self.session.rollback()
            return None
        return MeasurementSessionHandler(self, self.engine, ms)
            
             
class MeasurementSessionHandler(object):
    
    def __init__(self, engine, measurement_session):
        Session = sessionmaker(bind = self.engine)
        self.session = Session()
        self.measurement_session = measurement_session
        try:
            from sqlalchemy.sql.expression import text
            from sqlalchemy import Column, DateTime
            tablename = 'data_table_%d' % self.measurement_session.id
            data_table = type('DataTable', (Base,), {'__tablename__': tablename, 'created_at': Column(DateTime, server_default=text('NOW()'))})
            Base.metadata.create_all(tables = [data_table.__table__])
            self.measurement_session.data_table = self.measurement_session.id
            self.session.add(self.measurement_session)
            self.session.commit()          
        except Exception as e:
            logger.warning(e) 
            
        
        
                                                                              
if __name__ is '__main__':
    s = SessionManager(dsn = 'postgresql://petermoller:lotus123@localhost/unimeas')     