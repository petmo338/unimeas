from i_instrument import IInstrument
from enthought.traits.api import HasTraits, Instance, Float, Dict, \
    List, implements, Unicode, Str, Int, on_trait_change, Array,\
   Event, Bool, Enum
from enthought.traits.ui.api import View, Item, Group, ButtonEditor, Handler, EnumEditor
from pyface.timer.api import Timer
import visa
import numpy as np
import logging

logger = logging.getLogger(__name__)

DEFAULT_START_FREQUENCY = int(1000)
DEFAULT_STOP_FREQUENCY = int(1e6)

class ViewHandler(Handler):
    def closed(self, info, is_ok):
#        logger.debug('Closing')
        if info.object.timer is not None:
            info.object.timer.Stop()

class Agilent4284(HasTraits):

    implements(IInstrument)

    name = Unicode('Agilent 4284')

    x_units = Dict({0: 'Frequency'})
    y_units = Dict({0: 'Capacitance'})

    acquired_data = List(Dict)

    start_stop = Event
    running = Bool

    output_channels = Dict({0: 'ch0'})

    enabled_channels = List(Bool)

    timer = Instance(Timer)
    timer_dormant = Bool(False)
    update_interval = Float(0.5)

    start_frequency = Int
    stop_frequency = Int

    bias = Float(1.0)
    mode = Enum('CpD', 'CpQ','CpG', 'CpRp', 'CsD', 'CsQ', 'CsRs')
    current_frequency = Int
    current_capacitance = Float

    valid_start_frequency = Int(DEFAULT_START_FREQUENCY)
    valid_stop_frequency = Int(DEFAULT_STOP_FREQUENCY)


    use_log_steps = Bool(False)
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
                        Group(Item('start_frequency', enabled_when='not running'),
                            Item('stop_frequency', enabled_when='not running'),
                            Item('bias'), Item('mode', enabled_when='not running'),
                            Item('current_frequency', enabled_when='False'),
                            Item('current_capacitance', enabled_when='False'),
                            label='C/F', show_border = True),
                        Item('update_interval'),
                        Item('start_stop', label = 'Start/Stop Acqusistion',
                                editor = ButtonEditor(label_value='button_label')),
                        handler = ViewHandler)

    def instrument_init(self):
        if self.instrument is not None:
            self.instrument.write('OUTP:HPOW 1')
            self.instrument.write('VOLT 0.5')
            self.instrument.write('BIAS:VOLT ' + str(self.bias))
            self.instrument.write('BIAS:STAT 1')
            self.instrument.write('FUNC:IMP ' + str(self.mode))
            #self.instrument.write('TRIG:IMM')
            self.instrument.write('FREQ ' + str(self.start_frequency))

    def instrument_stop(self):
        if self.instrument is not None:
            self.instrument.write('BIAS:STAT 0')
            self.instrument.write('VOLT 0.5')


    def start(self):
        self.button_label = 'Stop'
        self.start_frequency = self.valid_start_frequency
        if self.valid_stop_frequency <= self.valid_start_frequency:
            i = self.available_frequencies.index(self.valid_start_frequency) + 1
            self.valid_stop_frequency = self.available_frequencies[i]
        self.stop_frequency = self.valid_stop_frequency
        self.current_frequency = self.start_frequency
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

    def _onTimer(self):
        stopping = False
        self.timer.Stop()
        self.timer_dormant = True
        d = dict()
        values = self.instrument.ask_for_values('FETC:IMP?')
        freq = self.instrument.ask('FREQ?')
        self.current_capacitance =  values[0]
        d[self.output_channels[0]] = (dict({self.x_units[0] : freq}),
                                        dict({self.y_units[0] : self.current_capacitance}))
        self.sample_nr += 1

        freq_idx = self.available_frequencies.index(self.current_frequency) + 1
        if freq_idx >= len(self.available_frequencies):
            stopping = True
        else:
            self.current_frequency = self.available_frequencies[freq_idx]

        self.timer.Start(self.update_interval * 1000)
        self.timer_dormant = False
        self.acquired_data.append(d)
        if self.current_frequency > self.stop_frequency or stopping:
            self.start_stop = True
        else:
            self.instrument.write('FREQ ' + str(self.current_frequency))

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
            if name == 'start_frequency':
                index = 0
                while new >= self.available_frequencies[index]:
                    index += 1
                    if index >= len(self.available_frequencies):
                        index = len(self.available_frequencies) - 2
                        break
            elif name == 'stop_frequency':
                index = len(self.available_frequencies) - 1
                while new <= self.available_frequencies[index]:
                    index -= 1
                    if index < 1:
                        index = 1
                        break
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

    def _start_frequency_default(self):
        return DEFAULT_START_FREQUENCY

    def _stop_frequency_default(self):
        return DEFAULT_STOP_FREQUENCY


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
