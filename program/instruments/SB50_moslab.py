import logging
from traits.api import HasTraits, Range, Instance, Bool, Dict, \
    List, Unicode, Str, Int, on_trait_change, Event, Button
from traitsui.api import View, Item, Group, ButtonEditor, \
    EnumEditor, Label, HGroup, spring, VGroup, Handler
import traits.has_traits
#traits.has_traits.CHECK_INTERFACES = 2
from time import time
from PyDAQmx.DAQmxFunctions import TaskHandle, DAQmxCreateTask, \
    DAQmxCreateDOChan, DAQmxStartTask, DAQmxStopTask, DAQmxWriteDigitalLines, \
    DAQmxClearTask
from PyDAQmx.Task import Task
from PyDAQmx.DAQmxConstants import DAQmx_Val_NRSE, DAQmx_Val_Volts, \
    DAQmx_Val_Rising, DAQmx_Val_ContSamps, DAQmx_Val_Acquired_Into_Buffer, \
    DAQmx_Val_GroupByScanNumber, DAQmx_Val_ChanForAllLines, DAQmx_Val_GroupByChannel, \
    DAQmx_Val_RSE

from numpy import zeros, ones
import PyDAQmx
from ctypes import byref, c_int32, c_uint32, c_ubyte, c_int, POINTER, c_double

from i_instrument import IInstrument
logger = logging.getLogger(__name__)

class CallbackTask(Task, HasTraits):
    INPUT_CHANNEL = 'ai0'
    HEATER_CONTROL_CHANNEL = 'port0/Line0:3'
#    INPUT_TASK_NAME = 'InputTask'
    output = List
    sample_number = Int(0)
    sample_number_in_cycle = Int(0)
    def __init__(self):
        super(CallbackTask, self).__init__()

    def __del__(self):
        DAQmxClearTask(self.DOtaskHandle)

    def setup(self, device):
#        self.ouput = zeros(len(channels))
        self.data = zeros(16)

        logger.info('Adding %s', device + '/' + self.INPUT_CHANNEL)
        self.DOtaskHandle = TaskHandle(0)
        DAQmxCreateTask("", byref(self.DOtaskHandle))
        self.CreateAIVoltageChan(device + '/' + self.INPUT_CHANNEL, "", DAQmx_Val_RSE,\
            -10.0,10.0, DAQmx_Val_Volts, None)
        DAQmxCreateDOChan(self.DOtaskHandle, device + '/' + self.HEATER_CONTROL_CHANNEL, "", DAQmx_Val_ChanForAllLines)

        self.CfgSampClkTiming("", 1 ,DAQmx_Val_Rising, DAQmx_Val_ContSamps, 1)
        self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, \
            1, 0)
        self.AutoRegisterDoneEvent(0)
        self.sample_number = 0
        self.start_time = time()

    def EveryNCallback(self):
        read = c_int32()
        self.ReadAnalogF64(1, 10.0, DAQmx_Val_GroupByScanNumber, self.data, \
                1, byref(read), None)
#        logger.info('readF64: %s', self.data)
        if self.sample_number_in_cycle == 0:
            self.sample_number += 1
            out = []
            out.append(self.sample_number)
            out.append(time() - self.start_time)
            out.extend(self.data.tolist())
            self.output = out
            output = zeros(4, dtype=c_ubyte)
            DAQmxStartTask(self.DOtaskHandle)
            DAQmxWriteDigitalLines(self.DOtaskHandle, 1, 1, 10.0, DAQmx_Val_GroupByChannel, output, byref(read), POINTER(c_uint32)())
            DAQmxStopTask(self.DOtaskHandle)
#            logger.info('Heater On')

        if self.sample_number_in_cycle == 3:
            output = ones(4, dtype=c_ubyte)
            DAQmxStartTask(self.DOtaskHandle)
            DAQmxWriteDigitalLines(self.DOtaskHandle, 1, 1, 10.0, DAQmx_Val_GroupByChannel, output, byref(read), POINTER(c_uint32)())
            DAQmxStopTask(self.DOtaskHandle)
#            logger.info('Heater Off')

        self.sample_number_in_cycle += 1
        if self.sample_number_in_cycle == 10:
            self.sample_number_in_cycle = 0


    def DoneCallback(self, status):
        logger.info("Status", status.value)
        return 0 # The function should return an integer

class NI6215Handler(Handler):
    def closed(self, info, is_ok):
        if hasattr(info.object.acqusition_task, 'StopTask') and info.object.running:
            info.object.acqusition_task.StopTask()
            info.object.acqusition_task.ClearTask()

#@provides(IInstrument)
class NI6215_MOSLab(HasTraits):
    """Dummy instrument for generation of values (V, I, R) over time"""
    CHANNEL_CELL_WIDTH = 25.0


    sampling_interval = Range(0.05, 10, 1)
    start_stop = Event
    refresh_list = Button
    ai0 =Bool(True)
    #ai1 =Bool(False)
    #ai2 =Bool(False)
    #ai3 =Bool(False)
    #ai4 =Bool(False)
    #ai5 =Bool(False)
    #ai6 =Bool(False)
    #ai7 =Bool(False)
    #ai8 =Bool(False)
    #ai9 =Bool(False)
    #ai10 =Bool(False)
    #ai11 =Bool(False)
    #ai12 =Bool(False)
    #ai13 =Bool(False)
    #ai14 =Bool(False)
    #ai15 =Bool(False)
    button_label = Str('Start')

    output_unit = 0
    timebase = 0
    acqusition_task = Instance(CallbackTask)
    acquired_data = List(Dict)
    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    parameter_group = Group(
        Item('sampling_interval', enabled_when='not running'),
        show_border = True)

    traits_view = View(
                        parameter_group,
                        HGroup(Label('Device: '), Item('selected_device', \
                        show_label = False,
                            editor = EnumEditor(name='_available_devices_map'), \
                            enabled_when='not running'),
                            Item('refresh_list')),
                        HGroup(Label('Channels:'), spring, VGroup(HGroup(\
                        Item('ai0', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai1', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai2', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai3', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH)), HGroup(\
                        #Item('ai4', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai5', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai6', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai7', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH)), HGroup(\
                        #Item('ai8', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai9', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai10', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai11', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH)), HGroup(\
                        #Item('ai12', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai13', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai14', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        #Item('ai15', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH))\
                        ))), \
                        Item('start_stop', label = 'Start/Stop Acqusistion',
                                editor = ButtonEditor(label_value='button_label')),\
                                handler=NI6215Handler)

    def __init__(self):
        self.on_trait_change(self.add_data, 'acqusition_task.output')
        self.on_trait_change(self.channel_changed, 'ai+')

    def _enabled_channels_default(self):
        return [self.ai0]

    def __available_devices_map_default(self):
        s = str('000000000000000000000000000000000000000000000000000')
        PyDAQmx.DAQmxGetSysDevNames(s, len(s))
        (a,b,c) = s.partition('\x00')
        devs=a.split(', ')
        serial = c_uint32(0)
        devices=[]
        for d in devs:
            PyDAQmx.DAQmxGetDevProductType(d, s, len(s))
            (a,b,c) = s.partition('\x00')
            if a.startswith('USB-62'):
                PyDAQmx.DAQmxGetDevSerialNum(d, serial)
                devices.append((d, a + ' - ' + hex(serial.value)[2:-1].upper()))
            if a.startswith('PCI-'):
                PyDAQmx.DAQmxGetDevSerialNum(d, serial)
                devices.append((d, a + ' - In computer'))
        retval = dict((device[0], device[1]) for device in devices)
        logger.info('_available_devices_map_default %s', retval)
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
#        self._selected_device_changed(device)
        return device

    def _refresh_list_fired(self):
        self._available_devices_map = self.__available_devices_map_default()
        self.__available_devices_map_changed()

    def add_data(self):
        data = self.acqusition_task.output
        if len(data) < 18:
            return
        d = dict()
        for i, enabled in enumerate(self.enabled_channels):

            d[self.output_channels[i]] = (dict({self.x_units[0]:data[0], self.x_units[1]:data[1],}),\
                            dict({self.y_units[0]:data[i + 2]}))
        self.acquired_data.append(d)

    #### 'IInstrument' interface #############################################
    name = Unicode('SB50_MOSLab')
    measurement_info = Dict()
    x_units = Dict({0:'SampleNumber', 1:'Time'})
    y_units = Dict({0: 'Voltage'})
    running = Bool(False)
    output_channels = Dict({0:'ai00'})
    enabled_channels = List(Bool)

    def start(self):
        self.running = True
        self.acq_start_time = time()
        self.acqusition_task = CallbackTask()
        dev_str = self._available_devices_map[self.selected_device]
        if dev_str.find('USB-6215') >= 0:
            self.acqusition_task.HEATER_CONTROL_CHANNEL = 'port1/line0:3'
        self.acqusition_task.setup(self.selected_device)
        self.acqusition_task.StartTask()

    def stop(self):
        logger.info('stop()')
        self.running = False
        self.acqusition_task.StopTask()
        self.acqusition_task.ClearTask()


    ##########################################################################

    def _start_stop_fired(self, old, new):
        if self.running:
            self.button_label= 'Start'
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
    n = NI6215_MOSLab()
    n.configure_traits()

#    a = AcquisitionThread()
#    d = DummySourcemeterTime()
#    d.tracer = SimpleTracer()
#    d.on_trait_change(d._log_changed)
#    d.traits_view = View(d.parameter_group)

#    d.tracer.configure_traits()
#    d.configure_traits()

    #d.start()
#    for t in d.traits():
#        if 'mean' in t:
#            a.config[t] = d.get(t)[t]
#        if 'stdev' in t:
#            a.config[t] = d.get(t)[t]
#        if 'sampling' in t:
#            a.config[t] = d.get(t)[t]
#    print a.config
#    a.data= []
#    a.start()
#    sleep(2)
#    a.wants_abort = True

#    a.data
