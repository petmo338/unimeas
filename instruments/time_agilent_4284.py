from i_instrument import IInstrument
from traits.api import HasTraits, Instance, Float, Dict, \
    List, Unicode, Str, Int, on_trait_change,\
   Event, Bool, Enum
from traitsui.api import View, Item, Group, ButtonEditor, Handler, EnumEditor, TableEditor
import traits.has_traits
#traits.has_traits.CHECK_INTERFACES = 2
from traitsui.table_column import NumericColumn
from pyface.timer.api import Timer
from pyvisa import visa
from time import time
import logging

logger = logging.getLogger(__name__)

DEFAULT_FREQUENCY = int(10000)

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
    current_frequency = Int
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
    instrument = Instance(visa.Instrument)

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

#    def _generate_output_list(self):
#        self.output_list = []
#        if self.measurement_mode is 0:
#            if self.valid_stop_frequency > self.valid_start_frequency:
#                self.output_list = self.available_frequencies[self.available_frequencies.index(self.valid_start_frequency):
#                                                                self.available_frequencies.index(self.valid_stop_frequency) + 1]
#            else:
#                self.output_list = self.available_frequencies[self.available_frequencies.index(self.valid_stop_frequency):
#                                                                self.available_frequencies.index(self.valid_start_frequency) + 1]
#                self.output_list.reverse()
#
#        elif self.measurement_mode is 1:
#            diff = self.stop_bias - self.start_bias
#            if diff > 0:
#                for i in xrange(int((diff) / self.step_bias) + 1):
#                    self.output_list.append(self.start_bias + self.step_bias * i)
#            elif diff < 0:
#                for i in xrange(int(abs(diff) / self.step_bias) + 1):
#                    self.output_list.append(self.start_bias - abs(self.step_bias) * i)
#            else:
#                self.output_list.append(self.start_bias)
##        logger.info('output_list %s', self.output_list)

    def _onTimer(self):
#        self.timer.Stop()
        self.timer_dormant = True
        d = dict()
        values = self.instrument.ask_for_values('FETC:IMP?')
        self.current_bias = float(self.instrument.ask('BIAS:VOLT?'))

        self.current_frequency = float(self.instrument.ask('FREQ?'))
        self.current_capacitance =  values[0]
        d[self.output_channels[0]] = (dict({self.x_units[0] : self.current_frequency,
                                            self.x_units[1] : time() - self.start_time}),
                                        dict({self.y_units[0] : self.current_capacitance,
                                            self.y_units[1] : self.current_frequency,
                                            self.y_units[2] : self.current_bias}))
        self.sample_nr += 1
#        self.timer.Start(self.update_interval * 1000)
        self.timer_dormant = False
        self.acquired_data.append(d)
        try:
            command = ''
            if self.measurement_mode is 0:
                command = 'FREQ ' + str(self.output_list[self.sample_nr])
            elif self.measurement_mode is 1:
                command = 'BIAS:VOLT ' + str(self.output_list[self.sample_nr])
            self.instrument.write(command)
        except IndexError:
            self.start_stop = True

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
#

#    def _stop_frequency_changed(self, new):
#
#        try:
#            index = self.available_frequencies.index(new)
#        except ValueError:
#            index = len(self.available_frequencies) - 1
#            while new <= self.available_frequencies[index]:
#                index -= 1
#        finally:
#            logger.info('Index: %s', index)
#            self.valid_stop_frequency = int(self.available_frequencies[index])
#
    def _selected_device_changed(self, new):
        self.instrument = visa.Instrument(new, timeout = 2)
        self.instrument.write('*RST')

    def _enabled_channels_default(self):
        return [True]

    def __available_devices_map_default(self):
        try:
            instruments = visa.get_instruments_list()
        except visa.VisaIOError:
            return {}

        d = dict()
        candidates = [n for n in instruments if n.startswith('GPIB')]
        for instrument in candidates:
            temp_inst = visa.instrument(instrument)
            model = temp_inst.ask('*IDN?')
            if model.find('HEWLETT') == 0 and model.find('4284A') > 0:
                d[instrument] = model

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
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    s = Agilent4284()
    s.configure_traits()
