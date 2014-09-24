from i_instrument import IInstrument
from enthought.traits.api import HasTraits, Instance, Float, Dict, \
    List,  Unicode, Str, Int, on_trait_change,\
   Event, Bool, Enum
from traitsui.api import View, Item, Group, ButtonEditor, Handler, EnumEditor
from ..generic_popup_message import GenericPopupMessage
from serial_util import SerialUtil
from pyface.timer.api import Timer
import visa
#import numpy as np
import logging
visa.logger.level=logging.ERROR
logger = logging.getLogger(__name__)


DEFAULT_START_FREQUENCY = int(1000)
DEFAULT_STOP_FREQUENCY = int(1e6)
INSTRUMENT_IDENTIFIER = ['HEWLETT', '4284A']
class ViewHandler(Handler):
    def closed(self, info, is_ok):
#        logger.debug('Closing')
        if info.object.timer is not None:
            info.object.timer.Stop()

#@provides(IInstrument)
class Agilent4284(HasTraits):



    name = Unicode('Agilent 4284')

    x_units = Dict({0: 'Voltage'})
    y_units = Dict({0: 'Capacitance'})
    measurement_info = Dict()
    acquired_data = List(Dict)
    output_channels = Dict({0: 'C/F', 1: 'C/V'})
    measurement_mode = Int
    start_stop = Event
    running = Bool


    enabled_channels = List(Bool)

    timer = Instance(Timer)
    timer_dormant = Bool(False)
    update_interval = Float(0.5)

    start_frequency = Int
    stop_frequency = Int
    start_bias = Float(-5.0)
    stop_bias = Float(5.0)
    step_bias = Float(0.05)
    keep_bias_on = Bool(False)
    cv_frequency = Int(DEFAULT_STOP_FREQUENCY)

    bias = Float(1.0)
    mode = Enum('CpD', 'CpQ','CpG', 'CpRp', 'CsD', 'CsQ', 'CsRs')
    current_frequency = Int
    current_capacitance = Float
    current_bias = Float

    valid_start_frequency = Int(DEFAULT_START_FREQUENCY)
    valid_stop_frequency = Int(DEFAULT_STOP_FREQUENCY)

    output_list = List
    use_log_steps = Bool(False)
    sample_nr = Int(0)
    start_stop = Event
    button_label = Str('Start')
    sweep_name = Str



    available_frequencies = List(Int)

    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    visa_resource = Instance(visa.ResourceManager, ())
    instrument = Instance(visa.Resource)

    traits_view = View(Item('selected_device', label = 'Device', \
                                editor = EnumEditor(name='_available_devices_map'), \
                                enabled_when='not running'),
                        Item('measurement_mode', editor=EnumEditor(name='output_channels'), enabled_when = 'not running'),
                        Group(Item('start_frequency', enabled_when='not running'),
                            Item('stop_frequency', enabled_when='not running'),
                            Item('bias'), Item('keep_bias_on'),
                            Item('mode', enabled_when='not running'),
                            Item('current_frequency', enabled_when='False'),
                            Item('current_capacitance', enabled_when='False'),
                            label='C/F', show_border = True, enabled_when = 'measurement_mode == 0'),
                        Group(Item('start_bias', enabled_when='not running'),
                            Item('stop_bias', enabled_when='not running'),
                            Item('step_bias', enabled_when='not running'),
                            Item('cv_frequency', label = 'Frequency'), Item('mode', enabled_when='not running'),
                            Item('current_bias', enabled_when='False'),
                            Item('current_capacitance', enabled_when='False'),
                            label='C/V', show_border = True, enabled_when = 'measurement_mode == 1'),

                        Item('update_interval'),
                        Item('sweep_name'),
                        Item('start_stop', label = 'Start/Stop Acqusistion',
                                editor = ButtonEditor(label_value='button_label')),
                        handler = ViewHandler)

    def instrument_init(self):
        if self.instrument is not None:
            self.instrument.write('OUTP:HPOW 1')
            self.instrument.write('VOLT 0.5')
            if self.measurement_mode is 0:
                self.instrument.write('BIAS:VOLT ' + str(self.bias))
                self.instrument.write('BIAS:STAT 1')
                self.instrument.write('FUNC:IMP ' + str(self.mode))
                self.instrument.write('FUNC:IMP:RANG:AUTO ON')
                self.instrument.write('FREQ ' + str(self.start_frequency))
            elif self.measurement_mode is 1:
                self.instrument.write('BIAS:VOLT ' + str(self.start_bias))
                self.instrument.write('BIAS:STAT 1')
                self.instrument.write('FUNC:IMP ' + str(self.mode))
                self.instrument.write('FUNC:IMP:RANG:AUTO ON')
                self.instrument.write('FREQ ' + str(self.cv_frequency))


    def instrument_stop(self):
        if self.instrument is not None:
            if not self.keep_bias_on:
                self.instrument.write('BIAS:STAT 0')
            self.instrument.write('VOLT 0.5')


    def start(self):
        self._generate_output_list()
        self.button_label = 'Stop'

        if self.measurement_mode is 0:
            self.measurement_info = {'name': self.sweep_name,
                                'start_frequency': self.start_frequency,
                                'stop_frequency': self.stop_frequency,
                                'bias': self.bias
                                }
        else:
            self.measurement_info = {'name': self.sweep_name,
                                'start_bias': self.start_frequency,
                                'stop_bias': self.stop_frequency,
                                'step_bias': self.step_bias,
                                'frequency': self.cv_frequency
                                }
        if len(self.measurement_info['name']) is 0:
            self.measurement_info.pop('name')
        self.sample_nr = 0
        self.running = True
        self.instrument_init()
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

    def _generate_output_list(self):
        self.output_list = []
        if self.measurement_mode is 0:
            if self.valid_stop_frequency > self.valid_start_frequency:
                self.output_list = self.available_frequencies[self.available_frequencies.index(self.valid_start_frequency):
                                                                self.available_frequencies.index(self.valid_stop_frequency) + 1]
            else:
                self.output_list = self.available_frequencies[self.available_frequencies.index(self.valid_stop_frequency):
                                                                self.available_frequencies.index(self.valid_start_frequency) + 1]
                self.output_list.reverse()

        elif self.measurement_mode is 1:
            diff = self.stop_bias - self.start_bias
            if diff > 0:
                for i in xrange(int((diff) / self.step_bias) + 1):
                    self.output_list.append(self.start_bias + self.step_bias * i)
            elif diff < 0:
                for i in xrange(int(abs(diff) / self.step_bias) + 1):
                    self.output_list.append(self.start_bias - abs(self.step_bias) * i)
            else:
                self.output_list.append(self.start_bias)
#        logger.info('output_list %s', self.output_list)

    def _onTimer(self):
        self.timer.Stop()
        self.timer_dormant = True
        d = dict()
        values = self.instrument.query_ascii_values('FETC:IMP?')
        if self.measurement_mode is 0:
            freq = self.instrument.query('FREQ?')
            self.current_capacitance =  values[0]
            self.current_frequency = int(float(freq))
            d[self.output_channels[0]] = (dict({self.x_units[0] : self.current_frequency}),
                                            dict({self.y_units[0] : self.current_capacitance,
                                            str(self.mode)[2:] : values[1]}))
        elif self.measurement_mode is 1:
            bias = self.instrument.query('BIAS:VOLT?')
            self.current_capacitance =  values[0]
            self.current_bias = float(bias)
            d[self.output_channels[1]] = (dict({self.x_units[0] : self.current_bias}),
                                            dict({self.y_units[0] : self.current_capacitance,
                                            str(self.mode)[2:] : values[1]}))
        self.sample_nr += 1
        self.timer.Start(self.update_interval * 1000)
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

    def _measurement_mode_changed(self, new):
        if new is 0:
            self.x_units = {0: 'Frequency'}
            self.y_units = {0: 'Capacitance'}
            self.enabled_channels = [True, False]
        elif new is 1:
            self.x_units = {0: 'Voltage'}
            self.y_units = {0: 'Capacitance'}
            self.enabled_channels = [False, True]

    def _measurement_mode_default(self):
        return 1

    def _enabled_channels_default(self):
        return [False, True]

    def __available_devices_map_default(self):
        try:
            instruments_info = self.visa_resource.list_resources_info()
        except visa.VisaIOError:
            return {}

        d = {}
        candidates = [n for n in instruments_info.values() if n.resource_name.upper().startswith('GPIB')]
        d.update(SerialUtil.probe(candidates, self.visa_resource, INSTRUMENT_IDENTIFIER))
        return d

    def _start_frequency_default(self):
        return DEFAULT_START_FREQUENCY

    def _stop_frequency_default(self):
        return DEFAULT_STOP_FREQUENCY

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
