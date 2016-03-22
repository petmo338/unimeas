from traits.api import HasTraits, Bool, Instance, Button, List, \
    Unicode, Str
from traitsui.api import EnumEditor, Item, View, HGroup, VGroup, spring, Handler, Label
from traitsui.menu import OKButton, CancelButton
from generic_popup_message import GenericPopupMessage
from database.session_manager import SessionManager
from database.measurement_session import MeasurementSession
import time
import logging
import pickle
from instruments.i_instrument import IInstrument
logger = logging.getLogger(__name__)

class CreateMeasurementPopup(Handler):
    class_name = Str
    class_description = Str

    traits_view = View(Label('Save current instrument settings as a template.'),
                       Item('class_name'),
                       Item('class_description', style = 'custom'),
                       buttons = [OKButton, CancelButton], kind = 'modal')

class SQLPanel(HasTraits):

    ############ Panel Interface ###########################3

    pane_name = Str('Save Configuration')
    pane_id = Str('sensorscience.unimeas.sql_pane_interval')

#    database_wrapper = Instance(SQLWrapper)
#    instrument = Instance(IInstrument)
    selected_user = Str
    save_instrument_config = Button
    measurement_name = Str
    measurement_description = Str
    save_in_database = Bool(False)
    session_manager = Instance(SessionManager)
    active_instrument = Instance(IInstrument)

    running = Bool

    available_users = List(Unicode)
    available_measurements = List(Unicode)


    traits_view = View(VGroup(HGroup(Item('save_in_database', enabled_when = 'not running'),
                            Item('selected_user',
                            editor=EnumEditor(name='available_users'),
                            enabled_when = 'True'), spring,
                        Item('save_instrument_config', show_label=False,  enabled_when = 'active_instruments is not None')),
                        Item('measurement_name',
                            editor=EnumEditor(name='available_measurements'),
                            enabled_when = 'not running and save_in_database'),
                        Item('measurement_description', style = 'custom')))

    def __init__(self):
        self.session_manager = SessionManager('postgresql://sensor:sensor@applsens.sensor.lab:5432/unimeas')
        super(SQLPanel, self).__init__()

    def _save_instrument_config_fired(self):
        popup = CreateMeasurementPopup()
        ui = popup.edit_traits()
        if ui.result is True:
            self.session_manager.add_measurement_class(popup.class_name, pickle.dumps(self.active_instrument).encode('zip').encode('base64').strip(),
                                                       self.active_instrument.get_nr_of_samples(), popup.class_description,
                                                       'INTERVAL')
    #         self.is_new = True
    #         self.available_measurements.append(popup.measurement_name)
    #         self.measurement_name = popup.measurement_name
    #         self.measurement_description = popup.measurement_description
    #         self.database_wrapper.set_table(self.measurement_name,
    #                 self.measurement_description)

    def _available_users_default(self):
        l = [u.ifmid for u in self.session_manager.get_users()]
        return l

    def _measurement_name_default(self):
        return ''

    def _measurement_name_changed(self, new):
        if hasattr(self, 'is_new'):
            if not self.is_new:
                self.measurement_description = self.database_wrapper.get_description(new)
            else:
                self.is_new = False
        else:
            self.measurement_description = self.database_wrapper.get_description(new)

        self.database_wrapper.set_table(new, self.measurement_description)

#    @on_trait_change('instrument.sample_number')
    def add_data(self, data):
        self.measurement_session.add_data(data.update({'sample_nr': self.active_instrument.sample_nr}))

    def start_stop(self, active_instrument):
        self.running = active_instrument.running
        if self.running and self.save_in_database:
            if self.measurement_session is None:
                self.measurement_session = self.session_manager.create_session(name='some name', instrument='some isnstr.',
                                                                               user=self.selected_user, description='some desc',
                                                                               sensor_id='sensor ID', gasmixer_system='GM2',
                                                                               measurement_class_id=2)
            self.measurement_session.new_run([self.active_instrument.x_units[0], self.active_instrument.y_units[0]])

    def set_active_instrument(self, instrument):
        self.active_instrument = instrument
        self.available_classes = self.session_manager.get_measurement_classes()

if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    s = SQLPanel()
    s.configure_traits()
