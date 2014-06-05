from enthought.traits.api import HasTraits, Bool, Int, List, Float, Instance, Any,\
    Str, Button
from traitsui.api import Item, View, Group, HGroup, Handler, \
    TableEditor, EnumEditor
from traitsui.table_column import NumericColumn
import logging
import serial
import os
import time
from serial.tools import list_ports
from pyface.timer.api import Timer
import numpy as np
import threading
import Queue
logger = logging.getLogger(__name__)

class SerialHandler(threading.Thread):
    BAUD_RATE = 115200
    UPDATE_INTERVAL = 500.0
    exit_flag = False

    def __init__(self, set_temp_queue, get_temp_queue, selected_com_port):
        threading.Thread.__init__(self)
        self.set_temp_queue = set_temp_queue
        self.get_temp_queue = get_temp_queue

        self.selected_com_port = selected_com_port

    def run(self):
        try:
            self.ser = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=0.4)
        except serial.SerialException as e:
            logger.error('Error opening COM port: %s', e)
        logger.info('ser %s', self.ser)
        time.sleep(1.5)
        #self.ser.read()
        while self.ser.inWaiting() > 0:
            self.ser.read()
#        self.ser.write('S50')
#        self.ser.write('S11')
#        self.ser.write('S10')

        while not self.exit_flag:
            time.sleep(self.UPDATE_INTERVAL / 1000.0)
            msg = ''
            self.ser.write('T')
            time.sleep(0.01)
            response = self.ser.readline()
            temperature = 0
            if response is not '':
                try:
                    temperature = int(response)
                except ValueError:
                    temperature = 1234

            logger.info('serilahandler %s', response)

            try:
                self.get_temp_queue.put_nowait(temperature)
            except Queue.Full:
                logger.info('Queue full')
                pass
            if not self.set_temp_queue.empty():
                msg = self.set_temp_queue.get()
                self.set_temp_queue.task_done()

            if msg is not '':
                logger.info('SerialHandler, Got %s from set_temp_queue', msg)
                self.ser.write(msg)
        logger.info('SerialHandler stopping')
        self.ser.close()






class TableEntry(HasTraits):

    time = Int
    start_temp = Int
    end_temp = Int
    remaining = Int

    def _on_time_changed(self, new):
        self.remaining = new

table_editor = TableEditor(
    columns = [ NumericColumn( name = 'time', label = 'Seconds', horizontal_alignment = 'right'),
                NumericColumn( name = 'start_temp', label = 'Start temp'),
                NumericColumn( name = 'end_temp', label = 'End temp'),
                NumericColumn( name = 'remaining', editable = False, label = 'Left', width = 70, read_only_cell_color = 0xF4F3EE)],
    deletable   = True,
    sort_model  = False,
    auto_size   = True,
    orientation = 'vertical',
    show_toolbar = False,
    sortable = False,
    row_factory = TableEntry )

class TemperatureControlHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        info.object.start_stop(False)
        return

class TemperatureControlPanel(HasTraits):
    UPDATE_INTERVAL = 500.0
    BAUD_RATE = 115200
    pane_name = Str('Temperature control ')
    pane_id = Str('sensorscience.unimeas.temperatur_control_pane')
    enable = Bool(False)
    timer = Instance(Timer)

    table_entries = List(TableEntry)
    current_row = Int(0)
    current_temp = Int(0)
    actual_temp = Int
    current_time = Float
    row_start_time = Float
    running = False

    controller = Instance(serial.Serial)
    temperature_table = List(Int)
    selected_com_port = Str
    com_ports_list = List(Str)
    test_com = Button


    set_temp_queue = Instance(Queue.Queue)
    get_temp_queue = Instance(Queue.Queue)


    traits_view = View(HGroup(Item('selected_com_port',  label = 'Com port', \
                                editor = EnumEditor(name='com_ports_list'), \
                                enabled_when='not running'),
                                Item('test_com', enabled_when = 'not running')),
                    Item('enable'),
        Group(
            Item( 'table_entries',
                  show_label  = False,
                  editor      = table_editor,
                  enabled_when = 'not running'
            ),
            show_border = True,
        ),
        Item('actual_temp'),
        resizable = True,
        kind      = 'live',
        handler = TemperatureControlHandler
    )

    def _onTimer(self):
        self.current_time += (self.UPDATE_INTERVAL / 1000)
        index = int(np.floor(self.current_time))
        if index >= len(self.temperature_table):
            self.start_stop(False)
        if self.temperature_table[index] is not self.current_temp:
            self.current_temp = self.temperature_table[index]
        if self.current_row >= len(self.table_entries):
            return
        time_left = self.table_entries[self.current_row].time + self.row_start_time - self.current_time
        self.table_entries[self.current_row].remaining = int(time_left)
        if self.table_entries[self.current_row].remaining < 1:
            self.current_row += 1
            self.row_changed(time_left)


        if not self.get_temp_queue.empty():
            self.actual_temp = self.get_temp_queue.get()
            self.get_temp_queue.task_done()


    def _table_entries_default(self):
        return [TableEntry(time = 10, start_temp = 50, end_temp = 50, remaining = -1),
                TableEntry(time = 5, start_temp = 50, end_temp = 150, remaining = -1),
                TableEntry(time = 10, start_temp = 150, end_temp = 150, remaining = -1),
                TableEntry(time = 20, start_temp = 150, end_temp = 100, remaining = -1),]

    def start_stop(self, running):
        if not self.enable:
            return
        self.running = running
        if running:
            logger.info('Starting')
            self.calculate_temperature_table()
            #self.controller = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=1)
            self.current_row = 0
            self.row_changed(0)
            self.current_time = 0

            self.set_temp_queue = Queue.Queue(2)
            self.get_temp_queue = Queue.Queue(2)
            self.serial_handler = SerialHandler(self.set_temp_queue, self.get_temp_queue,
                self.selected_com_port)
            self.serial_handler.start()
            self.current_temp = self.temperature_table[0]
            self.timer = Timer(self.UPDATE_INTERVAL, self._onTimer)

        else:
            logger.info('Stopping')
            #if self.controller is not None:
            #    self.controller.close()
            if self.timer is not None:
                self.timer.Stop()
            if self.serial_handler is not None:
                self.serial_handler.exit_flag = True
                while self.serial_handler.isAlive():
                    self.serial_handler.join(0.4)
                    logger.info('Waiting for serial_handler')

    def add_data(self, data):
        pass

    def calculate_temperature_table(self):
        self.temperature_table = []
        for row in self.table_entries:
            slope = (row.end_temp - row.start_temp) / float(row.time - 1)
            #logger.info('Slope of row %s is %f', row, slope)
            for i in range(row.time):
                self.temperature_table.append(int(i * slope + row.start_temp))

    def row_changed(self, remainder):
        self.row_start_time = self.current_time + remainder
        if self.current_row >= len(self.table_entries):
            return

    def _current_temp_changed(self, new):
        msg = 'S%d' % new
        logger.info('Send %s to temp controller', msg)
        self.set_temp_queue.put(msg)


#    def _com_ports_list_default(self):
#        return ['/dev/ttyACM0']


    def _com_ports_list_default(self):
        l = []
        if os.name == 'nt':
            # windows
            for i in range(256):
                try:
                    s = serial.Serial(i)
                    s.close()
                    l.append('COM' + str(i + 1))
                except serial.SerialException:
                    pass
        else:
            # unix
            for port in list_ports.comports():
                l.append(port[0])
        return l

    def _test_com_fired(self):
        ser = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=1)
        ser.write('C')
        result = ser.readline()
        logger.info('result %s, ser %s', result, ser)
        if result.find('OK') is 0:
            logger.info('Connection OK!')
        #result = ser.read(30)
        ser.close()

    def get_pt100_temp(self):
        self.controller.write('T')
        line = self.controller.readline()
        return int(line)


class TestSerial(HasTraits):
    controller = Instance(serial.Serial)
    selected_com_port = Str
    com_ports_list = List(Str)

    test_com = Button
    traits_view = View(HGroup(Item('selected_com_port',  label = 'Com port', \
                                editor = EnumEditor(name='com_ports_list'), \
                                enabled_when='not running'), Item('test_com', enabled_when = 'selected_com_port != \'\'')))

    def _test_com_fired(self):
        ser = serial.Serial(self.selected_com_port, 115200, timeout=1)
        logger.info('%s', ser)
        #ser.flushOutput()
        #ser.flushInput()


        #ser.writelines(['50'])
        #self.actual_temp = int(ser.readline()[:-2])
        #while ser.inWaiting() > 0:
        #    ser.read(1)
        #logger.info('buffer %d', ser.inWaiting())

        #result = ser.readlines(30)
        #logger.info('result %s, buffer %d, count %d', result, ser.inWaiting(), count)
        lines = []
        while True:
            line = ser.readline()
            lines.append(line.decode('utf-8').rstrip())

            # wait for new data after each line
            timeout = time.time() + 0.1
            while not ser.inWaiting() and timeout > time.time():
                pass
            if not ser.inWaiting():
                break
        logger.info('lines1 %s', lines)
        count = ser.write('C')
        lines = []
        while True:
            line = ser.readline()
            lines.append(line.decode('utf-8').rstrip())

            # wait for new data after each line
            timeout = time.time() + 0.1
            while not ser.inWaiting() and timeout > time.time():
                pass
            if not ser.inWaiting():
                break
        logger.info('lines2 %s', lines)
        for r in lines:
            if r.find('OK') is 0:
                logger.info('Connection OK!')
        #result = ser.read(30)
        ser.close()

    def _com_ports_list_default(self):
        l = []
        if os.name == 'nt':
            # windows
            for i in range(256):
                try:
                    s = serial.Serial(i)
                    s.close()
                    l.append('COM' + str(i + 1))
                except serial.SerialException:
                    pass
        else:
            # unix
            for port in list_ports.comports():
                l.append(port[0])
        return l

if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.handlers = []
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    g=TemperatureControlPanel()
    g.configure_traits()
    #g=TestSerial()
    #g.configure_traits()
