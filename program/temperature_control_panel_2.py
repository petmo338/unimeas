from traits.api import HasTraits, Bool, Int, List, Float, Instance,\
    Str, Button, Dict, File, Array, on_trait_change
from traitsui.api import Item, View, Group, HGroup, Handler, \
    TableEditor, EnumEditor, spring, FileEditor, VGroup
from traitsui.table_column import NumericColumn
import logging
import serial
import os
from time import sleep, time
from serial.tools import list_ports
from pyface.timer.api import Timer
import threading
import Queue
import numpy as np
from math import sqrt
import struct
from generic_popup_message import GenericPopupMessage
import csv
logger = logging.getLogger(__name__)
BAUD_RATE = 115200
POLL_INTERVAL = 200.0
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
    is_connected = False

    def __init__(self, set_parameters_queue, get_parameters_queue, selected_com_port):
        threading.Thread.__init__(self)
        self.set_parameters_queue = set_parameters_queue
        self.get_parameters_queue = get_parameters_queue
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
        result = self.ser.readall()
        if result.find('CC') > -1:
            self.is_connected = True
            return True
        else:
            self.ser.close()
            GenericPopupMessage(message='No temperature controller found!').edit_traits()
            return False

    def run(self):
        while not self.exit_flag:
            sleep(POLL_INTERVAL / 1000.0)
            self.ser.write('a')
            #time.sleep(0.01)
            response = self.ser.read(23)
            values = struct.unpack('<2f3B3f', response)
            try:
                self.get_parameters_queue.put_nowait(values)
            except Queue.Full:
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
    ramp = Float
    remaining = Int
    
    def _time_changed(self, new):
        #logger.info('_time_changed')
        if new < 1:
            new = 1
        self.remaining = new
        self.trait_set(trait_change_notify=False, ramp=int((self.end_temp - self.start_temp) / (new/60.0)))
        #self.ramp = int((self.end_temp - self.start_temp) / (new/60))

    def _ramp_changed(self, new):
        if new != 0:
            self.trait_set(trait_change_notify=False, time = int(60.0*(self.end_temp - self.start_temp) / (new)))
            self.remaining = self.time
        #else:
        
    @on_trait_change('start_temp', 'end_temp')
    def _update_ramp(self, obj, old, new):
        self.trait_set(trait_change_notify=False, ramp=int((self.end_temp - self.start_temp) / (self.time/60.0)))     


table_editor = TableEditor(
    columns = [ NumericColumn( name = 'time', label = 'Seconds', horizontal_alignment = 'right'),
                NumericColumn( name = 'start_temp', label = 'Start temp'),
                NumericColumn( name = 'end_temp', label = 'End temp'),
                NumericColumn( name = 'ramp', label = u'Ramp \u00b0/min'),
                NumericColumn( name = 'remaining', editable = False, label = 'Time left', width = 60, read_only_cell_color = 0xF4F3EE)],
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
        #info.object.start_stop(False)
        
        if info.object.serial_handler != None:
            info.object.serial_handler.exit_flag = True
            #while self.serial_handler.isAlive():
            #    self.serial_handler.join()
        if info.object.timing_timer is not None:
            info.object.timing_timer.Stop()

        while not info.object.set_parameters_queue.empty():
            info.object.set_parameters_queue.get()
            info.object.set_parameters_queue.task_done()           
        info.object.set_parameters_queue.join()
        while not info.object.get_parameters_queue.empty():
            info.object.get_parameters_queue.get()
            info.object.get_parameters_queue.task_done()
        info.object.get_parameters_queue.join()        
        

class TemperatureControlPanel(HasTraits):
    TIMING_UPDATE_INTERVAL = 500.0

    pane_name = Str('Temperature control ')
    pane_id = Str('sensorscience.unimeas.temperatur_control_pane')
    output_channels = Dict({0:'temp_controller'})
    y_units = Dict({0 : 'temp'})
    enable = Bool(False)
    loop_sequence = Bool(True)
    poll_timer = Instance(Timer)
    timing_timer = Instance(Timer)
    table_entries = List(TableEntry)
    current_row = Int(0)
    current_temp = Float
    actual_temp = Float
    process_value = Float
    PID_out = Float
    pwm_value = Int
    max31865_ctrl = Int
    max31865_error = Int
    setpoint = Float
    supply_voltage = Float
    RT_resistance = Float
    set_temp = Float
    current_time = Float
    row_start_time = Float
    start_time = Float
    running = False
    connected = Bool(False)
    
    pid_P = Float(0)
    pid_I = Float(0)
    pid_D = Float(0)
    
    
    temp_setpoint = Float
    resistance_setpoint = Float
    supply_voltage_setpoint = Float(15.0)
    RT_resistance_setpoint = Float(109.71)
    

    temperature_table = Array
    selected_com_port = Str
    com_ports_list = List(Str)
    connect = Button
    set_parameters = Button

    save = Button
    load = Button
    filename = File

    set_parameters_queue = Instance(Queue.Queue)
    get_parameters_queue = Instance(Queue.Queue)
    serial_handler = Instance(SerialHandler)


    traits_view = View(
        HGroup(Item('selected_com_port',  label = 'Com port', \
                                editor = EnumEditor(name='com_ports_list'), \
                                enabled_when='not running'),
                                Item('connect', show_label = False,  enabled_when = 'selected_com_port != ""')),
        Item('enable', label = 'Enable temp program', enabled_when = 'connected'),
        Item('loop_sequence', label = 'Loop temperature sequence'),
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

        Group(
            HGroup(
                VGroup(Item('actual_temp', style = 'readonly', format_str = '%.2f'),Item('process_value', style = 'readonly', format_str = '%.2f'),  Item('setpoint', style = 'readonly', format_str = '%.2f')),spring,
                VGroup(Item('pwm_value', style = 'readonly', format_str = '%d'), Item('max31865_ctrl', style = 'readonly', format_str = '%#04x'),  Item('max31865_error', style = 'readonly', format_str = '%#04x')),spring,
                VGroup(Item('PID_out', style = 'readonly', format_str = '%.2f'),  Item('supply_voltage', style = 'readonly', format_str = '%.2f'),  Item('RT_resistance', style = 'readonly', format_str = '%.2f'))),
            label = 'Diagnostic parameters', show_border = True,
       ),
        
       HGroup(
            Group(
                VGroup(Item('temp_setpoint', format_str = '%.1f')), 
                VGroup(Item('resistance_setpoint', format_str = '%.1f')), 
                VGroup(Item('supply_voltage_setpoint', format_str = '%.1f')), 
                VGroup(Item('RT_resistance_setpoint', format_str = '%.1f')), 
                Item('set_parameters', enabled_when = 'connected'),
                label = 'Adjustable parameters', show_border = True,
                ),
            Group(
                VGroup(Item('pid_P', format_str = '%.1f')), 
                VGroup(Item('pid_I', format_str = '%.1f')), 
                VGroup(Item('pid_D', format_str = '%.1f')), 
                label = 'PID parameters - Don\'t touch', show_border = True,
                ),
        ),
        resizable = True,
        kind      = 'live',
        handler = TemperatureControlHandler
    )
    
    def _set_parameters_queue_default(self):
        return Queue.Queue(2)
        
    def _get_parameters_queue_default(self):
        return Queue.Queue(2)

    def _temp_setpoint_changed(self, new):
        self.resistance_setpoint = temp_to_resistance(new, self.RT_resistance_setpoint)

    def _RT_resistance_setpoint_changed(self, new):
        self.resistance_setpoint = temp_to_resistance(self.temp_setpoint, new)
        

    def _onTimer(self):
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
            self.get_parameters_queue.task_done()
            self.actual_temp = resistance_to_temp(values[0], values[7])
            self.process_value = values[0]
            self.PID_out = values[1]
            self.pwm_value = values[2]
            self.max31856_ctrl = values[3]
            self.max31856_error = values[4]
            self.setpoint = values[5]
            self.supply_voltage = values[6]
            self.RT_resistance = values[7]
 

    def _table_entries_default(self):
        return [TableEntry(time = 15, start_temp = 150, end_temp = 150, remaining = -1),
                TableEntry(time = 15, start_temp = 350, end_temp = 350, remaining = -1),
                TableEntry(time = 15, start_temp = 250, end_temp = 250, remaining = -1)]
        #return [TableEntry(time = 700, start_temp = 50, end_temp = 650, remaining = -1),
        #        TableEntry(time = 200, start_temp = 650, end_temp = 650, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 650, end_temp = 200, remaining = -1),
        #        TableEntry(time = 7300, start_temp = 200, end_temp = 200, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 200, end_temp = 150, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 150, end_temp = 150, remaining = -1),
        #        TableEntry(time = 750, start_temp = 150, end_temp = 650, remaining = -1),
        #        TableEntry(time = 120, start_temp = 650, end_temp = 50, remaining = -1),
        #        TableEntry(time = 700, start_temp = 50, end_temp = 650, remaining = -1),
        #        TableEntry(time = 200, start_temp = 650, end_temp = 650, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 650, end_temp = 300, remaining = -1),
        #        TableEntry(time = 7300, start_temp = 300, end_temp = 300, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 300, end_temp = 150, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 150, end_temp = 150, remaining = -1),
        #        TableEntry(time = 750, start_temp = 150, end_temp = 650, remaining = -1),
        #        TableEntry(time = 120, start_temp = 650, end_temp = 50, remaining = -1),
        #        TableEntry(time = 700, start_temp = 50, end_temp = 650, remaining = -1),
        #        TableEntry(time = 200, start_temp = 650, end_temp = 650, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 650, end_temp = 400, remaining = -1),
        #        TableEntry(time = 7300, start_temp = 400, end_temp = 400, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 400, end_temp = 150, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 150, end_temp = 150, remaining = -1),
        #        TableEntry(time = 750, start_temp = 150, end_temp = 650, remaining = -1),
        #        TableEntry(time = 120, start_temp = 650, end_temp = 50, remaining = -1),
        #        TableEntry(time = 700, start_temp = 50, end_temp = 650, remaining = -1),
        #        TableEntry(time = 200, start_temp = 650, end_temp = 650, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 650, end_temp = 500, remaining = -1),
        #        TableEntry(time = 7300, start_temp = 500, end_temp = 500, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 500, end_temp = 150, remaining = -1),
        #        TableEntry(time = 1200, start_temp = 150, end_temp = 150, remaining = -1),
        #        TableEntry(time = 750, start_temp = 150, end_temp = 650, remaining = -1),
        #        TableEntry(time = 120, start_temp = 650, end_temp = 50, remaining = -1),]

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
            self.current_time = 0
            self.current_row = 0
            self.row_changed(time() - self.start_time)
            self.current_temp = self.temperature_table[0]
            self.timing_timer = Timer(self.TIMING_UPDATE_INTERVAL, self._onTimer)

        else:
            if not self.running:
                return
            if self.timing_timer is not None:
                self.timing_timer.Stop()
        self.running = running

    def add_data(self, data):
        pass

    def get_data(self):
        return ({'time': 0}, {'temp': self.actual_temp})

    def calculate_temperature_table(self):
        self.temperature_table = np.array([])
        for row in self.table_entries:
            self.temperature_table = np.hstack((self.temperature_table,
                np.linspace(row.start_temp, row.end_temp, row.time)))

    def row_changed(self, remainder):
        self.row_start_time = self.current_time + remainder
        if self.current_row >= len(self.table_entries):
            if self.loop_sequence == True:
                self.start_time = time()
                for row in self.table_entries:
                    row.remaining = row.time
                self.current_time = 0
                self.current_row = 0
                self.row_changed(time() - self.start_time)

    def _current_temp_changed(self, new):
        self.temp_setpoint = new
        self._set_parameters_fired()

#    def _com_ports_list_default(self):
#        return ['/dev/ttyACM0']


    def _com_ports_list_default(self):
        l = []
        if os.name == 'nt':
            # windows
            for i in range(1,12):
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
        
    def _set_parameters_fired(self):
        self.set_parameters_queue.put_nowait(struct.pack('<c4b5f', 's', 0, 0, 0, 0, self.resistance_setpoint, self.supply_voltage_setpoint, self.RT_resistance_setpoint, 0, 0))

     
    def _connect_fired(self):
        if self.serial_handler is None:
            self.serial_handler = SerialHandler(self.set_parameters_queue, self.get_parameters_queue,
                    self.selected_com_port)
            if self.serial_handler.open_port() == False:
                return
            self.poll_timer = Timer(POLL_INTERVAL/2, self._poll_queue)
            self.serial_handler.start()
            self.connected = True
        else:
            self.start_stop(False)
            self.serial_handler.exit_flag = True
            self.serial_handler.join()
            self.serial_handler = None
            if self.poll_timer != None:
                self.poll_timer.stop()

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