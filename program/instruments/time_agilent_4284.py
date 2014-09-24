from i_instrument import IInstrument
from traits.api import HasTraits, Instance, Float, Dict, \
    List, Unicode, Str, Int, on_trait_change, \
   Event, Bool, Enum
from traitsui.api import View, Item, Group, ButtonEditor, Handler, EnumEditor, TableEditor

from traitsui.table_column import NumericColumn
from pyface.timer.api import Timer
from ..generic_popup_message import GenericPopupMessage
import visa
from serial_util import SerialUtil
from time import time
import logging
visa.logger.level=logging.ERROR
logger = logging.getLogger(__name__)


DEFAULT_FREQUENCY = int(10000)
INSTRUMENT_IDENTIFIER = ['HEWLETT', '4284A']
class ViewHandler(Handler):
    def closed(self, info, is_ok):
#        logger.debug('Closing')
        if info.object.timer is not None:
            info.object.timer.Stop()

class TableEntry(HasTraits):

    time = Int
    bias = Float(0.0)
    freq = Int
    v_osc = Float(0.5)
    remaining = Int

table_editor = TableEditor(
    columns = [ NumericColumn( name = 'time'),
                NumericColumn( name = 'bias'),
                NumericColumn( name = 'freq'),
                NumericColumn( name = 'v_osc'),
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
class Agilent4284(HasTraits):



    name = Unicode('Agilent 4284')
    measurement_info = Dict()
    x_units = Dict({0: 'SampleNumber', 1: 'Time'})
    y_units = Dict({0: 'Capacitance',  1: 'Frequency', 2: 'BIAS'})

    acquired_data = List(Dict)
    output_channels = Dict({0: 'cap'})
#    measurement_mode = Int
    start_stop = Event
    running = Bool

    enabled_channels = List(Bool)

    timer = Instance(Timer)
    timer_dormant = Bool(False)
    update_interval = Float(0.5)

    frequency = Int(DEFAULT_FREQUENCY)
    bias = Float(0.0)
    osc_level = Float(0.5)

    mode = Enum('CpD', 'CpQ','CpG', 'CpRp', 'CsD', 'CsQ', 'CsRs')
    current_frequency = Float
    current_capacitance = Float
    current_bias = Float
    start_time = Float

    output_list = List
    sample_nr = Int(0)
    start_stop = Event
    button_label = Str('Start')

    available_frequencies = List(Int)

    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    visa_resource = Instance(visa.ResourceManager, ())
    instrument = Instance(visa.Resource)

#    instrument = Instance(visa.Instrument)

    traits_view = View(Item('selected_device', label = 'Device', \
                                editor = EnumEditor(name='_available_devices_map'), \
                                enabled_when='not running'),
                        Group(Item('frequency', enabled_when='not running'),
                            Item('bias'), Item('osc_level'),
                            Item('mode', enabled_when='not running'),
                            Item('current_capacitance', style = 'readonly'),
                            Item('current_frequency', style = 'readonly'),
                            Item('current_bias', style = 'readonly'),
                            label='Instrument setting', show_border = True, enabled_when='not running'),
                        Item('update_interval'),
                        Item('start_stop', label = 'Start/Stop Acqusistion',
                                editor = ButtonEditor(label_value='button_label')),
                        handler = ViewHandler)

    def instrument_init(self):
        if self.instrument is not None:
            self.instrument.write('OUTP:HPOW 1')
            self.instrument.write('VOLT ' + str(self.osc_level))
            self.instrument.write('BIAS:VOLT ' + str(self.bias))
            self.instrument.write('BIAS:STAT 1')
            self.instrument.write('FUNC:IMP ' + str(self.mode))
            self.instrument.write('FREQ ' + str(self.frequency))

    def instrument_stop(self):
        if self.instrument is not None:
            self.instrument.write('BIAS:STAT 0')

    def start(self):
#        self._generate_output_list()
        self.button_label = 'Stop'
        self.sample_nr = 0
        self.running = True
        self.instrument_init()
        self.start_time = time()
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
        values = self.instrument.query_ascii_values('FETC:IMP?')
        self.current_bias = float(self.instrument.query('BIAS:VOLT?'))

        self.current_frequency = float(self.instrument.query('FREQ?'))
        self.current_capacitance =  values[0]
        d[self.output_channels[0]] = (dict({self.x_units[0] : self.sample_nr,
                                            self.x_units[1] : time() - self.start_time}),
                                        dict({self.y_units[0] : self.current_capacitance,
                                            self.y_units[1] : self.current_frequency,
                                            self.y_units[2] : self.current_bias}))
        self.sample_nr += 1
        self.timer_dormant = False
        self.acquired_data.append(d)


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

    @on_trait_change('stop_frequency, start_frequency')
    def _frequency_checker(self, obj, name, old, new):
        try:
            index = self.available_frequencies.index(new)
        except ValueError:
            if new > 5000:   # Most freq are below 5kHz in the table, search from 1 MHz and down here
                index = len(self.available_frequencies) - 1
                while new <= self.available_frequencies[index]:
                    index -= 1
            else:
                index = 0
                while new >= self.available_frequencies[index]:
                    index += 1
        finally:
            if name == 'start_frequency':
                self.valid_start_frequency = self.available_frequencies[index]
            elif name == 'stop_frequency':
                self.valid_stop_frequency = self.available_frequencies[index]

    def _selected_device_changed(self, new):
        logger.info('New instrument %s', new)
        if self.instrument is not None:
            self.instrument.close()
        if new is not '':
            self.instrument = SerialUtil.open(new, self.visa_resource)
            if self.instrument is None:
                GenericPopupMessage(message ='Error opening ' + new).edit_traits()
                self.instrument = None
                self.selected_device = ''

    def _enabled_channels_default(self):
        return [True]

    def __available_devices_map_default(self):
        try:
            instruments_info = self.visa_resource.list_resources_info()
        except visa.VisaIOError:
            return {}

        d = {}
        candidates = [n for n in instruments_info.values() if n.resource_name.upper().startswith('GPIB')]
        d.update(SerialUtil.probe(candidates, self.visa_resource, INSTRUMENT_IDENTIFIER))
        return d

    def _selected_device_default(self):
        try:
            device = self._available_devices_map.items()[0][0]
        except IndexError:
            return ''
        self._selected_device_changed(device)
        return device

    def _available_frequencies_default(self):
        l = []
        ll = []
        for n in xrange(13, 3751):
            ll.append(int(1000 * (60.0 / n)))
            ll.append(int(1000 * (62.5 / n)))
            ll.append(int(1000 * (75.0 / n)))
            l += [e for e in ll if e >= 20 and e <= 5e3]
        ll = []
        for n in xrange(13, 30):
            ll.append(int(1000 * (120.0 / n)))
            ll.append(int(1000 * (125.0 / n)))
            ll.append(int(1000 * (150.0 / n)))
            l += [e for e in ll if e > 5e3 and e <= 10e3]
        ll = []
        for n in xrange(13, 30):
            ll.append(int(1000 * (240.0 / n)))
            ll.append(int(1000 * (250.0 / n)))
            ll.append(int(1000 * (300.0 / n)))
            l += [e for e in ll if e > 10e3 and e <= 20e3]
        ll = []
        for n in xrange(2, 30):
            ll.append(int(1000 * (480.0 / n)))
            ll.append(int(1000 * (500.0 / n)))
            ll.append(int(1000 * (600.0 / n)))
            l += [e for e in ll if e > 20e3 and e <= 250e3]
        ll = []
        for n in xrange(2, 5):
            ll.append(int(1000 * (960.0 / n)))
            ll.append(int(1000 * (1000.0 / n)))
            ll.append(int(1000 * (1200.0 / n)))
            l += [e for e in ll if e > 250e3 and e <= 500e3]
        ll = []
        for n in xrange(2, 5):
            ll.append(int(1000 * (1920.0 / n)))
            ll.append(int(1000 * (2000.0 / n)))
            ll.append(int(1000 * (2400.0 / n)))
            l += [e for e in ll if e > 500e3 and e <= 1000e3]
        l = list(set(l))
        l.sort()
        return l


if __name__ == '__main__':
    if __package__  is None:
        __package__ = "instruments"
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    s = Agilent4284()
    s.configure_traits()
