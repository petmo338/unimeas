from i_instrument import IInstrument
from enthought.traits.api import HasTraits, Instance, Float, Dict, \
    List, implements, Unicode, Str, Int,Event, Bool
from enthought.traits.ui.api import View, Item, ButtonEditor, Handler, EnumEditor, RangeEditor, Group
from pyface.timer.api import Timer
from pyvisa import visa
from time import time
import logging

logger = logging.getLogger(__name__)

DEFAULT_START_FREQUENCY = int(1000)
DEFAULT_STOP_FREQUENCY = int(1e6)

class ViewHandler(Handler):
    def closed(self, info, is_ok):
#        logger.debug('Closing')
        if info.object.timer is not None:
            info.object.timer.Stop()

class Boonton7200(HasTraits):

    implements(IInstrument)

    name = Unicode('Boonton7200')

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


    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    instrument = Instance(visa.Instrument)

    traits_view = View(Item('selected_device', label = 'Device', \
                                editor = EnumEditor(name='_available_devices_map'), \
                                enabled_when='not running'),
                        Item('update_interval', enabled_when='not running'),
                        Item('bias', editor = RangeEditor(is_float = True, low_name = 'bias_low_limit', high_name = 'bias_high_limit')),
                        Group(Item('current_capacitance', enabled_when = 'False'),
                                Item('current_bias', enabled_when = 'False'),
                                Item('sample_nr', enabled_when = 'False'),
                                label = 'Measurement', show_border = True),

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
        values = self.instrument.ask_for_values('TM')
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
        self.instrument = visa.Instrument(new, timeout = 2)

    def _selected_device_default(self):
        try:
            device = self._available_devices_map.items()[0][0]
        except KeyError:
            return ''     
        self._selected_device_changed(device)
        return device

    def _enabled_channels_default(self):
        return [True, False]

    def __available_devices_map_default(self):
        try:
            instruments = visa.get_instruments_list()
        except visa.VisaIOError:
            return {}

        d = dict()
        candidates = [n for n in instruments if n.startswith('GPIB')]
        for instrument in candidates:
            temp_inst = visa.instrument(instrument)
            model = temp_inst.ask('ID')
            if model.find('Model') == 0 and model.find('7200') > 0:
                d[instrument] = model

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
