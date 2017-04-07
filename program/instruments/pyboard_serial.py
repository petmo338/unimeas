import logging
import serial
import struct
from traits.api import HasTraits, Instance, Bool, Dict, \
    List, Unicode, Str, Event, Button, Float, Int
from traitsui.api import View, Item, ButtonEditor, \
    EnumEditor, Label, HGroup, Handler, RangeEditor
from time import time, sleep
from pyface.timer.api import Timer
import threading

logger = logging.getLogger(__name__)


class SerialHandler(threading.Thread):
    POLL_INTERVAL = 20
    RESPONSE_UNPACK_FORMAT = 'hHH'

    exit_flag = False
    is_connected = False
    ser = Instance(serial.Serial)
    lock = threading.Lock()
    values = (0, 0, 0)

    def __init__(self, selected_com_port):
        threading.Thread.__init__(self)
        self.ser = selected_com_port
        self.is_connected = True

    def run(self):
        while not self.exit_flag:
            sleep(self.POLL_INTERVAL / 1000.0)
            try:
                response = self.ser.read(struct.calcsize(self.RESPONSE_UNPACK_FORMAT))
            except serial.SerialException:
                self.is_connected = False
                self.ser.close()
                self.exit_flag = True
                logger.error('Lost connection with COM port')

            if len(response) == struct.calcsize(self.RESPONSE_UNPACK_FORMAT):
                self.lock.acquire()
                self.values = struct.unpack(self.RESPONSE_UNPACK_FORMAT, response)
                self.lock.release()
        logger.info('Stopping serial thread')


class PyboardHandler(Handler):

    def closed(self, info, is_ok):
        """
        Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """

        if info.object.serial_handler is not None:
            info.object.serial_handler.exit_flag = True

        if info.object.serialport is not None:
            if info.object.serialport.isOpen():
                info.object.serialport.close()


class PyBoardSerial(HasTraits):
    """Instrument for communication with PyBoard"""

    start_stop = Event
    refresh_list = Button

    button_label = Str('Start')

    output_unit = 0
    timebase = 0
    acquired_data = List(Dict)
    available_ports = List(Str)
    serialport = Instance(serial.Serial)
    portname = Str
    timer = Instance(Timer)
    name = Unicode('PyBoardNOxAdapter')
    measurement_info = Dict()
    x_units = Dict({0: 'SampleNumber', 1: 'Time'})
    y_units = Dict({0: 'NOx', 1: 'lin_lambda'})
    running = Bool(False)
    output_channels = Dict({0: 'chan0'})
    enabled_channels = List(Bool)
    acq_start_time = Float
    sample_nr = Int
    sample_interval = Float(1)
    serial_out = Str
    serial_handler = Instance(SerialHandler)
    traits_view = View(
        HGroup(
            Label('Device: '), Item(
                'portname', show_label=False, editor=EnumEditor(name='available_ports'),
                enabled_when='not running'
            ),
            Item('refresh_list')
        ),
        Item('start_stop', label='Start/stop acqusistion', editor=ButtonEditor(
            label_value='button_label')
        ),

        Item('serial_out', label='Recv. data', style="readonly"),
        Item('sample_interval', editor=RangeEditor(
            low=0.05, high=10, is_float=True, format="%.2f"), enabled_when='not running'),
        handler=PyboardHandler)

    def _enabled_channels_default(self):
        return [True]

    def _available_ports_default(self):
        import serial.tools.list_ports as lp
        ll = []
        if int(serial.VERSION[0]) == 2:
            return [l[0] for l in lp.comports()]
        else:
            for p in lp.grep('F055:9800'):
                ll.append(p.device)
        return ll

    def _poll_queue(self):
        self.serial_handler.lock.acquire()
        is_connceted = self.serial_handler.is_connected
        retval = self.serial_handler.values
        self.serial_handler.lock.release()
        if not is_connceted:
            self._start_stop_fired()
        return retval

    def _refresh_list_fired(self):
        self.available_ports = self._available_ports_default()

    def _portname_changed(self):
        self.serialport = None

    def add_data(self):
        self.sample_nr += 1
        measurement_time = time() - self.acq_start_time
        (nox_ppm, lambda_linear, oxygen_millivolt) = self._poll_queue()
        if not self.running:
            return
        self.serial_out = "NOx: " + str(nox_ppm) + u", lin_\u03BB:" + str(lambda_linear)
        dict_data = dict()
        for i, enabled in enumerate(self.enabled_channels):
            dict_data[
                self.output_channels[i]] = (
                dict(
                    {self.x_units[0]: self.sample_nr, self.x_units[1]: measurement_time}),
                    dict({self.y_units[0]: nox_ppm, self.y_units[1]: 1000.0/lambda_linear}))  # From Zhafira
        self.acquired_data.append(dict_data)
        self.timer = Timer.singleShot(max(0, (self.sample_interval * self.sample_nr -
                                              (time() - self.acq_start_time))*1000), self.add_data)

    def start(self):
        self.running = True
        self.acq_start_time = time()
        self.sample_nr = 0
        if self.serialport is None:
            try:
                self.serialport = serial.Serial(self.portname, 115200, timeout=0.045)
            except Exception as e:
                logger.error(e)
                self.stop()
                return
        else:
            self.serialport.open()
        self.serial_handler = SerialHandler(self.serialport)
        self.serial_handler.start()
        self.timer = Timer.singleShot(self.sample_interval * 1000, self.add_data)

    def stop(self):
        self.serial_handler.exit_flag = True
        self.serial_handler.join()
        self.serial_handler = None
        self.running = False
        if self.serialport is not None:
            self.serialport.close()

    def _start_stop_fired(self):
        if self.portname == '':
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
    n = PyBoardSerial()
    n.configure_traits()
