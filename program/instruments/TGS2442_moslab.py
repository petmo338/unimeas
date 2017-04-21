import logging
import serial
import os
from traits.api import HasTraits, Range, Instance, Bool, Dict, \
    List, Unicode, Str, Int, on_trait_change, Event, Button, Float
from traitsui.api import View, Item, Group, ButtonEditor, \
    EnumEditor, Label, HGroup, spring, VGroup, Handler
import traits.has_traits
# traits.has_traits.CHECK_INTERFACES = 2
from time import time, sleep
from numpy import zeros, ones
from pyface.timer.api import Timer

from i_instrument import IInstrument

logger = logging.getLogger(__name__)


class TGS2442Handler(Handler):
    def closed(self, info, is_ok):
        if info.object.serialport is not None:
            if info.object.serialport.isOpen():
                info.object.serialport.close()


# @provides(IInstrument)
class TGS2442_MOSLab(HasTraits):
    """Dummy instrument for generation of values (V, I, R) over time"""
    CHANNEL_CELL_WIDTH = 25.0

    #    sampling_interval = Range(0.05, 10, 1)
    start_stop = Event
    refresh_list = Button
    #    ai0 =Bool(True)
    # ai1 =Bool(False)
    # ai2 =Bool(False)
    # ai3 =Bool(False)
    # ai4 =Bool(False)
    # ai5 =Bool(False)
    # ai6 =Bool(False)
    # ai7 =Bool(False)
    # ai8 =Bool(False)
    # ai9 =Bool(False)
    # ai10 =Bool(False)
    # ai11 =Bool(False)
    # ai12 =Bool(False)
    # ai13 =Bool(False)
    # ai14 =Bool(False)
    # ai15 =Bool(False)
    button_label = Str('Start')

    output_unit = 0
    timebase = 0
    acquired_data = List(Dict)
    _available_ports = List(Unicode)
    serialport = Instance(serial.Serial)
    portname = Str
    sensor_output_voltage = Float
    sample_nr = Int

    traits_view = View(HGroup(Label('Device: '), Item('portname',
                                                      show_label=False,
                                                      editor=EnumEditor(name='_available_ports'),
                                                      enabled_when='not running'),
                              Item('refresh_list')),
                       Item('start_stop', label='Start/Stop Acqusistion',
                            editor=ButtonEditor(label_value='button_label')),
                       Item('sensor_output_voltage', style='readonly', format_str='%.3f'),
                       Item('sample_nr', style='readonly'),
                       handler=TGS2442Handler)

    # def __init__(self):
    #    self.on_trait_change(self.add_data, 'acqusition_task.output')
    #    self.on_trait_change(self.channel_changed, 'ai+')

    def _enabled_channels_default(self):
        return [True]

    # def __available_ports_default(self):
    #     l = []
    #     if os.name == 'nt':
    #         # windows
    #         for i in range(0, 8):
    #             #                l.append('COM' + str(i + 1))
    #             try:
    #                 s = serial.Serial(i)
    #                 s.close()
    #                 l.append('COM' + str(i + 1))
    #             except serial.SerialException:
    #                 pass
    #     else:
    #         # unix
    #         import serial.tools.list_ports as lp
    #         for port in lp.comports():
    #             l.append(port[0])
    #     return l
    #

    def __available_ports_default(self):
        import serial.tools.list_ports as lp
        valid_ports = [p[0] for p in lp.grep('Uno')]
        return valid_ports

    def _refresh_list_fired(self):
        self._available_devices = self.__available_ports_default()

    def _portname_changed(self):
        self.serialport = None

    def add_data(self):
        if not self.running:
            return
        b = bytearray(2)
        self.sample_nr += 1
        measurement_time = time() - self.acq_start_time
        if self.serialport.readinto(b) == 2:
            dig = ((b[0] * 256 + b[1]) / 1024.0)
            if dig > 1:
                dig = 1
            self.sensor_output_voltage = 4.9 * dig

        d = dict()
        for i, enabled in enumerate(self.enabled_channels):
            d[self.output_channels[i]] = (dict({self.x_units[0]: self.sample_nr,
                                                self.x_units[1]: measurement_time}),
                                          dict({self.y_units[0]: self.sensor_output_voltage}))
        self.acquired_data.append(d)
        self.timer = Timer.singleShot(max(0, ((float(self.sample_nr)) - measurement_time) * 1000), self.add_data)

    #### 'IInstrument' interface #############################################
    name = Unicode('TGS2442_MOSLab')
    measurement_info = Dict()
    x_units = Dict({0: 'SampleNumber', 1: 'Time'})
    y_units = Dict({0: 'Voltage'})
    running = Bool(False)
    output_channels = Dict({0: 'chan0'})
    enabled_channels = List(Bool)


    def start(self):
        self.running = True
        self.acq_start_time = time()
        self.sample_nr = 0
        if self.serialport is None:
            try:
                self.serialport = serial.Serial(self.portname, 57600, timeout=0.2)
            except Exception as e:
                logger.error(e)
                self.stop()
                return
        else:
            self.serialport.open()
        # self.serialport.write('a')
        self.serialport.flush()
        self.timer = Timer.singleShot(900, self.add_data)

    def stop(self):
        logger.info('stop()')
        self.running = False
        if self.serialport is not None:
            self.serialport.write('b')
            self.serialport.close()

    ##########################################################################

    def _start_stop_fired(self, old, new):
        if self.portname == '':
            return
        if self.running:
            self.button_label = 'Start'
            self.stop()
        else:
            self.button_label = 'Stop'
            self.start()


            # def channel_changed(self, obj, name, new):
            #    self.enabled_channels[int(name[2:])] = new


if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    n = TGS2442_MOSLab()
    n.configure_traits()

#    a = AcquisitionThread()
#    d = DummySourcemeterTime()
#    d.tracer = SimpleTracer()
#    d.on_trait_change(d._log_changed)
#    d.traits_view = View(d.parameter_group)

#    d.tracer.configure_traits()
#    d.configure_traits()

# d.start()
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
