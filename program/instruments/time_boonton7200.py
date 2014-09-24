from i_instrument import IInstrument
from traits.api import HasTraits, Instance, Float, Dict, \
    List, Unicode, Str, Int,Event, Bool
from traitsui.api import View, Item, ButtonEditor, Handler, EnumEditor, RangeEditor, Group, TableEditor
from traitsui.table_column import NumericColumn
from pyface.timer.api import Timer
from ..generic_popup_message import GenericPopupMessage
import visa
from serial_util import SerialUtil
from time import time
import logging
visa.logger.level=logging.ERROR
logger = logging.getLogger(__name__)

DEFAULT_START_FREQUENCY = int(1000)
DEFAULT_STOP_FREQUENCY = int(1e6)
INSTRUMENT_IDENTIFIER = ['Model', '7200']
class ViewHandler(Handler):
    def closed(self, info, is_ok):
#        logger.debug('Closing')
        if info.object.timer is not None:
            info.object.timer.Stop()


class TableEntry(HasTraits):

    time = Int
    bias = Float(0.0)
    remaining = Int

table_editor = TableEditor(
    columns = [ NumericColumn( name = 'time'),
                NumericColumn( name = 'bias'),
                NumericColumn( name = 'remaining')],
    deletable   = True,
    sort_model  = False,
    auto_size   = True,
    orientation = 'vertical',
    edit_view   = None,
    auto_add = False,
    show_toolbar = True,
    sortable = False,
    row_factory = TableEntry )

#@provides(IInstrument)
class Boonton7200(HasTraits):

    name = Unicode('Boonton7200')
    measurement_info = Dict()
    x_units = Dict({0: 'SampleNumber', 1: 'Time'})
    y_units = Dict({0: 'Capacitance'})

    acquired_data = List(Dict)

    start_stop = Event
    running = Bool

    output_channels = Dict({0: 'cap', 1: 'bias'})

    enabled_channels = List(Bool)

    timer = Instance(Timer)
    timer_dormant = Bool(False)
    update_interval = Float(0.5)

    start_time = Float

#    bias = Range(-10.0, 10.0, 0.0)
    bias = Float(0.0)
    current_capacitance = Float
    current_bias = Float

    sample_nr = Int(0)
    start_stop = Event
    button_label = Str('Start')

    bias_low_limit = Float(-10.0)    # Instrument supports -100V to +100V
    bias_high_limit = Float(10.0)

    bias_table = List(TableEntry)
    bias_table_current_row = Int(0)
    bias_table_enable = Bool(False)
    stop_meas_after_last_row = Bool(False)
    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    visa_resource = Instance(visa.ResourceManager, ())
    instrument = Instance(visa.Resource)


    traits_view = View(Item('selected_device', label = 'Device', \
                                editor = EnumEditor(name='_available_devices_map'), \
                                enabled_when='not running'),
                        Item('update_interval', enabled_when='not running'),
                        Item('bias', editor = RangeEditor(is_float = True, low_name = 'bias_low_limit', high_name = 'bias_high_limit')),
                        Group(Item('current_capacitance', enabled_when = 'False'),
                                Item('current_bias', enabled_when = 'False'),
                                Item('sample_nr', enabled_when = 'False'),
                                label = 'Measurement', show_border = True),

                        Group(Item('bias_table_enable'),
                                Item('stop_meas_after_last_row'),
                            Item( 'bias_table',
                                show_label  = False,
#                               label       = 'right-click to edit',
                                editor      = table_editor,
                                enabled_when = 'not running and bias_table_enable'),
                            show_border = True),
                        Item('start_stop', label = 'Start/Stop Acqusistion',
                                editor = ButtonEditor(label_value='button_label')),
                        handler = ViewHandler)

    def instrument_init(self):
        if self.instrument is not None:
            self.instrument.write('BI' + str(self.bias))

    def instrument_stop(self):
        if self.instrument is not None:
            pass

    def start(self):
        self.button_label = 'Stop'
        self.sample_nr = 0
        self.running = True
        self.instrument_init()
        self.start_time = time()
        self.bias_table_current_row = 0
        self._row_changed(0)
        if self.timer is None:
            self.timer = Timer(self.update_interval * 1000, self._onTimer)
        else:
            self.timer.Start(self.update_interval * 1000)

    def stop(self):
        if self.timer is not None:
            self.timer.Stop()
        self.button_label = 'Start'
        self.running = False
        self.timer_dormant = False
        self.instrument_stop()

    def _onTimer(self):
#        self.timer.Stop()
        self.timer_dormant = True
        d = dict()
        values = self.instrument.query_ascii_values('TM')
        self.current_capacitance =  values[0] * 1e-12
        self.current_bias = values[2]
        d[self.output_channels[0]] = (dict({self.x_units[0] : self.sample_nr,
                                            self.x_units[1] :  time() - self.start_time}),
                                        dict({self.y_units[0] : self.current_capacitance}))
        d[self.output_channels[1]] = (dict({self.x_units[0] : self.sample_nr,
                                            self.x_units[1] :  time() - self.start_time}),
                                        dict({self.y_units[0] : self.bias}))
        self.sample_nr += 1
#        self.timer.Start(self.update_interval * 1000)
        self.timer_dormant = False
        self.acquired_data.append(d)

        if self.bias_table_enable:
            if self.bias_table_current_row < len(self.bias_table):
                row_time = time() - self.row_start_time
                self.bias_table[self.bias_table_current_row].remaining = int(self.bias_table[self.bias_table_current_row].time - row_time)
                if self.bias_table[self.bias_table_current_row].remaining < 1:
                    self.bias_table_current_row += 1
                    self._row_changed(self.bias_table[self.bias_table_current_row - 1].time - row_time)


    def _row_changed(self, remainder):
        self.row_start_time = time() + remainder
#        logging.getLogger(__name__).info('self.row_start_time: %f', self.row_start_time)
        if self.bias_table_current_row >= len(self.bias_table):
            if self.stop_meas_after_last_row:
                self.start_stop = True
            return
        self.bias = self.bias_table[self.bias_table_current_row].bias

    def _start_stop_fired(self):
        if self.instrument is None:
            return
        if self.timer is None:
            self.start()
            return
        if self.timer.isActive() or self.timer_dormant:
            self.stop()
        else:
            self.start()

    def _selected_device_changed(self, new):
        logger.info('New instrument %s', new)
        if self.instrument is not None:
            self.instrument.close()
        if new is not '':
            self.instrument = SerialUtil.open(new, self.visa_resource, command = 'ID')
            if self.instrument is None:
                GenericPopupMessage(message ='Error opening ' + new).edit_traits()
                self.instrument = None
                self.selected_device = ''

    def _selected_device_default(self):
        try:
            device = self._available_devices_map.items()[0][0]
        except IndexError:
            return ''
        self._selected_device_changed(device)
        return device

    def _enabled_channels_default(self):
        return [True, False]

    def _bias_table_default(self):
        return [TableEntry(time = 10, bias = 0.0, remaining = 0),
                TableEntry(time = 10, bias = 0.5, remaining = 0)]

    def __available_devices_map_default(self):
        try:
            instruments_info = self.visa_resource.list_resources_info()
        except visa.VisaIOError:
            return {}
        d = {}
        candidates = [n for n in instruments_info.values() if n.resource_name.upper().startswith('GPIB')]
        d.update(SerialUtil.probe(candidates, self.visa_resource, INSTRUMENT_IDENTIFIER, command = 'ID'))
        return d


    def _bias_changed(self, new):
        if self.instrument is not None:
            self.instrument.write('BI' + str(new))

if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    s = Boonton7200()
    s.configure_traits()
