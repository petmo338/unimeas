from i_instrument import IInstrument
from enthought.traits.api import HasTraits, Instance, Float, Dict, \
    List, implements, Unicode, Str, Int, \
   Event, Bool
from enthought.traits.ui.api import View, Item, Group, ButtonEditor, Handler
from pyface.timer.api import Timer
from numpy import random
import logging
logger = logging.getLogger(__name__)

class DummyIntervalInstrumentHandler(Handler):
    def closed(self, info, is_ok):
        logger.debug('Closing')
        if info.object.timer is not None:
            info.object.timer.Stop()

class DummyIntervalInstrument(HasTraits):

    implements(IInstrument)

    name = Unicode('DummyIntervalInstrument')

    x_units = Dict({0: 'Voltage', 1: 'Frequency'})
    y_units = Dict({0: 'Current', 1: 'Capacitance'})

    acquired_data = List(Dict)

    start_stop = Event
    running = Bool

    output_channels = Dict({0: 'ch0', 1: 'ch1'})

    enabled_channels = List(Bool)

    timer = Instance(Timer)
    update_interval = Float(0.03)
    start_voltage = Float(0)
    stop_voltage = Float(5)
    step_voltage = Float(0.05)
    current_voltage = Float
    current_current = Float

    start_frequency = Float(20)
    stop_frequency = Float(1e6)
    step_frequency = Float(10000)
    current_frequency = Float
    current_capacitance = Float
    use_log_steps = Bool(True)
    iteration = Int(0)
    start_stop = Event
    button_label = Str('Start')
    bias = Float

    traits_view = View(Group(Item('start_voltage'), Item('stop_voltage'),
                            Item('step_voltage'),
                            Item('current_voltage', enabled_when='False'),
                            Item('current_current', enabled_when='False'),
                            label='I/V', show_border = True),
                        Group(Item('start_frequency'), Item('stop_frequency'),
                            Item('step_frequency'), Item('use_log_steps'),
                            Item('current_frequency', enabled_when='False'),
                            Item('current_capacitance', enabled_when='False'),
                            label='C/F', show_border = True),
                        Item('update_interval'),
                        Item('start_stop', label = 'Start/Stop Acqusistion',
                                editor = ButtonEditor(label_value='button_label')),
                        handler = DummyIntervalInstrumentHandler)

    def start(self):
        if self.timer is None:
            self.timer = Timer(self.update_interval * 1000, self._onTimer)
        else:
            self.timer.Start(self.update_interval * 1000)
        self.button_label = 'Stop'
        self.current_voltage = self.start_voltage
        self.current_frequency = self.start_frequency
        self.iteration = 0
        self.running = True
        self.bias = random.random_sample() - 0.5

    def stop(self):
        if self.timer is not None:
            self.timer.Stop()
        self.button_label = 'Start'
        self.running = False

    def _onTimer(self):
        d = dict()
        self.current_current = self.current_voltage**1.3 + self.bias
        self.current_capacitance =  (self.current_frequency * (self.stop_frequency - self.current_frequency))/1e9
        d[self.output_channels[0]] = (dict({self.x_units[0] : self.current_voltage}),
                                        dict({self.y_units[0] : self.current_current}))
        d[self.output_channels[1]] = (dict({self.x_units[1] : self.current_frequency}),
                                        dict({self.y_units[1] : self.current_capacitance}))
        self.iteration += 1
        self.current_voltage += self.step_voltage

        #if self.use_log_steps:
        self.current_frequency += self.step_frequency
        self.acquired_data.append(d)
        if self.current_voltage > self.stop_voltage:
            self.start_stop = True

    def _start_stop_fired(self):
        if self.timer is None:
            self.start()
            return
        if self.timer.isActive():
            self.stop()
        else:
            self.start()

    def _enabled_channels_default(self):
        return [True, False]
