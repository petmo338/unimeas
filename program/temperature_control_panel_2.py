from traits.api import HasTraits, Bool, Int, List, Float, Instance,\
    Str, Button, Dict, File, Array, on_trait_change
from traitsui.api import Item, View, Group, HGroup, Handler, \
    TableEditor, EnumEditor, spring, VGroup, ButtonEditor
from traitsui.table_column import NumericColumn
import logging
import serial
from time import sleep, time, strftime
from pyface.timer.api import Timer
import threading
import Queue
import numpy as np
from math import sqrt
import struct
from generic_popup_message import GenericPopupMessage
import csv
logger = logging.getLogger(__name__)


PID_configurations = {'Normal TO-8': {'P': 5.821729083089657, 'I': 1.626933965977756, 'D': 1.332938348953647,
                                      'N': 1.448274562118016, 'pwm_table_index': 0},
                      'Sensic M18 ceramic': {'P': 9.56699386091245, 'I': 6.07629935945335, 'D': 1.98583413086793,
                                             'N': 37.8230336021021, 'pwm_table_index': 1},
                      'L-A Cap': {'P': 8.56699386091245, 'I': 6.07629935945335, 'D': 1.98583413086793,
                                  'N': 37.8230336021021, 'pwm_table_index': 0},
                      'Small mass': {'P': 2.56699386091245, 'I': 6.07629935945335, 'D': 1.98583413086793,
                                     'N': 37.8230336021021, 'pwm_table_index': 0}}
BAUD_RATE = 115200
POLL_INTERVAL = 200.0


def open_port(port, timeout):
    com = serial.Serial()
    com.port = port
    com.baudrate = BAUD_RATE
    com.timeout = timeout
    if float(serial.VERSION) > 3.0:
        com.dtr = False
    else:
        com.setDTR(False)
    com.open()
    return com


def temp_to_resistance(temp, resistance_at_rt=109.7):
    return (100.0 * (resistance_at_rt/109.7)) * (1 + (3.908e-3 * temp) + (-5.775e-7 * temp * temp))


def resistance_to_temp(resistance, resistance_at_rt=109.7):
    r0 = (100.0 * (resistance_at_rt/109.7))
    a = 3.908e-3
    b = -5.775e-7
    if resistance > 500:
        return 999
    return (-r0*a + sqrt(r0*r0*a*a-4*r0*b*(r0-resistance)))/(2*r0*b)


class SerialHandler(threading.Thread):
    BAUD_RATE = 115200
    response_unpack_format = '<2f3B7f'
    exit_flag = False
    is_connected = False
    ser = Instance(serial.Serial)

    def __init__(self, set_parameters_queue, get_parameters_queue, selected_com_port):
        threading.Thread.__init__(self)
        self.set_parameters_queue = set_parameters_queue
        self.get_parameters_queue = get_parameters_queue
        self.selected_com_port = selected_com_port

    def open_port(self):
        try:
            self.ser = open_port(self.selected_com_port, 0.1)
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
            response = self.ser.read(struct.calcsize(self.response_unpack_format))
            if len(response) == struct.calcsize('<2f3B7f'):
                values = struct.unpack('<2f3B7f', response)
                try:
                    self.get_parameters_queue.put_nowait(values)
                except Queue.Full:
                    logger.debug('Queue full')
                    pass
            if not self.set_parameters_queue.empty():
                msg = self.set_parameters_queue.get()
                self.set_parameters_queue.task_done()
                if msg is not '':
                    self.ser.write(msg)
        self.ser.close()


class TableEntry(HasTraits):

    time = Int
    start_temp = Int
    end_temp = Int
    ramp = Float
    remaining = Int

    def _time_changed(self, new):
        if new < 1:
            new = 1
        self.remaining = new
        self.trait_set(trait_change_notify=False, ramp=int((self.end_temp - self.start_temp) / (new / 60.0)))

    def _ramp_changed(self, new):
        if new != 0:
            self.trait_set(trait_change_notify=False, time=int(60.0*(self.end_temp - self.start_temp) / new))
            self.remaining = self.time

    @on_trait_change('start_temp', 'end_temp')
    def _update_ramp(self, obj, old, new):
        self.trait_set(trait_change_notify=False, ramp=int((self.end_temp - self.start_temp) / (self.time / 60.0)))


table_editor = TableEditor(
    columns=[
        NumericColumn(name='time', label='Seconds', horizontal_alignment='right'),
        NumericColumn(name='start_temp', label='Start temp'),
        NumericColumn(name='end_temp', label='End temp'),
        NumericColumn(name='ramp', label=u'Ramp \u00b0/min'),
        NumericColumn(name='remaining', editable=False, label='Time left', width=60,
                      read_only_cell_color=0xF4F3EE)],
    deletable=True,
    sort_model=False,
    auto_size=True,
    orientation='vertical',
    show_toolbar=False,
    sortable=False,
    row_factory=TableEntry
)


class TemperatureControlHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """

        if info.object.serial_handler is not None:
            info.object.serial_handler.exit_flag = True
            # while self.serial_handler.isAlive():
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
    pane_id = Str('sensorscience.unimeas.temperature_control_pane')
    output_channels = Dict({0: 'temp_controller'})
    y_units = Dict({0: 'temp'})
    enable = Bool(False)
    loop_sequence = Bool(True)
    poll_timer = Instance(Timer)
    timing_timer = Instance(Timer)
    table_entries = List(TableEntry)
    current_row = Int(0)
    current_temp = Float
    actual_temp = Float
    process_value = Float
    adjusted_pv = Float
    PID_out = Float
    pwm_value = Int
    max31865_ctrl = Int
    max31865_error = Int
    setpoint = Float
    supply_voltage = Float
    rt_resistance = Float
    set_temp = Float
    current_time = Float
    row_start_time = Float
    start_time = Float
    running = False
    connected = Bool(False)
    save_detailed_log = Bool(False)

    pid_P = Float(0)
    pid_I = Float(0)
    pid_D = Float(0)
    pid_N = Float(0)
    pwm_table_index = Int(0)
    use_direct_pwm = Bool(False)
    pwm_set_direct = Int(0)

    temp_setpoint = Float
    resistance_setpoint = Float
    supply_voltage_setpoint = Float(15.0)
    rt_resistance_setpoint = Float(109.71)

    temperature_table = Array
    selected_com_port = Str
    selected_pid_configuration = Str
    available_pid_configurations = List(['Normal TO-8', 'M18 ceramic', 'L-A Cap'])
    com_ports_list = List(Str)
    connect = Button
    connect_button_string = Str('Connect')
    update_PID_values = Int(0)
    set_parameters = Button
    update_pid = Button
    save = Button
    load = Button
    filename = File

    set_parameters_queue = Instance(Queue.Queue)
    get_parameters_queue = Instance(Queue.Queue)
    serial_handler = Instance(SerialHandler)

    traits_view = View(
        HGroup(Item('selected_com_port',  label='Com port',
                    editor=EnumEditor(name='com_ports_list'),
                    enabled_when='not running'),
               Item('connect', editor=ButtonEditor(label_value='connect_button_string'),
                    show_label=False,  enabled_when='selected_com_port != ""')),
        Item('enable', label='Enable temp program', enabled_when='connected'),
        Item('loop_sequence', label='Loop temperature sequence'),
        Group(Item('table_entries', show_label=False, editor=table_editor,
                   enabled_when='True'
                   ),
              HGroup(Item('filename'), spring, Item('save', show_label=False),
                     Item('load', show_label=False)),
              show_border=True,
              ),
        Group(
            HGroup(
                VGroup(Item('actual_temp', style='readonly', format_str='%.2f'),
                       Item('process_value', style='readonly', format_str='%.2f'),
                       Item('adjusted_pv', style='readonly', format_str='%.2f'),
                       Item('setpoint', style='readonly', format_str='%.2f')),
                spring,
                VGroup(Item('pwm_value', style='readonly', format_str='%d'),
                       Item('max31865_ctrl', style='readonly', format_str='%#04x'),
                       Item('max31865_error', style='readonly', format_str='%#04x')),
                spring,
                VGroup(Item('PID_out', style='readonly', format_str='%.2f'),
                       Item('supply_voltage', style='readonly', format_str='%.2f'),
                       Item('rt_resistance', style='readonly', format_str='%.2f'))),
            label='Diagnostic parameters', show_border=True,
        ),
        HGroup(
            Group(
                VGroup(Item('temp_setpoint', format_str='%.1f')),
                VGroup(Item('resistance_setpoint', format_str='%.1f')),
                VGroup(Item('supply_voltage_setpoint', format_str='%.1f')),
                VGroup(Item('rt_resistance_setpoint', format_str='%.1f')),
                Item('set_parameters', enabled_when='connected'),
                label='Adjustable parameters', show_border=True,
                ),
            Group(
                Item('selected_pid_configuration', label='PID adaption',
                     editor=EnumEditor(name='available_pid_configurations'),
                     enabled_when='True'),
                VGroup(Item('pid_P', label='PID P', format_str='%.7f')),
                VGroup(Item('pid_I', label='PID I', format_str='%.7f')),
                VGroup(Item('pid_D', label='PID D',  format_str='%.7f')),
                VGroup(Item('pid_N', label='PID Nd',  format_str='%.7f')),
                VGroup(Item('pwm_table_index', label='tbl_idx')),
                HGroup(Item('use_direct_pwm'), Item('pwm_set_direct', show_label=False)),
                Item('update_pid', enabled_when='connected'),
                Item('save_detailed_log', enabled_when='connected'),
                label='PID parameters - Don\'t touch', show_border=True,
                ),
        ),
        resizable=True, kind='live', handler=TemperatureControlHandler
    )

    def _set_parameters_queue_default(self):
        return Queue.Queue(2)

    def _get_parameters_queue_default(self):
        return Queue.Queue(2)

    def _temp_setpoint_changed(self, new):
        self.resistance_setpoint = temp_to_resistance(new, float(self.rt_resistance_setpoint))

    def _connected_changed(self, new):
        if new is True:
            self.connect_button_string = 'Disconnect'
            self.update_PID_values = 3
        else:
            self.connect_button_string = 'Connect'

    def _save_detailed_log_changed(self, new):
        if new:
            self.fh = open('templog_' + strftime("%y%m%d_%H%M%S") + '.csv', 'w')
            self.csv_writer = csv.writer(self.fh, quoting=csv.QUOTE_NONNUMERIC)
            self.csv_writer.writerow(['pv', 'pid_out', 'pwm', 'max31ctrl', 'max31err', 'sp', 'sv', 'RT_ref', 'pid_p',
                                      'pid_i', 'pid_d', 'pid_n', 'time'])
            self.log_start_time = time()
        else:
            self.fh.close()

    def _rt_resistance_setpoint_changed(self, new):
        self.resistance_setpoint = temp_to_resistance(self.temp_setpoint, new)

    def _selected_pid_configuration_changed(self, new):
        self.pid_P = PID_configurations[new]['P']
        self.pid_I = PID_configurations[new]['I']
        self.pid_D = PID_configurations[new]['D']
        self.pid_N = PID_configurations[new]['N']
        self.pwm_table_index = PID_configurations[new]['pwm_table_index']

    def _available_pid_configurations_default(self):
        return PID_configurations.keys()

    def _on_timer(self):
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
            except Queue.Empty:
                logger.error('No temp received from SerialHandler - Strange')
                pass
            self.get_parameters_queue.task_done()
            self.actual_temp = resistance_to_temp(values[0], values[7])
            self.process_value = values[0]
            self.adjusted_pv = values[0]*(109.7/values[7])
            self.PID_out = values[1]
            self.pwm_value = values[2]
            self.max31856_ctrl = values[3]
            self.max31856_error = values[4]
            self.setpoint = values[5]
            self.supply_voltage = values[6]
            self.rt_resistance = values[7]
            if self.update_PID_values > 0:
                self.update_PID_values -= 1
                self.pid_P = values[8]
                self.pid_I = values[9]
                self.pid_D = values[10]
                self.pid_N = values[11]
            if self.save_detailed_log:
                self.csv_writer.writerow(values + (time() - self.log_start_time,))

    def _table_entries_default(self):
        return [TableEntry(time=15, start_temp=150, end_temp=150, remaining=-1),
                TableEntry(time=15, start_temp=350, end_temp=350, remaining=-1),
                TableEntry(time=15, start_temp=250, end_temp=250, remaining=-1)]

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
            self.timing_timer = Timer(self.TIMING_UPDATE_INTERVAL, self._on_timer)

        else:
            if not self.running:
                return
            if self.timing_timer is not None:
                self.timing_timer.Stop()
        self.running = running

    def add_data(self, data):
        pass

    def get_data(self):
        return {'time': 0}, {'temp': self.actual_temp}

    def calculate_temperature_table(self):
        self.temperature_table = np.array([])
        for row in self.table_entries:
            self.temperature_table = np.hstack((self.temperature_table,
                                                np.linspace(row.start_temp, row.end_temp, row.time)))

    def row_changed(self, remainder):
        self.row_start_time = self.current_time + remainder
        if self.current_row >= len(self.table_entries):
            if self.loop_sequence:
                self.start_time = time()
                for row in self.table_entries:
                    row.remaining = row.time
                self.current_time = 0
                self.current_row = 0
                self.row_changed(time() - self.start_time)

    def _current_temp_changed(self, new):
        self.temp_setpoint = new
        if self.use_direct_pwm:
            self.pwm_set_direct = int(new)
            self._update_pid_fired()
            return
        self._set_parameters_fired()

    def _com_ports_list_default(self):
        import serial.tools.list_ports as lp
        ports = []
        for p in lp.grep('Arduino'):
            ports.append(p[0])
        return ports

    def _set_parameters_fired(self):
        self.set_parameters_queue.put_nowait(struct.pack('<c5B5f', 's', 0, 0, 0, 0, self.pwm_table_index,
                                                         self.resistance_setpoint, self.supply_voltage_setpoint,
                                                         self.rt_resistance_setpoint, 0, 0))

    def _update_pid_fired(self):
        self.set_parameters_queue.put_nowait(struct.pack('<c4f', 'p', self.pid_P, self.pid_I, self.pid_D, self.pid_N))
        self.set_parameters_queue.put_nowait(struct.pack('<c5B5f', 's', 0, int(self.use_direct_pwm), 0,
                                                         self.pwm_set_direct, self.pwm_table_index,
                                                         self.resistance_setpoint, self.supply_voltage_setpoint,
                                                         self.rt_resistance_setpoint, 0, 0))
        self.update_PID_values = 3

    def _connect_fired(self):
        if self.serial_handler is None:
            self.serial_handler = SerialHandler(self.set_parameters_queue, self.get_parameters_queue,
                                                self.selected_com_port)
            if not self.serial_handler.open_port():
                return
            self.poll_timer = Timer(POLL_INTERVAL / 2, self._poll_queue)
            self.serial_handler.start()
            self.connected = True
        else:
            self.start_stop(False)
            self.serial_handler.exit_flag = True
            self.serial_handler.join()
            self.serial_handler = None
            if self.poll_timer is not None:
                self.poll_timer.stop()
            self.connected = False

    def _save_fired(self):
        if self.filename is '':
            GenericPopupMessage(message='No filename given').edit_traits()
            return
        filehandle = open(self.filename, "w", 1)
        fieldnames = self.table_entries[0].trait_get().keys()
        csv_writer = csv.DictWriter(filehandle, fieldnames=fieldnames, delimiter=',',
                                    quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        csv_writer.writeheader()
        for row in self.table_entries:
            csv_writer.writerow(row.trait_get())
        filehandle.close()

    def _load_fired(self):
        if self.filename is '':
            GenericPopupMessage(message='No filename given').edit_traits()
            return
        filehandle = open(self.filename, "r", 1)
        reader = csv.DictReader(filehandle)
        self.table_entries = []
        for row in reader:
            self.table_entries.append(TableEntry(time=int(row['time']),
                                                 start_temp=int(row['start_temp']),
                                                 end_temp=int(row['end_temp']),
                                                 remaining=int(row['time'])))
        filehandle.close()

    def _set_temp_table_for_calibration(self):
        pwms = [int(a) for a in np.hstack((np.linspace(0, 255, 256), np.linspace(255, 0, 256)))]
        self.table_entries = [TableEntry(time=60, start_temp=t, end_temp=t, remaining=-1) for t in pwms]
        self.temp_setpoint = self.table_entries[0].start_temp - 1  # Make sure they are unequal


if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.handlers = []
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    g = TemperatureControlPanel()
    g.configure_traits(filename='test2.test', id='unique_stuff.apa')