import logging
from traits.api import HasTraits, Range, Instance, Bool, Dict,\
    List, Unicode, Str, Int, on_trait_change, Event, Button, Float
from traitsui.api import View, Item, Group, ButtonEditor,\
    EnumEditor, Label, HGroup, spring, VGroup, Handler
from pyface.timer.api import Timer
import traits.has_traits
from time import time
from PyDAQmx.Task import Task
from PyDAQmx.DAQmxConstants import DAQmx_Val_RSE, DAQmx_Val_Volts,\
    DAQmx_Val_Rising, DAQmx_Val_ContSamps, DAQmx_Val_Acquired_Into_Buffer,\
    DAQmx_Val_GroupByScanNumber, DAQmx_Val_ChanPerLine, DAQmx_Val_FiniteSamps,\
    DAQmx_Val_GroupByChannel, DAQmx_Val_OnDemand
from numpy import zeros, float64, size, mean
import PyDAQmx
from ctypes import byref, c_int32, c_uint32
from i_instrument import IInstrument

logger = logging.getLogger(__name__)
MAX_TRIG_FREQ = 1000
RENDER_INTERVAL_MS = 200


class CallbackTask(Task):

    def setup(self, device, channels, sampling_interval, parent):
        self.logger = logger
        self.data = zeros(16)
        for channel in channels:
            self.logger.info('Adding %s', device + '/' + channel)
            self.CreateAIVoltageChan(device + '/' + channel, "", DAQmx_Val_RSE,
                                     -10.0, 10.0, DAQmx_Val_Volts, None)

        self.CfgSampClkTiming("", 1/sampling_interval ,DAQmx_Val_Rising,
                              DAQmx_Val_ContSamps, 1)
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer,
                                            1, 0)
        self.AutoRegisterDoneEvent(0)
        self.sample_number = 0
        self.start_time = time()
        self.parent = parent
        self.sample_number = 0
        self.data_acquired = parent.data_acquired

    def EveryNCallback(self):
        self.sample_number += 1
        out = list()
        out.append(self.sample_number)
        out.append(time() - self.start_time)
        read = c_int32()
        try:
            self.ReadAnalogF64(1, 10.0, DAQmx_Val_GroupByScanNumber, self.data,
                               16, byref(read), None)
        except PyDAQmx.DAQError as e:
            print(e) 
        out.extend(self.data.tolist())
        self.parent.add_data(out)
        self.parent.data_acquired = True

    def DoneCallback(self, status):
        #self.logger.info("Status", status.value)
        return 0    # The function should return an integer


class CallbackTaskSynced(Task):

    def setup(self, device, channels, sampling_interval, parent):
        self.samples_per_chan = 15
        self.pretrigger_samples = 12
        self.logger = logger
        self.data = zeros((self.samples_per_chan, len(channels)), dtype=float64)
        self.internal_buffer = zeros((self.pretrigger_samples * MAX_TRIG_FREQ * sampling_interval, len(channels)))
                    
        for channel in channels:
            self.logger.info('Adding %s', device + '/' + channel)
            self.CreateAIVoltageChan(device + '/' + channel, "", DAQmx_Val_RSE,
                                     -10.0, 10.0, DAQmx_Val_Volts, None)

        self.CfgSampClkTiming('', 5000.0, DAQmx_Val_Rising,
                              DAQmx_Val_FiniteSamps, self.samples_per_chan)
        self.CfgDigEdgeRefTrig(device + '/PFI0', DAQmx_Val_Rising, self.pretrigger_samples)
        self.SetBufInputBufSize(size(self.data))

        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer,
                                            self.samples_per_chan, 0)
        self.AutoRegisterDoneEvent(0)
        self.parent = parent
        self.start_time = time()
        self.last_sample_time = self.start_time
        self.next_sample_time = self.last_sample_time + sampling_interval
        self.fast_sample_counter = 0
        self.sample_number = 0
        self.sampling_interval = sampling_interval
        self.data_acquired = parent.data_acquired

    def EveryNCallback(self):
        self.fast_sample_counter += 1
        logger.warning('EveryNCallback %d', self.fast_sample_counter)

        read = c_int32()
        try:
            self.ReadAnalogF64(self.samples_per_chan, 0, DAQmx_Val_GroupByScanNumber, self.data,
                               size(self.data), byref(read), None)
        except PyDAQmx.DAQError as e:
            logger.warning('Exception %s, nr of samples read %s', e, str(read))

        self.internal_buffer[:][self.pretrigger_samples * (self.fast_sample_counter - 1): self.pretrigger_samples * self.fast_sample_counter] = self.data[:][:self.pretrigger_samples]
        current_time = time()
        if current_time > self.next_sample_time:
            self.next_sample_time = current_time + self.sampling_interval - (current_time - self.next_sample_time)                                
            self.sample_number += 1
            out = []
            out.append(self.sample_number)
            out.append(current_time - self.start_time)
            out.extend(mean(self.internal_buffer[:][:self.pretrigger_samples * self.fast_sample_counter], axis=0).tolist())
            self.fast_sample_counter = 0        
            self.parent.add_data(out)
            self.data_acquired = True

    def DoneCallback(self, status):
        self.logger.info("Status %s", str(status))
        return 0    # The function should return an integer


class NI6215Handler(Handler):
    def closed(self, info, is_ok):
        if hasattr(info.object.acqusition_task, 'StopTask') and info.object.running:
            info.object.acqusition_task.StopTask()
            info.object.acqusition_task.ClearTask()


# @provides(IInstrument)
class NI6215(HasTraits):
    """Dummy instrument for generation of values (V, I, R) over time"""

    """ 'IInstrument' interface ############################################# """
    name = Unicode('NI-DAQmx')
    measurement_info = Dict()
    x_units = Dict({0:'SampleNumber', 1:'Time'})
    y_units = Dict({0: 'Voltage'})
    running = Bool(False)
    output_channels = Dict({0:'ai00', 1:'ai01', 2:'ai02', 3:'ai03',
                            4:'ai04', 5:'ai05', 6:'ai06', 7:'ai07',
                            8:'ai08', 9:'ai09', 10:'ai10', 11:'ai11',
                            12:'ai12', 13:'ai13', 14:'ai14', 15:'ai15'})
    enabled_channels = List(Bool)
    CHANNEL_CELL_WIDTH = 25.0
    sampling_interval = Range(0.05, 10, 1)
    start_stop = Event
    refresh_list = Button
    ai0 =Bool(False)
    ai1 =Bool(False)
    ai2 =Bool(False)
    ai3 =Bool(False)
    ai4 =Bool(False)
    ai5 =Bool(False)
    ai6 =Bool(False)
    ai7 =Bool(False)
    ai8 =Bool(False)
    ai9 =Bool(False)
    ai10 =Bool(False)
    ai11 =Bool(False)
    ai12 =Bool(False)
    ai13 =Bool(False)
    ai14 =Bool(False)
    ai15 =Bool(False)
    button_label = Str('Start')

    value_ai0 = Float
    value_ai1 = Float
    value_ai2 = Float
    value_ai3 = Float

    synced_acqusistion = Bool(False)

    data_acquired = Bool(False)
    data = List(Float)
    output_unit = 0
    timebase = 0
    acqusition_task = Instance(Task)
    acquired_data = List(Dict)
    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    parameter_group = Group(Item('sampling_interval', enabled_when='not running'),
                            show_border=True)

    traits_view = View(parameter_group,
                       HGroup(Label('Device: '), Item('selected_device',
                                                      show_label=False,
                                                      editor=EnumEditor(name='_available_devices_map'),
                                                      enabled_when='not running'),
                              Item('refresh_list')),
                       HGroup(Label('Channels:'), spring, 
                              VGroup(
                                  HGroup(
                                      Item('ai0', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai1', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai2', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai3', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH)),
                                  HGroup(
                                      Item('ai4', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai5', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai6', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai7', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH)),
                                  HGroup(
                                      Item('ai8', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai9', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai10', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai11', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH)),
                                  HGroup(
                                      Item('ai12', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai13', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai14', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH),
                                      Item('ai15', enabled_when='not running', springy=True, width=CHANNEL_CELL_WIDTH)))),
                       HGroup(Item('value_ai0', style='readonly'),
                              Item('value_ai1', style='readonly'),
                              Item('value_ai2', style='readonly'),
                              Item('value_ai3', style='readonly')),
                       Item('synced_acqusistion', enabled_when='false'),
                       Item('start_stop', label='Start/Stop Acqusistion',
                            editor=ButtonEditor(label_value='button_label')),
                       handler=NI6215Handler)

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.on_trait_change(self.channel_changed, 'ai+')
        self.ai0 = self.ai1 = self.ai2 = self.ai3 = True

    def _enabled_channels_default(self):
        return [False] * 16

    def __available_devices_map_default(self):
        s = str('000000000000000000000000000000000000000000000000000')
        PyDAQmx.DAQmxGetSysDevNames(s, len(s))
        (a, b, c) = s.partition('\x00')
        devs = a.split(', ')
        serial = c_uint32(0)
        devices=[]
        for d in devs:
            if len(d) > 0:
                PyDAQmx.DAQmxGetDevProductType(d, s, len(s))
                (a, b, c) = s.partition('\x00')
                if a.startswith('USB-'):
                    PyDAQmx.DAQmxGetDevSerialNum(d, serial)
                    devices.append((d, a + ' - ' + hex(serial.value)[2:-1].upper()))
                if a.startswith('PCI-'):
                    PyDAQmx.DAQmxGetDevSerialNum(d, serial)
                    devices.append((d, a + ' - In computer'))
            else:
                break
        retval = dict((device[0], device[1]) for device in devices)
        self.logger.info('_available_devices_map_default %s', retval)
        return retval

    @on_trait_change('_available_devices_map')
    def __available_devices_map_changed(self):
        if self.selected_device not in self._available_devices_map.keys():
            self.selected_device = self._available_devices_map.items()[0][0]

    def _selected_device_default(self):
        try:
            device = self._available_devices_map.items()[0][0]
        except IndexError:
            return ''
        return device

    def _refresh_list_fired(self):
        self._available_devices_map = self.__available_devices_map_default()
        self.__available_devices_map_changed()

    def add_data(self, data):
        self.data = data

    def handle_data(self):
        if self.data_acquired is False:
            return
        self.data_acquired = False
        if len(self.data) < 18:
            return
        d = dict()
        for i, enabled in enumerate(self.enabled_channels):

            d[self.output_channels[i]] = (dict({self.x_units[0]:self.data[0], self.x_units[1]:self.data[1], }),
                                          dict({self.y_units[0]:self.data[i + 2]}))
        self.acquired_data.append(d)
        self.value_ai0 = self.data[2]
        self.value_ai1 = self.data[3]
        # self.timer = Timer.singleShot(RENDER_INTERVAL_MS, self.add_data)

    def start(self):
        self.running = True
        self.acq_start_time = time()
        if self.synced_acqusistion is True:
            self.acqusition_task = CallbackTaskSynced()
        else:
            self.acqusition_task = CallbackTask()
        channels = []
        for i, enabled in enumerate(self.enabled_channels):
            if enabled:
                channels.append('ai' + str(i))
        self.acqusition_task.setup('/' + self.selected_device,
                                   channels, self.sampling_interval, self)
        self.acqusition_task.StartTask()
        self.timer = Timer(RENDER_INTERVAL_MS, self.handle_data)
        self.timer.start()

    def stop(self):
        self.logger.info('stop()')
        self.running = False
        self.acqusition_task.StopTask()
        self.acqusition_task.ClearTask()

    def _start_stop_fired(self, old, new):
        if self.running:
            self.button_label = 'Start'
            self.stop()
        else:
            self.button_label = 'Stop'
            self.start()

    def channel_changed(self, obj, name, new):
        self.enabled_channels[int(name[2:])] = new


if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    n = NI6215()
    n.configure_traits()
