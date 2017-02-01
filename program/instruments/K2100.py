from traits.api import HasTraits, Range, Instance, Bool, Dict, \
    List, Float, Unicode, Str, Int, Event, Button, Enum
from traitsui.api import View, Item, ButtonEditor, \
    EnumEditor, Label, HGroup, Handler

from time import time, sleep
from serial_util import SerialUtil
from pyface.timer.api import Timer
import visa
import threading
import logging

logger = logging.getLogger(__name__)
INSTRUMENT_IDENTIFIER = ['KEITHLEY', '21']


class Poller(threading.Thread):
    POLL_INTERVAL = 200

    exit_flag = False
    is_connected = True
    instrument = Instance(visa.Resource)
    lock = threading.Lock()
    value = 0.0

    def __init__(self, instrument):
        threading.Thread.__init__(self)
        self.instrument = instrument

    def run(self):
        while not self.exit_flag:
            sleep(self.POLL_INTERVAL / 1000.0)
            try:
                response = self.instrument.query('READ?')
            except visa.VisaIOError as e:
                self.is_connected = False
                self.instrument.close()
                self.exit_flag = True
                logger.error('VISA error %s', e)
            else:
                self.lock.acquire()
                self.value = float(response)
                self.lock.release()
        logger.info('Stopping K2100 poller thread')


class K2100Handler(Handler):
    def closed(self, info, is_ok):
        if info.object.instrument is not None:
            info.object.instrument.close()


# @provides(IInstrument)
class K2100(HasTraits):
    """Keithley 2100 multimeter driver"""
    sampling_interval = Range(0.2, 10, 1)
    start_stop = Event
    refresh_list = Button
    button_label = Str('Start')
    acquired_data = List(Dict)
    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    measurement_info = Dict()
    visa_resource = Instance(visa.ResourceManager, ())
    instrument = Instance(visa.Resource)
    measurement_mode = Str('RES')
    valid_measurement_ranges = List
    measurement_range = Enum(values='valid_measurement_ranges')

    measurement_mode_map = Dict({'RES': 'Resistance', 'VOLT:DC': 'Voltage DC',
                                 'VOLT:AC': 'Voltage AC', 'CURR:DC': 'Current DC',
                                 'CURR:AC': 'Current AC', 'FREQ': 'Frequency',
                                 'TEMP': 'Temperature', 'FRES': '4-wire resistance'})
    measurement_ranges = Dict({'RES': ['100', '1000', '10000', '100000', '1.0E+06', '1.0E+07', '1.0E+08'],
                               'FRES': ['100', '1000', '10000', '100000', '1.0E+06', '1.0E+07', '1.0E+08'],
                               'VOLT:DC': ['0.1', '1', '10', '100'],
                               'VOLT:AC': ['0.1', '1', '10', '100'],
                               'CURR:DC': ['0.01', '0.1', '1', '3'],
                               'CURR:AC': ['1', '3'],
                               'FREQ': ['0.1', '1', '10', '100', '750'],
                               'TEMP': ['xx']})
    x_units = Dict({0: 'SampleNumber', 1: 'Time'})
    y_units = Dict({0: 'Resistance', 1: 'Voltage', 2: 'Current',
                    3: 'Frequency', 4: 'Temp'})
    acq_value = Float
    measurement_time = Float
    sample_nr = Int
    name = Unicode('Keithley 2100')
    running = Bool(False)
    output_channels = Dict({0: 'chan0'})
    enabled_channels = List(Bool)
    acq_start_time = Float
    timer = Instance(Timer)
    poller = Instance(Poller)
    range_label = Str(u'Range: [\u2126]')
    traits_view = View(HGroup(Label('Device: '), Item('selected_device',
                                                      show_label=False,
                                                      editor=EnumEditor(name='_available_devices_map'),
                                                      enabled_when='not running'),
                              Item('refresh_list')),
                       HGroup(Item('measurement_mode',
                                   editor=EnumEditor(name='measurement_mode_map'),
                                   enabled_when='not running'),
                              Label('Range:'),
                              Item('measurement_range', style='simple', show_label=False)),
                       Item('sampling_interval', enabled_when='not running'),
                       Item('start_stop', label='Start/Stop Acquisition',
                            editor=ButtonEditor(label_value='button_label')),
                       Item('acq_value', style='readonly'),
                       Item('measurement_time', style='readonly', format_str='%.2f'),
                       Item('sample_nr', style='readonly'),
                       handler=K2100Handler)

    def _valid_measurement_ranges_default(self):
        return self.measurement_ranges[self.measurement_mode]

    def _enabled_channels_default(self):
        return [True]

    def _measurement_mode_changed(self, new):
        self.valid_measurement_ranges = self.measurement_ranges[self.measurement_mode]
        if new[:4] is 'VOLT':
            self.range_label = 'Range: [V]'
        if new[:3] is 'RES':
            self.range_label = 'Range: [\u2126]'
        if new[:3] is 'CURR':
            self.range_label = 'Range: [A]'

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
        output_name = self.measurement_mode_map.get(self.measurement_mode)
        if output_name[-1] == 'C':
            output_name = output_name[:-3]
        d[output_name] = data
        return d

    def add_data(self):
        if not self.running:
            return
        self.sample_nr += 1
        self.poller.lock.acquire()
        is_connected = self.poller.is_connected
        data = self.poller.value
        self.poller.lock.release()
        self.acq_value = data
        if self.acq_value > 1e9 and self.measurement_mode is 'RES':
            self.acq_value = 1e9
        # logger.info(data)
        self.measurement_time = time() - self.acq_start_time   
        d = dict()
        for i, enabled in enumerate(self.enabled_channels):
            d[self.output_channels[i]] = (dict({self.x_units[0]: self.sample_nr,
                                                self.x_units[1]: self.measurement_time}),
                                          self._fix_output_dict(self.acq_value))
        self.acquired_data.append(d)
        if is_connected:
            self.timer = Timer.singleShot(max(0,
                                              ((float(self.sample_nr) * self.sampling_interval)
                                               - self.measurement_time) * 1000),
                                          self.add_data)
        else:
            self._start_stop_fired()

    def start(self):
        self.running = True
        self.acq_start_time = time()
        self.sample_nr = 0
        self.instrument = SerialUtil.open(self.selected_device, self.visa_resource, timeout=3000)
        self.instrument_init()
        if self.instrument is None:
            # GenericPopupMessage(message ='Error opening ' + new).edit_traits()
            logger.error('Can\'t open device: %s', self.instrument.description)
            self.instrument = None
            self.selected_device = ''
            self.running = False
            return
        self.poller = Poller(self.instrument)
        self.poller.start()
        self.timer = Timer.singleShot(float(self.sampling_interval) * 1000, self.add_data)

    def stop(self):
        self.poller.exit_flag = True
        self.poller.join()
        self.running = False
        self.instrument.close()

    def instrument_init(self):
        self.instrument.write('*CLS')
        self.instrument.write('FUNC \"{0}\"'.format(str(self.measurement_mode)))
        self.instrument.write(self.measurement_mode + ':RANG ' + self.measurement_range)
        self.instrument.write(self.measurement_mode + ':NPLCycles 10')
        self.instrument.write('TRIG:SOUR IMM')

    def _start_stop_fired(self):
        if self.selected_device == '':
            return
        if self.running:
            self.button_label = 'Start'
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
    n = K2100()
    n.configure_traits()
