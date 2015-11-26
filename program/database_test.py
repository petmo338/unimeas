__author__ = 'petmo_000'
# -*- coding: utf-8 -*-
from traits.api import HasTraits, Bool, Int, List, Float, Instance, Any,\
    Str, Button, on_trait_change, Dict
from traitsui.api import Item, View, Group, HGroup, Handler, \
    ButtonEditor, EnumEditor
from pyface.timer.api import Timer
from database import session_manager as db
from database.measurement_session import MeasurementSession
import numpy as np
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-2s %(name)-12s %(levelname)-8s %(message)s',
                    filename=__name__ + '.log')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(asctime)-2s %(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger().addHandler(console)
logger = logging.getLogger(__name__)
# if __name__ is '__main__':
logger.info('Starting')


class DatabaseTestHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        info.object.start_stop(False)
        return


class DatabaseTest(HasTraits):

    selected_user = Int
    available_users = Dict()
    selected_instrument = Int
    available_instruments = Dict()
    selected_measurement_class = Int
    available_measurement_classes = Dict()
    measurement_session = Int
    available_measurement_sessions = Dict()
    active_measurement_session = Instance(MeasurementSession)
    session = Instance(db.SessionManager)
    start = Button
    button_label = Str('Start')
    running = False
    sample_nr = Int

    traits_view = View(Item('selected_user', editor=EnumEditor(name='available_users')),
                       Item('selected_instrument', editor=EnumEditor(name='available_instruments')),
                       Item('selected_measurement_class', editor=EnumEditor(name='available_measurement_classes')),
                       Item('measurement_session', editor=EnumEditor(name='available_measurement_sessions')),

                       Item('start', editor=ButtonEditor(label_value='button_label')), handler=DatabaseTestHandler)

    def __init__(self):
        self.session = db.SessionManager(dsn='postgresql://sensor:sensor@pc15389.sensor.lab/unimeas')
        self.on_trait_change(self.update_available_sessions, 'selected+')

    def _available_users_default(self):
        retval = self.session.get_users()
        d = dict()
        d[0] = ''
        for user in retval:
            d[user.id] = user.fullname
        return d

    def _available_instruments_default(self):
        retval = self.session.get_instruments()
        d = dict()
        d[0] = ''
        for instrument in retval:
            d[instrument.id] = instrument.model + ', ' + instrument.serial
        return d

    def _available_measurement_classes_default(self):
        retval = self.session.get_measurement_classes()
        d = dict()
        d[0] = ''
        for measurement_class in retval:
            d[measurement_class.id] = measurement_class.name
        return d

    def _available_measurement_sessions_default(self):
        retval = self.session.get_measurement_sessions()
        d = dict()
        d['None'] = ''
        for measurement_session in retval:
            d[measurement_session.id] = measurement_session.name
        return d

    def _measurement_session_changed(self, new):
        self.active_measurement_session = self.session.open_session(new)

#    @on_trait_change('selected_+')
    def update_available_sessions(self):
        logger.info('on_trait_cahange, selected...')
        d = {}
        if self.selected_user != 0:
            d['user'] = self.selected_user
        if self.selected_instrument != 0:
            d['instrument_id'] = self.selected_instrument
        if self.selected_measurement_class != 0:
            d['measurement_class_id'] = self.selected_measurement_class
        measurement_sessions = self.session.get_measurement_sessions(**d)
        d = {}
        for measurement_session in measurement_sessions:
            d[measurement_session.id] = measurement_session.name
        self.available_measurement_sessions = d

    def _start_fired(self):
        if self.running:
            self.button_label = 'Start'
            self.running = False
            if self.timer is not None:
                self.timer.Stop()
                self.timer = None

            # self.stop()
        else:
            if self.active_measurement_session is None:
                return
            self.button_label = 'Stop'
            self.running = True
            self.sample_nr = 0
            self.timer = Timer(1000, self._onTimer)

            # self.start()

    def _onTimer(self):
        self.sample_nr += 1
        self.active_measurement_session.add_data({'samplenr': self.sample_nr, 'voltage': np.log(self.sample_nr), 'temp': 321.3})

    def start_stop(self, starting):
        if starting is False and self.running is True:
            self._start_fired()



database_test = DatabaseTest()
#database_test.configure_traits()
# s = db.SessionManager(dsn='postgresql://sensor:sensor@localhost/unimeas')
# # s = SessionManager()
#database_test.session.add_user('mikan', u'Mike Andersson')
#database_test.session.add_user('jenser', u'Jens')
#database_test.session.add_user('donpu', u'Donatella')
#database_test.session.add_instrument('Sourcemeter 2601A', '32345', 'SourceMeter')
#database_test.session.add_instrument('Keitley 2100', '32345', 'Multimeter')
#database_test.session.add_instrument('Bontoon', '32e345656', 'Cap meter')
#database_test.session.add_instrument('NiDAQ', '3234522', ' bliblib')
#database_test.session.add_measurement_class('Sourcemeter over time', 'samplenr, time, voltage, current, resistance, temp, gascol', 0, 'bla_desc', 'TIME')
#database_test.session.add_measurement_class('Generic I/V 0 to 5', '', 501, '0 to 5 volts in 0.01V steps', 'INTERVAL')
#database_test.session.add_measurement_class('Resistance over time', 'samplenr, time, resistance, temp, gascol', 0, 'bla_desc', 'INTERVAL')
#database_test.session.add_measurement_class('Generic C/V -5 to 5',  '', 1001, '-5 to 5V bias sweep in 0.01V steps', 'INTERVAL')

#ms = database_test.session.create_session(name='SrTiO3 Fet 2', instrument=1, user=1, description='500->600 deg, 3V, Ir', sensor_id='W3C24R12-2',
#                    measurement_class=1, gasmixer_system='GM2')
#ms = database_test.session.create_session(name='SrTiO3 cap powder', instrument=3, user=2, description='Test on cap with SrTiO3 powder', sensor_id='Nja',
#                    measurement_class=1, gasmixer_system='GM1')
#ms = database_test.session.create_session(name='test5_name', instrument=4, user=2, description='my_desc4', sensor_id='sensor_id_text4',
#                    measurement_class=3, gasmixer_system='GM4')
#ms = database_test.session.create_session(name='test6_name', instrument=3, user=3, description='my_desc5', sensor_id='sensor_id_text5',
#                    measurement_class=1, gasmixer_system='GM4')
#ms = database_test.session.create_session(name='test7_name', instrument=4, user=2, description='my_desc2', sensor_id='sensor_id_text6',
#                    measurement_class=3, gasmixer_system='GM3')
ms = database_test.session.create_session(name='tfdsfsname', instrument=1, user=1, description='my_desc2', sensor_id='sensor_id_text7',
                    measurement_class=2, gasmixer_system='GM3')
# ms.engine = s.engine
# ms.create_data_table()
