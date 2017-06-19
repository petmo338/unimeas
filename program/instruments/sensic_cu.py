import logging
import serial
import os
from traits.api import HasTraits, Range, Instance, Bool, Dict, \
    List, Unicode, Str, Int, Float, on_trait_change, Event, Button
from traitsui.api import View, Item, Group, ButtonEditor, \
    EnumEditor, Label, HGroup, spring, VGroup, Handler
import traits.has_traits
# traits.has_traits.CHECK_INTERFACES = 2
from time import time, sleep
from numpy import zeros, ones, linspace
from pyface.timer.api import Timer

from i_instrument import IInstrument

logger = logging.getLogger(__name__)


class SenSiCCUHandler(Handler):
    def closed(self, info, is_ok):
        if info.object.running is True:
            info.object.stop()


# @provides(IInstrument)
class SenSiCCU(HasTraits):
    """Dummy instrument for generation of values (V, I, R) over time"""
    CHANNEL_CELL_WIDTH = 25.0

    #    sampling_interval = Range(0.05, 10, 1)
    start_stop = Event
    refresh_list = Button
    drain1 = Bool(True)
    drain2 = Bool(True)
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

    temperature = Int(20)
    samples_per_sec = Int(1)
    max_cur_drain1 = Int(500)
    min_cur_drain1 = Int(0)
    max_cur_drain2 = Int(500)
    min_cur_drain2 = Int(0)
    set_parameters = Button

    #    output_unit = 0
    #    timebase = 0
    sample_interval = 500
    acquired_data = List(Dict)
    _available_ports = List(Unicode)
    serialport = Instance(serial.Serial)
    portname = Str
    serial_response = ''
    last_drain1 = Float(0.0)
    last_drain2 = Float(0.0)
    last_temp = Float(0.0)
    last_time = Float(0.0)

    traits_view = View(HGroup(Label('Device: '), Item('portname',
                                                      show_label=False,
                                                      editor=EnumEditor(name='_available_ports'),
                                                      enabled_when='not running'),
                              Item('refresh_list')),
                       Item('last_drain1', style='readonly'), Item('last_drain2', style='readonly'),
                       Group(Item('temperature'), Item('samples_per_sec'),
                             HGroup(Item('max_cur_drain1'), Item('min_cur_drain1')),
                             HGroup(Item('max_cur_drain2'), Item('min_cur_drain2')),
                             Item('set_parameters', label='Set'),
                             show_border=True, label='Parameters'),
                       Item('start_stop', label='Start/Stop Acqusistion',
                            editor=ButtonEditor(label_value='button_label')),
                       handler=SenSiCCUHandler)

    # def __init__(self):
    #    self.on_trait_change(self.add_data, 'acqusition_task.output')
    #    self.on_trait_change(self.channel_changed, 'ai+')

    def _set_parameters_fired(self):
        enter = '\r\n'
        if self.serialport.isOpen():
            self.serialport.flushOutput()
            self.serialport.read(self.serialport.inWaiting())
            self.timer = None
            self.serialport.write('A')
            sleep(0.1)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            self.serialport.write(str(self.temperature) + enter)
            sleep(0.1)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            self.serialport.write(str(0) + enter)
            sleep(0.1)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            self.serialport.write(str(self.samples_per_sec) + enter)
            sleep(0.1)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            self.serialport.write(str(self.max_cur_drain1) + enter)
            sleep(0.1)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            self.serialport.write(str(self.min_cur_drain1) + enter)
            sleep(0.1)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            self.serialport.write(str(self.max_cur_drain2) + enter)
            sleep(0.1)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            self.serialport.write(str(self.min_cur_drain2) + enter)
            sleep(0.1)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            self.serialport.write(str(0) + enter)
            sleep(0.1)
            #            sleep(0.2)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            sleep(0.1)
            self.serialport.write(enter)
            logger.debug(bytearray(self.serialport.read(self.serialport.inWaiting())))
            sleep(0.1)
            self.timer = Timer.singleShot(500, self.add_data)

    def _calibrate_temp_fired(self):
        self.timer = None

    def _enabled_channels_default(self):
        return [self.drain1, self.drain2]

    def __available_ports_default(self):
        import serial.tools.list_ports as lp
        valid_ports = [p[0] for p in lp.grep('USB')]
        return valid_ports


    def _refresh_list_fired(self):
        self._available_devices = self.__available_ports_default()

    def _portname_changed(self, new):
        if new is '':
            return
        if self.serialport != None:
            self.serialport.close()
        # try:
        #     self.serialport = serial.Serial(self.portname, 115200, timeout=0.1)
        # except Exception as e:
        #     logger.error(e)
        #     return
        # # self.serialport.open()
        # self.serialport.flushInput()
        # self.timer = Timer.singleShot(self.sample_interval, self.add_data)

    def add_data(self):
        if not self.running:
            return
        self.timer = Timer.singleShot(self.sample_interval, self.add_data)
        self.response_remainder = self.serial_response[-15:]
        self.serial_response = bytearray(self.serialport.inWaiting())
        self.serialport.readinto(self.serial_response)
        d = self._parse_data(self.response_remainder + self.serial_response)
        data_dict = dict()
        if self.running is True:
            for entry in d:
                data_dict[self.output_channels[0]] = entry[0]
                data_dict[self.output_channels[1]] = entry[1]
                self.acquired_data.append(data_dict)

                # logger.debug(data_dict)

    def _parse_data(self, data):

        measurement_time = time() - self.acq_start_time
        value_screenpos_map = {'drain1': '009;100H', 'drain2': '015;100H', 'Temperature': '019;100H',
                               'Resistance': '020;100H', 'Percent': '021;100H'}
        d = dict()
        max_length = 0

        for (key, value) in value_screenpos_map.iteritems():
            part_data = data
            index = part_data.find(value)
            d[key] = []
            while index != -1:
                val = part_data[index + 8: index + 15]
                val = val.replace(',', '.')
                val.lstrip()
                try:
                    val = float(val)
                except ValueError:
                    break
                d[key].append(val)
                part_data = part_data[index + 15:]
                index = part_data.find(value)
            if len(d[key]) > max_length:
                max_length = len(d[key])
            elif len(d[key]) == 0:
                if key == 'drain1':
                    d[key] = [self.last_drain1]
                if key == 'drain2':
                    d[key] = [self.last_drain2]
                if key == 'Temperature':
                    d[key] = [self.last_temp]
            else:
                if key == 'drain1':
                    self.last_drain1 = d[key][0]
                if key == 'drain2':
                    self.last_drain2 = d[key][0]
                if key == 'Temperature':
                    self.last_temp = d[key][0]

        retval = []
        sample_times = linspace(self.last_time, measurement_time, max_length, endpoint=False)
        sample_numbers = linspace(self.sample_nr, self.sample_nr + max_length, max_length, endpoint=False)
        d['drain1'] = d['drain1'] * max_length
        d['drain2'] = d['drain2'] * max_length
        d['Temperature'] = d['Temperature'] * max_length
        for i in xrange(max_length):
            retval.append(((dict({self.x_units[0]: int(sample_numbers[i]), self.x_units[1]: sample_times[i], }),
                            dict({self.y_units[0]: d['drain1'][i] * 1e-6,
                                  self.y_units[1]: d['Temperature'][i],
                                  self.y_units[2]: d['Resistance'][i],
                                  self.y_units[3]: d['Percent'][i], })),
                           (dict({self.x_units[0]: int(sample_numbers[i]), self.x_units[1]: sample_times[i], }),
                            dict({self.y_units[0]: d['drain2'][i] * 1e-6,
                                  self.y_units[1]: d['Temperature'][i],
                                  self.y_units[2]: d['Resistance'][i],
                                  self.y_units[3]: d['Percent'][i], }))))
        self.sample_nr += max_length
        self.last_time = measurement_time
        # logger.debug(retval)
        return retval


        #### 'IInstrument' interface #############################################

    name = Unicode('SenSiC CU')
    measurement_info = Dict()
    x_units = Dict({0: 'SampleNumber', 1: 'Time'})
    y_units = Dict({0: 'Current', 1: 'Temperature', 2: 'Resistance', 3: 'Percent'})
    running = Bool(False)
    output_channels = Dict({0: 'drain1', 1: 'drain2'})
    enabled_channels = List(Bool)

    def start(self):
        self.acquired_data = []
        self.running = True
        self.acq_start_time = time()
        self.sample_nr = 0
        if self.serialport is None:
            try:
                self.serialport = serial.Serial(self.portname, 115200, timeout=0.2)
            except Exception as e:
                logger.error(e)
                self.stop()
                return
        else:
            if not self.serialport.isOpen():
                self.serialport.open()
        self.serialport.flushInput()

        self.serialport.write('j')
        self.timer = Timer.singleShot(self.sample_interval, self.add_data)


    def stop(self):
        logger.info('stop()')
        self.running = False
        if self.serialport is not None:
            #            self.serialport.write('b')
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
    n = SenSiCCU()
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
