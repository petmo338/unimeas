from traits.api import HasTraits, Bool, Int, List, Float, Instance,\
    Str, Button, Dict, File
from traitsui.api import Item, View, Group, HGroup, Handler, \
    TableEditor, EnumEditor, spring, FileEditor
from traitsui.table_column import NumericColumn
import logging
import serial
import os
from time import sleep, time
from serial.tools import list_ports
from pyface.timer.api import Timer
import numpy as np
import threading
import queue
import numpy as np
from math import sqrt
import struct
#from . generic_popup_message import GenericPopupMessage
import csv
logger = logging.getLogger(__name__)
BAUD_RATE = 115200
UPDATE_INTERVAL = 200.0
def open_port(port, timeout):
    com = serial.Serial()
    com.port = port
    com.baudrate = BAUD_RATE
    com.timeout = timeout
    com.setDTR(False)
    com.open()
    return com
    

def temp_to_resistance(temp, resistance_at_RT = 109.7):
    return (100.0 * (resistance_at_RT/109.7)) * (1 + (3.908e-3 * temp) + (-5.775e-7 * temp * temp))

def resistance_to_temp(resistance, resistance_at_RT = 109.7):
    R0 = (100.0 * (resistance_at_RT/109.7))
    a = 3.908e-3
    b = -5.775e-7
    return (-R0*a + sqrt(R0*R0*a*a-4*R0*b*(R0-resistance)))/(2*R0*b)


class SerialHandler(threading.Thread):
    BAUD_RATE = 115200
    exit_flag = False

    def __init__(self, set_parameters_queue, get_parameters_queue, selected_com_port):
        threading.Thread.__init__(self)
        self.set_parameters_queue = set_temp_queue
        self.get_parameters_queue = get_temp_queue
        self.selected_com_port = selected_com_port

    def open_port(self):
        try:
            self.ser = open_port(self.selected_com_port, 0.1)
#            self.ser = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=0.4)
        except serial.SerialException as e:
            logger.error('Error opening COM port: %s', e)
            return False

        self.ser.readall()
        self.ser.write('C')
        result = self.ser.readline()
        if result.find('CC') is 0:
            return True
        else:
            return False

    def run(self):
        while not self.exit_flag:
            sleep(UPDATE_INTERVAL / 1000.0)
            self.ser.write('a')
            #time.sleep(0.01)
            response = self.ser.read(25)
            values = struct.unpack('<2f3b3f', response)

            try:
                self.get_parameters_queue.put_nowait(values)
            except queue.Full:
                logger.debug('Queue full')
                pass
            if not self.set_parameters_queue.empty():
                msg = self.set_parameters_queue.get()
                self.set_parameters_queue.task_done()
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
    start_time = Float
    running = False

    temperature_table = List(Float)
    selected_com_port = Str
    com_ports_list = List(Str)
    connect = Button
    get_pv = Button
    set_pv = Button

    save = Button
    load = Button
    filename = File

    set_temp_queue = Instance(queue.Queue)
    get_temp_queue = Instance(queue.Queue)


    traits_view = View(HGroup(Item('selected_com_port',  label = 'Com port', \
                                editor = EnumEditor(name='com_ports_list'), \
                                enabled_when='not running'),
                                Item('connect', enabled_when = 'selected_com_port != ""')),
                    Item('enable', label = 'Enable temp program'),
        Group(
            Item( 'table_entries',
                  show_label  = False,
                  editor      = table_editor,
                  enabled_when = 'True'
            ),
            HGroup(Item('filename'), spring, Item('save', show_label = False),
            Item('load', show_label = False)),
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

        #self.current_time += (self.UPDATE_INTERVAL / 1000)
        self.current_time = time() - self.start_time
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
        while not self.get_parameters_queue.empty():
            try:
                values = self.get_parameters_queue.get_nowait()
            except serial.Empty:
                logger.error('No temp recieved from SerialHandler - Strange')
                pass
            self.get_temp_queue.task_done()

            self.actual_temp = resistance_to_temp(values[0])
 

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

            self.start_time = time()
            self.calculate_temperature_table()
            for row in self.table_entries:
                row.remaining = row.time
            #self.controller = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=1)
            self.current_time = 0
            self.current_row = 0
            self.row_changed(0)
            self.set_parameters_queue = queue.Queue(2)
            self.get_parameters_queue = queue.Queue(2)
            self.serial_handler = SerialHandler(self.set_parameters_queue, self.get_parameters_queue,
                self.selected_com_port)
            if not self.serial_handler.open_port():
                self.running = False
                return
            self.serial_handler.start()
            self.current_temp = self.temperature_table[0]
            self.timer = Timer(UPDATE_INTERVAL, self._onTimer)

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
                    self.serial_handler.join()
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
        self.set_temp_queue.put(msg)
        self.set_temp = new


#    def _com_ports_list_default(self):
#        return ['/dev/ttyACM0']


    def _com_ports_list_default(self):
        l = []
        if os.name == 'nt':
            # windows
            for i in range(1,8):
                l.append('COM' + str(i + 1))
                #try:
                #    s = serial.Serial(i)
                #    s.close()
                #    l.append('COM' + str(i + 1))
                #except serial.SerialException:
                #    pass
        else:
            # unix
            for port in list_ports.comports():
                l.append(port[0])
        return l

    def _get_pv_fired(self):
        if self.selected_com_port is '':
            return
        try:

            ser = open_port(self.selected_com_port, 0.2)
#            ser = serial.Serial(self.selected_com_port, self.BAUD_RATE, timeout=1)
        except serial.SerialException as e:
            logger.error('Error opening COM port: %s', e)
            return
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
            ser = open_port(self.selected_com_port, 0.2)
        except serial.SerialException as e:
            logger.error('Error opening COM port: %s', e)
            return
        ser.readall()
        msg = 's%d' % temp_to_pv(self.set_temp)
        ser.write(msg)
        ser.close()
     

    def _test_com_fired(self):
        ser = open_port(self.selected_com_port, 0.5)
        ser.readall()
        ser.write('C')
        result = ser.readline()
#        logger.info('result %s, ser %s', result, ser)
        if result.find('OK') is 0:
            logger.info('Connection OK!')
            GenericPopupMessage(message='Temperature controller found').edit_traits()
            
        #result = ser.read(30)
        ser.close()

    def _save_fired(self):
        if self.filename is '':
            GenericPopupMessage(message='No filename given').edit_traits()
            return
        filehandle = open(self.filename, "w", 1)
        fieldnames = self.table_entries[0].trait_get().keys()
        csv_writer = csv.DictWriter(filehandle, fieldnames=fieldnames, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        csv_writer.writeheader()
#        csv_writer.writerow(self.table_entries[0].trait_get().keys())
        for row in self.table_entries:
            csv_writer.writerow(row.trait_get())
        filehandle.close()           

    def _load_fired(self):
        if self.filename is '':
            GenericPopupMessage(message='No filename given').edit_traits()
            return
        filehandle = open(self.filename, "r", 1)
        reader = csv.DictReader(filehandle)
        i = 0
        self.table_entries = []
        for row in reader:
            self.table_entries.append(TableEntry(time = int(row['time']),
                start_temp = int(row['start_temp']), end_temp = int(row['end_temp']),
                remaining = int(row['time'])))
        #    for k,v in row.iteritems():
        #        setattr(self.table_entries[i], k, int(v))
        #    i += 1
        #self.table_entries = self.table_entries[:i]
        filehandle.close()           


if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.handlers = []
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    g=TemperatureControlPanel()
    g.configure_traits(filename='test2.test', id='unique_stuff.apa')
    #g=TestSerial()
    #g.configure_traits()
