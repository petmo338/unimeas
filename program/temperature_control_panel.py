from enthought.traits.api import HasTraits, Bool, Int, List, Float, Instance, Any,\
    Str, Button, Dict
from traitsui.api import Item, View, Group, HGroup, Handler, \
    TableEditor, EnumEditor, spring
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
import numpy as np
logger = logging.getLogger(__name__)

def pv_to_temp(pv, offset = 0.0):
    PT100_TABLE_STEP_DEG = 30.0
    MIN_TEMP = -10
    MAX_TEMP = 710
    Pt100 = np.array([96.09, 107.79, 119.40, 130.90, 142.29, 153.58,\
              164.77, 175.86, 186.84, 197.71, 208.48, 219.15,\
              229.72, 240.18, 250.35, 260.78, 270.93, 280.98,\
              290.92, 300.75, 310.49, 320.12, 329.64, 339.06]) + offset
    voltage = 5.0 * pv / 1024
    resistance = 91.5 + voltage / 0.019051
    
    for i in xrange(len(Pt100) - 1):
        if resistance < Pt100[i + 1]:
            return PT100_TABLE_STEP_DEG * ((resistance - Pt100[i]) / (Pt100[i + 1] - Pt100[i]) + i) + MIN_TEMP
    return MAX_TEMP
    

def temp_to_pv(temp, offset = 0.0):
    resistance = (100.0 + offset) * (1 + (3.908e-3 * temp) + (-5.775e-7 * temp * temp))
    voltage = (resistance - 91.5) * 0.019051
    return int((voltage * 1024.0) / 5.0)

class SerialHandler(threading.Thread):
    BAUD_RATE = 115200
    UPDATE_INTERVAL = 500.0
    exit_flag = False

    def __init__(self, set_temp_queue, get_temp_queue, selected_com_port):
        threading.Thread.__init__(self)
        self.set_temp_queue = set_temp_queue
        self.get_temp_queue = get_temp_queue
        self.selected_com_port = selected_com_port

    def open_port(self):
        try:
            self.ser = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=0.4)
        except serial.SerialException as e:
            logger.error('Error opening COM port: %s', e)
        logger.debug('ser %s', self.ser)
        time.sleep(1.6)
        self.ser.readall()
        self.ser.write('C')
        result = self.ser.readline()
        if result.find('OK') is 0:
            return True
        else:
            return False

    def run(self):
        while self.ser.inWaiting() > 0:
            self.ser.read()
        while not self.exit_flag:
            time.sleep(self.UPDATE_INTERVAL / 1000.0)
            msg = ''
            self.ser.write('p')
            #time.sleep(0.01)
            response = self.ser.readline()
            pv = 0
            if response is not '':
                try:
                    pv = int(response)
                except ValueError:
                    pv = 1234

            try:
                self.get_temp_queue.put_nowait(pv)
            except Queue.Full:
                logger.debug('Queue full')
                pass
            if not self.set_temp_queue.empty():
                msg = self.set_temp_queue.get()
                self.set_temp_queue.task_done()
            if msg is not '':
                #logger.info('SerialHandler, Got %s from set_temp_queue', msg)
                self.ser.write(msg)
        #logger.info('SerialHandler stopping')
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
                NumericColumn( name = 'remaining', editable = False, label = 'Time left', width = 70, read_only_cell_color = 0xF4F3EE)],
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
    output_channels = Dict({0:'temp_controller'})
    y_units = Dict({0 : 'temp'})
    enable = Bool(False)
    timer = Instance(Timer)

    table_entries = List(TableEntry)
    current_row = Int(0)
    current_temp = Float
    actual_temp = Float
    set_temp = Float
    current_time = Float
    row_start_time = Float
    running = False

    temperature_table = List(Float)
    selected_com_port = Str
    com_ports_list = List(Str)
    test_com = Button
    get_pv = Button
    set_pv = Button


    set_temp_queue = Instance(Queue.Queue)
    get_temp_queue = Instance(Queue.Queue)


    traits_view = View(HGroup(Item('selected_com_port',  label = 'Com port', \
                                editor = EnumEditor(name='com_ports_list'), \
                                enabled_when='not running'),
                                Item('test_com', enabled_when = 'not running')),
                    Item('enable', label = 'Enable temp program'),
        Group(
            Item( 'table_entries',
                  show_label  = False,
                  editor      = table_editor,
                  enabled_when = 'True'
            ),
            show_border = True,
        ),
        HGroup(Item('actual_temp', style = 'readonly', format_str = '%.1f'), spring, Item('get_pv', label = 'Get temp', enabled_when = 'not enable')),
        HGroup(Item('set_temp', format_str = '%.1f'), Item('set_pv', label = 'Set temp', enabled_when = 'not enable')),
        resizable = True,
        kind      = 'live',
        handler = TemperatureControlHandler
    )

    def _onTimer(self):
        self._poll_queue()

        self.current_time += (self.UPDATE_INTERVAL / 1000)
        index = int(np.floor(self.current_time))
        if index >= len(self.temperature_table):
            return
        if self.temperature_table[index] is not self.current_temp:
            self.current_temp = self.temperature_table[index]
        if self.current_row >= len(self.table_entries):
            return
        time_left = self.table_entries[self.current_row].time + self.row_start_time - self.current_time
        self.table_entries[self.current_row].remaining = int(time_left)
        if self.table_entries[self.current_row].remaining < 1:
            self.current_row += 1
            self.row_changed(time_left)


    def _poll_queue(self):
        while not self.get_temp_queue.empty():
            try:
                self.actual_temp = pv_to_temp(self.get_temp_queue.get(timeout = 0.5))
                self.get_temp_queue.task_done()
            except serial.Empty:
                logger.error('No temp recieved from SerailHandler - Strange')
                pass


    def _table_entries_default(self):
        return [TableEntry(time = 700, start_temp = 50, end_temp = 650, remaining = -1),
                TableEntry(time = 200, start_temp = 650, end_temp = 650, remaining = -1),
                TableEntry(time = 1200, start_temp = 650, end_temp = 200, remaining = -1),
                TableEntry(time = 7300, start_temp = 200, end_temp = 200, remaining = -1),
                TableEntry(time = 1200, start_temp = 200, end_temp = 150, remaining = -1),
                TableEntry(time = 1200, start_temp = 150, end_temp = 150, remaining = -1),
                TableEntry(time = 750, start_temp = 150, end_temp = 650, remaining = -1),
                TableEntry(time = 120, start_temp = 650, end_temp = 50, remaining = -1),
                TableEntry(time = 700, start_temp = 50, end_temp = 650, remaining = -1),
                TableEntry(time = 200, start_temp = 650, end_temp = 650, remaining = -1),
                TableEntry(time = 1200, start_temp = 650, end_temp = 300, remaining = -1),
                TableEntry(time = 7300, start_temp = 300, end_temp = 300, remaining = -1),
                TableEntry(time = 1200, start_temp = 300, end_temp = 150, remaining = -1),
                TableEntry(time = 1200, start_temp = 150, end_temp = 150, remaining = -1),
                TableEntry(time = 750, start_temp = 150, end_temp = 650, remaining = -1),
                TableEntry(time = 120, start_temp = 650, end_temp = 50, remaining = -1),
                TableEntry(time = 700, start_temp = 50, end_temp = 650, remaining = -1),
                TableEntry(time = 200, start_temp = 650, end_temp = 650, remaining = -1),
                TableEntry(time = 1200, start_temp = 650, end_temp = 400, remaining = -1),
                TableEntry(time = 7300, start_temp = 400, end_temp = 400, remaining = -1),
                TableEntry(time = 1200, start_temp = 400, end_temp = 150, remaining = -1),
                TableEntry(time = 1200, start_temp = 150, end_temp = 150, remaining = -1),
                TableEntry(time = 750, start_temp = 150, end_temp = 650, remaining = -1),
                TableEntry(time = 120, start_temp = 650, end_temp = 50, remaining = -1),
                TableEntry(time = 700, start_temp = 50, end_temp = 650, remaining = -1),
                TableEntry(time = 200, start_temp = 650, end_temp = 650, remaining = -1),
                TableEntry(time = 1200, start_temp = 650, end_temp = 500, remaining = -1),
                TableEntry(time = 7300, start_temp = 500, end_temp = 500, remaining = -1),
                TableEntry(time = 1200, start_temp = 500, end_temp = 150, remaining = -1),
                TableEntry(time = 1200, start_temp = 150, end_temp = 150, remaining = -1),
                TableEntry(time = 750, start_temp = 150, end_temp = 650, remaining = -1),
                TableEntry(time = 120, start_temp = 650, end_temp = 50, remaining = -1),]

    def start_stop(self, running):
        if not self.enable:
            return

        if running:
            if self.running:
                return
            #logger.info('Starting')
            self.calculate_temperature_table()
            #self.controller = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=1)
            self.current_time = 0
            self.current_row = 0
            self.row_changed(0)


            self.set_temp_queue = Queue.Queue(2)
            self.get_temp_queue = Queue.Queue(2)
            self.serial_handler = SerialHandler(self.set_temp_queue, self.get_temp_queue,
                self.selected_com_port)
            if not self.serial_handler.open_port():
                self.running = False
                return
            self.serial_handler.start()
            self.current_temp = self.temperature_table[0]
            self.timer = Timer(self.UPDATE_INTERVAL, self._onTimer)

        else:
            if not self.running:
                return
            #logger.info('Stopping')
            #if self.controller is not None:
            #    self.controller.close()
            if self.timer is not None:
                self.timer.Stop()
            self._poll_queue()
            if self.serial_handler is not None:
                self.serial_handler.exit_flag = True
                while self.serial_handler.isAlive():
                    self.serial_handler.join(0.4)
                    logger.debug('Waiting for serial_handler')
                logger.debug('serial_handler stopped')
        self.running = running

    def add_data(self, data):
        pass

    def get_data(self):
        return ({'time': 0}, {'temp': self.actual_temp})

    def calculate_temperature_table(self):
        self.temperature_table = []
        for row in self.table_entries:
            slope = (row.end_temp - row.start_temp) / float(row.time - 1)
            #logger.info('Slope of row %s is %f', row, slope)
            for i in range(row.time):
                self.temperature_table.append(i * slope + row.start_temp)

    def row_changed(self, remainder):
        self.row_start_time = self.current_time + remainder
        if self.current_row >= len(self.table_entries):
            return

    def _current_temp_changed(self, new):
        msg = 's%d' % temp_to_pv(new)
        logger.debug('Send %s to temp controller', msg)
        self.set_temp_queue.put(msg)
        self.set_temp = new


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

    def _get_pv_fired(self):
        if self.selected_com_port is '':
            return
        try:
            ser = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=1)
        except serial.SerialException as e:
            logger.error('Error opening COM port: %s', e)
            return
        response = ser.readall()
        ser.write('p')
        response = ser.readline()
        if response is not '':
            try:
                self.actual_temp = pv_to_temp(int(response))
            except ValueError:
                self.actual_temp = -1
        ser.close()
        
    def _set_pv_fired(self):
        if self.selected_com_port is '':
            return
        try:
            ser = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=1)
        except serial.SerialException as e:
            logger.error('Error opening COM port: %s', e)
            return
        ser.readall()
        msg = 's%d' % temp_to_pv(self.set_temp)
        ser.write(msg)
        ser.close()
     

    def _test_com_fired(self):
        ser = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=1)
#        time.sleep(1)
        ser.readall()
        ser.write('C')
        result = ser.readline()
        logger.info('result %s, ser %s', result, ser)
        if result.find('OK') is 0:
            logger.info('Connection OK!')
        #result = ser.read(30)
        ser.close()

    #def get_pt100_temp(self):
    #    self.controller.write('p')
    #    line = self.controller.readline()
    #    return int(line)


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
