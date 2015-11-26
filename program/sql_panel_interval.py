from traits.api import HasTraits, Bool, Instance, Button, List, \
    Unicode, Str
from traitsui.api import EnumEditor, Item, View, HGroup, VGroup, spring, Handler
from traitsui.menu import OKButton, CancelButton
from generic_popup_message import GenericPopupMessage
from database import SessionManager
import time
import logging
logger = logging.getLogger(__name__)

class CreateMeasurementPopup(Handler):
    measurement_name = Str
    measurement_description = Str
    prepend_timestamp = Bool(True)

    traits_view = View(Item('measurement_name'),
                       Item('prepend_timestamp'),
                       Item('measurement_description', style = 'custom'),
                       buttons = [OKButton, CancelButton], kind = 'modal')

    def _measurement_name_default(self):
        localtime   = time.localtime()
        return time.strftime("%Y%m%d_%H%M%S_", localtime)

    def _prepend_timestamp_changed(self, old, new):
        if new == True:
            self.measurement_name = self._measurement_name_default() + self.measurement_name
        else:
            self.measurement_name = ''

class SQLPanel(HasTraits):

    ############ Panel Interface ###########################3

    pane_name = Str('Save Configuration')
    pane_id = Str('sensorscience.unimeas.sql_pane_interval')

#    database_wrapper = Instance(SQLWrapper)
#    instrument = Instance(IInstrument)
    selected_user = Str
    new_measurement = Button
    measurement_name = Str
    measurement_description = Str
    save_in_database = Bool(False)


    running = Bool

    available_users = List(Unicode)
    available_measurements = List(Unicode)


    traits_view = View(VGroup(HGroup(Item('save_in_database', enabled_when = 'not running'),
                            Item('selected_user',
                            editor=EnumEditor(name='available_users'),
                            enabled_when = 'not running and save_in_database'), spring,
                        Item('new_measurement', show_label=False,  enabled_when = 'not running and save_in_database')),
                        Item('measurement_name',
                            editor=EnumEditor(name='available_measurements'),
                            enabled_when = 'not running and save_in_database'),
                        Item('measurement_description', style = 'custom')))

    def _new_measurement_fired(self):
        popup = CreateMeasurementPopup()
        ui = popup.edit_traits()
        if ui.result is True:
            self.is_new = True
            self.available_measurements.append(popup.measurement_name)
            self.measurement_name = popup.measurement_name
            self.measurement_description = popup.measurement_description
            self.database_wrapper.set_table(self.measurement_name,
                    self.measurement_description)




    def _available_users_default(self):
        return []

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

    def _selected_user_changed(self, old, new):
        if new == '':
            self.save_in_database = False
        else:
            self.save_in_database = True
            if not self.database_wrapper.change_database(new):
                logger.error('Unable to connect to database %s', new)
                self.save_in_database = False
                self.available_measurements = []
                return
            self.available_measurements = self.database_wrapper.get_measurements()
            self.available_measurements.insert(0, '')


    def _save_in_database_changed(self, new):
        if new:
            self.database_wrapper = SQLWrapper()
            self.available_users = self.database_wrapper.get_users()
        else:
            del self.database_wrapper
            self.available_users = []

#    @on_trait_change('instrument.sample_number')
    def add_data(self, data):
        if self.save_in_database:
            self.database_wrapper.insert_data(data)


    def start_stop(self, active_instrument):
        self.running = active_instrument.running
        if self.running and self.save_in_database:
            if len(self.measurement_name) == 0:
                GenericPopupMessage(message = 'No measurement selected').edit_traits()
                self.save_in_database = False
            else:
                if self.database_wrapper.get_description(self.measurement_name) is not self.measurement_description:
                            self.database_wrapper.set_table(self.measurement_name, self.measurement_description)
                self.database_wrapper.add_columns([active_instrument.x_units[0] +active_instrument.sweep_name,\
                                                    active_instrument.y_units[0] + active_instrument.sweep_name])



if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    s = SQLPanel()
    s.configure_traits()
