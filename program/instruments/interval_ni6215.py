import logging
from traits.api import HasTraits, Range, Instance, Bool, Dict, \
    List, Unicode, Str, Int, on_trait_change, Event, Button, Float, Any
from traitsui.api import View, Item, Group, ButtonEditor, \
    EnumEditor, Label, HGroup, spring, VGroup, Handler
import traits.has_traits
#traits.has_traits.CHECK_INTERFACES = 2
from time import time
try:
    from PyDAQmx.Task import Task
    from PyDAQmx.DAQmxConstants import DAQmx_Val_RSE, DAQmx_Val_Volts, \
        DAQmx_Val_Rising, DAQmx_Val_ContSamps, DAQmx_Val_Acquired_Into_Buffer, \
        DAQmx_Val_GroupByScanNumber, DAQmx_Val_FiniteSamps
except NotImplementedError as e:
    raise ImportError('PyDAQmx import error. No VISA lib installed?')

from numpy import zeros, array, mean
import PyDAQmx
from ctypes import byref, c_int32, c_uint32
logger = logging.getLogger(__name__)
from i_instrument import IInstrument
from pyface.timer.api import Timer

DEFAULT_START_VOLTAGE = 0
DEFAULT_STOP_VOLTAGE = 5
DEFAULT_STEP_VOLTAGE = 0.01
AVERAGE_SAMPLES = 20
DEFAULT_SAMPLE_RATE = 1000
class CallbackTask(Task, HasTraits):
    output = List
    sample_number = Int(0)
    analog_output = Instance(Task, ())


    def setup(self, device, channel, sampling_interval, vout_values, parent_obj):
        self.vout_buffer = array(vout_values)
#        logger.info('vout:s %s', self.vout_buffer)
        self.data = zeros((AVERAGE_SAMPLES, 2))
        self.CreateAIVoltageChan(device + '/ai8', "", DAQmx_Val_RSE,\
            -10.0,10.0, DAQmx_Val_Volts, None)
        self.CreateAIVoltageChan(device + '/' + channel, "", DAQmx_Val_RSE,\
            -10.0,10.0, DAQmx_Val_Volts, None)

        self.CfgSampClkTiming("", DEFAULT_SAMPLE_RATE ,DAQmx_Val_Rising, \
            DAQmx_Val_FiniteSamps, AVERAGE_SAMPLES)
        #self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, \
        #    AVERAGE_SAMPLES, 0)
        #self.AutoRegisterDoneEvent(0)
        self.sample_number = 0
        self.start_time = time()
        self.analog_output.CreateAOVoltageChan(device + '/ao0', "", -10.0,10.0, DAQmx_Val_Volts, None)
        self.parent_obj = parent_obj
        read = c_int32()
        self.analog_output.StartTask()
        self.analog_output.WriteAnalogF64(1, 1, 10.0, DAQmx_Val_GroupByScanNumber,\
            array(self.vout_buffer[0]), byref(read), None)
#        self.analog_output.CfgSampClkTiming("", 1/sampling_interval ,DAQmx_Val_Rising, \
#            DAQmx_Val_ContSamps, 1)
    
    #def StartTask(self):
    #    self.analog_output.StartTask()
    #    super(CallbackTask, self).StartTask()        
    #                        
    #def StopTask(self):
    #    read = c_int32()
    #    self.analog_output.WriteAnalogF64(1, 1, 10.0, DAQmx_Val_GroupByScanNumber,\
    #        array(0.0), byref(read), None)
    #    self.analog_output.StopTask()
    #    self.analog_output.ClearTask()
    #    
    #    super(CallbackTask, self).StopTask()        

    def Sample(self):
        self.sample_number += 1
        out = []
        read = c_int32()
        self.StartTask()
        self.ReadAnalogF64(AVERAGE_SAMPLES, 50.0, DAQmx_Val_GroupByScanNumber, self.data, \
            AVERAGE_SAMPLES * 2, byref(read), None)
        self.StopTask()
        out.append(mean(self.data[:,0]))
        out.append(mean(self.data[:,1]))
        out.append(self.sample_number)
        out.append(time() - self.start_time)
         
#        logger.info('out: %s', out)
        self.output = out
        if self.sample_number >= len(self.vout_buffer):
            self.analog_output.WriteAnalogF64(1, 1, 10.0, DAQmx_Val_GroupByScanNumber,\
                array(0.0), byref(read), None)
            self.parent_obj.measurement_finished()
            return
        self.analog_output.WriteAnalogF64(1, 1, 10.0, DAQmx_Val_GroupByScanNumber,\
            array(self.vout_buffer[self.sample_number]), byref(read), None)
        #return 0

    #def DoneCallback(self, status):
    #    logger.info("Status", status.value)
    #    return 0 # The function should return an integer

class NI6215Handler(Handler):
    def closed(self, info, is_ok):
        if hasattr(info.object.acqusition_task, 'StopTask') and info.object.running:
            info.object.acqusition_task.StopTask()
            info.object.acqusition_task.ClearTask()

#@provides(IInstrument)
class NI6215(HasTraits):
    """Dummy instrument for generation of values (V, I, R) over time"""
    CHANNEL_CELL_WIDTH = 25.0

    #### 'IInstrument' interface #############################################
    name = Unicode('NI-DAQmx')
    x_units = Dict({0: 'Voltage'})
    y_units = Dict({0: 'Current'})
    measurement_info = Dict()

    running = Bool(False)
    output_channels = Dict({0:'ai00', 1:'ai01', 2:'ai02', 3:'ai03', \
                            4:'ai04', 5:'ai05', 6:'ai06', 7:'ai07', \
                            8:'ai08', 9:'ai09', 10:'ai10', 11:'ai11', \
                            12:'ai12', 13:'ai13', 14:'ai14', 15:'ai15'})
    enabled_channels = List(Bool)

    sampling_interval = Range(0.05, 10, 1)
    start_stop = Event
    refresh_list = Button
    ai0 =Bool(True)
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

    start_voltage = Float
    step_voltage = Float
    stop_voltage = Float
    current_voltage= Float
    current_current = Float
    update_interval = Float(0.2)

    acqusition_task = Instance(CallbackTask)
    acquired_data = List(Dict)
    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    timer = Instance(Timer)
    sweep_name = Str
    traits_view = View(HGroup(Label('Device: '), Item('selected_device', \
                        show_label = False,
                            editor = EnumEditor(name='_available_devices_map'), \
                            enabled_when='not running'),
                            Item('refresh_list')),
                        Group(Item('start_voltage', enabled_when='not running'),
                            Item('step_voltage', enabled_when='not running'),
                            Item('stop_voltage', enabled_when='not running'),
                            Item('current_voltage', enabled_when='False', label = 'U [V]'),
                            Item('current_current', enabled_when='False', label = 'I [A]')),
                        Item('update_interval', enabled_when='not running'),
                        HGroup(Label('Channels:'), spring, VGroup(HGroup(\
                        Item('ai0', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai1', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai2', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai3', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH)), HGroup(\
                        Item('ai4', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai5', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai6', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai7', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH)), HGroup(\
                        Item('ai8', enabled_when='False', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai9', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai10', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai11', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH)), HGroup(\
                        Item('ai12', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai13', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai14', enabled_when='False', springy = True, width = CHANNEL_CELL_WIDTH), \
                        Item('ai15', enabled_when='not running', springy = True, width = CHANNEL_CELL_WIDTH)))),
                        Item('sweep_name'),
                        Item('start_stop', label = 'Start/Stop',
                                editor = ButtonEditor(label_value='button_label')),\
                                handler=NI6215Handler)

    def __init__(self):

        self.on_trait_change(self.add_data, 'acqusition_task.output')
        self.on_trait_change(self.channel_changed, 'ai+')


    def _enabled_channels_default(self):
        l = [False] * 16
        l[0] = True
        return l

    def __available_devices_map_default(self):
        s = str('000000000000000000000000000000000000000000000000000')
        PyDAQmx.DAQmxGetSysDevNames(s, len(s))
        (a,b,c) = s.partition('\x00')
        devs=a.split(', ')
        serial = c_uint32(0)
        devices=[]
        for d in devs:
            if len(d) > 0:
                PyDAQmx.DAQmxGetDevProductType(d, s, len(s))
                (a,b,c) = s.partition('\x00')
                if a.startswith('USB-62'):
                    PyDAQmx.DAQmxGetDevSerialNum(d, serial)
                    devices.append((d, a + ' - ' + hex(serial.value)[2:-1].upper()))
                if a.startswith('PCI-'):
                    PyDAQmx.DAQmxGetDevSerialNum(d, serial)
                    devices.append((d, a + ' - In computer'))
            else:
                break
        retval = dict((device[0], device[1]) for device in devices)
        #logger.info('_available_devices_map_default %s', retval)
        return retval

    def _start_voltage_default(self):
        return DEFAULT_START_VOLTAGE

    def _stop_voltage_default(self):
        return DEFAULT_STOP_VOLTAGE

    def _step_voltage_default(self):
        return DEFAULT_STEP_VOLTAGE

    @on_trait_change('_available_devices_map')
    def __available_devices_map_changed(self):
        if self.selected_device not in self._available_devices_map.keys():
            self.selected_device = self._available_devices_map.items()[0][0]

    def _selected_device_default(self):
        try:
            device = self._available_devices_map.items()[0][0]
        except IndexError:
            return ''
        #self._selected_device_changed(device)
        return device

    def _refresh_list_fired(self):
        self._available_devices_map = self.__available_devices_map_default()
        self.__available_devices_map_changed()

    def measurement_finished(self):
        #self.acqusition_task.ClearTask()
        self.acqusition_task.analog_output.StopTask()
        self._start_stop_fired(None, None)

    def add_data(self):
        #data = self.acqusition_task.output
        #if len(data) < 18:
        #    return
        if self.acqusition_task is None:
            return
        d = dict()
        for i, enabled in enumerate(self.enabled_channels):
            try:
                self.current_voltage = self.acqusition_task.output[0]
            except IndexError:
                self.current_voltage = 0
            try:
                temp = self.acqusition_task.output[1]
            except IndexError:
                temp = 0
            self.current_current = (self.current_voltage - temp) / 1000.0
            d[self.output_channels[i]] = (dict({self.x_units[0]:self.current_voltage,}),\
                            dict({self.y_units[0]:self.current_current}))
        self.acquired_data.append(d)



    def start(self):
        self.measurement_info = {'name': self.sweep_name,
                    'start_voltage': self.start_voltage,
                    'stop_voltage': self.stop_voltage,
                    'step_voltage': self.step_voltage
                    }
        if len(self.measurement_info['name']) is 0:
            self.measurement_info.pop('name')
        self.running = True
        self.acq_start_time = time()
        if self.acqusition_task is not None:
            del self.acqusition_task
            del self.timer
        self.acqusition_task = CallbackTask()
        channels = []
        for i, enabled in enumerate(self.enabled_channels):
            if enabled:
               channels.append('ai' + str(i))
        self.acqusition_task.setup(self.selected_device, \
            channels[0], self.sampling_interval, \
            [(self.start_voltage + j * self.step_voltage) \
                for j in xrange(int((self.stop_voltage - self.start_voltage)/self.step_voltage)+1)], self)
    
        if self.timer is None:
            self.timer = Timer(self.update_interval * 1000, self.acqusition_task.Sample)
        else:
            self.timer.Start(self.update_interval * 1000)

    def stop(self):
        if self.timer is not None:
            self.timer.Stop()
        self.running = False



    ##########################################################################

    def _start_stop_fired(self, old, new):
        if self.running:
            self.button_label= 'Start'
            self.stop()
        else:
            self.button_label = 'Stop'
            self.start()


    def channel_changed(self, obj, name, new):
        ec = [False] * len(self.enabled_channels)
        ec[int(name[2:])] = new
        self.enabled_channels[int(name[2:])] = new
        if new is False:
            return
        channels = [a for a in self.all_trait_names() if a.startswith('ai') and len(a) > 2 and a[2].isalnum()]
        for channel in channels:
            if channel is not name:
                if getattr(self, channel):
                    setattr(self, channel, False)
            else:
                setattr(self, channel, new)






if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    n = NI6215()
    w = n.configure_traits()

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
