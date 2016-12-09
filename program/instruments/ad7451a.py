import logging
import os
from traits.api import HasTraits, Range, Instance, Bool, Dict, \
    List, Float, Unicode, Str, Int, on_trait_change, Event, Button, Enum
from traitsui.api import View, Item, Group, ButtonEditor, \
    EnumEditor, Label, HGroup, spring, VGroup, Handler
import traits.has_traits
from time import time
from serial_util import SerialUtil
from pyface.timer.api import Timer
import visa

from i_instrument import IInstrument
logger = logging.getLogger(__name__)
INSTRUMENT_IDENTIFIER = ['ADC', '7451']


class ad7451aHandler(Handler):
    def closed(self, info, is_ok):
        if info.object.instrument is not None:
            info.object.instrument.close()

#@provides(IInstrument)
class ad7451a(HasTraits):
    """Keithley 2100 multimeter driver"""
    sampling_interval = Range(0.05, 10, 1)
    start_stop = Event
    refresh_list = Button
    button_label = Str('Start')
    acquired_data = List(Dict)
    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    measurement_info = Dict()
    visa_resource = Instance(visa.ResourceManager, ())
    timer = Instance(Timer.singleShot)
    instrument = Instance(visa.Resource)
    measurement_mode = Str('VOLT:DC')
    measurement_map_mode = Dict({'RES': 'Resistance', 'VOLT:DC': 'Voltage DC',
                                 'VOLT:AC': 'Voltage AC', 'CURR:DC': 'Current DC',
                                 'CURR:AC': 'Current AC', 'FREQ': 'Frequency',
                                 'TEMP': 'Temperature'})
    x_units = Dict({0: 'SampleNumber', 1: 'Time'})
    y_units = Dict({0: 'Voltage', 1: 'Resistance', 2: 'Current',
                    3: 'Frequency', 4: 'Temp'})
    acq_value = Float
    measurement_time = Float
    acq_start_time = Float
    sample_nr = Int
    name = Unicode('ADCMT 7451A')
    running = Bool(False)
    output_channels = Dict({0:'chan0'})
    enabled_channels = List(Bool)

    traits_view = View(HGroup(Label('Device: '), Item('selected_device',
                                                      show_label=False,
                                                      editor=EnumEditor(name='_available_devices_map'),
                                                      enabled_when='not running'),
                              Item('refresh_list')),
                       HGroup(Item('measurement_mode',
                                   editor=EnumEditor(name='measurement_map_mode'),
                                   enabled_when='False'), Label('<--- NOT USED. Select mode on instrument')),
                       Item('sampling_interval', enabled_when='not running'),
                       Item('start_stop', label='Start/Stop Acqusistion',
                            editor=ButtonEditor(label_value='button_label')),
                       Item('acq_value', style='readonly'),
                       Item('measurement_time', style='readonly', format_str='%.2f'),
                       Item('sample_nr', style='readonly'),
                       handler=ad7451aHandler)

    def _enabled_channels_default(self):
        return [True]

    def __available_devices_map_default(self):
        try:
            instruments_info = self.visa_resource.list_resources_info()
        except visa.VisaIOError:
            return {}

        d = {}
        candidates = [n for n in instruments_info.values() if n.resource_name.upper().startswith('USB')]
        d.update(SerialUtil.probe(candidates, self.visa_resource, INSTRUMENT_IDENTIFIER))

        return d

    def _refresh_list_fired(self):
        self._available_devices = self.__available_ports_default()

    def _fix_output_dict(self, data):
        d = {}
        for unit in self.y_units.values():
            d[unit] = 0.0

        d[self.measurement_map_mode.get(self.measurement_mode)[:-3]] = data
        return d

    def add_data(self):
        if not self.running:
            return
        self.sample_nr += 1
        try:
            data = float(self.instrument.read())
        except visa.VisaIOError:
            data = self.acq_value
            pass
        self.acq_value = float(data)
        logger.info(data)
        self.measurement_time = time() - self.acq_start_time   
        d = dict()
        for i, enabled in enumerate(self.enabled_channels):

            d[self.output_channels[i]] = (dict({self.x_units[0]:self.sample_nr,
                                                self.x_units[1]:self.measurement_time}),
                                          self._fix_output_dict(self.acq_value))
        self.timer = Timer.singleShot(max(0,
                                          ((float(self.sample_nr) * self.sampling_interval) -
                                           self.measurement_time) * 1000),
                                      self.add_data)
        self.acquired_data.append(d)

    def start(self):
        self.running = True
        self.acq_start_time = time()
        self.sample_nr = 0
        self.instrument = SerialUtil.open(self.selected_device, self.visa_resource)
        if self.instrument is None:
            self.instrument = None
            self.selected_device = ''

        self.timer = Timer.singleShot(self.sampling_interval * 1000, self.add_data)

    def stop(self):
        logger.info('stop()')
        self.running = False
        self.instrument.close()

    def _start_stop_fired(self, old, new):
        if self.selected_device == '':
            return
        if self.running:
            self.button_label= 'Start'
            self.stop()
        else:
            self.button_label = 'Stop'
            self.start()


if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    n = ad7451a()
    n.configure_traits()
