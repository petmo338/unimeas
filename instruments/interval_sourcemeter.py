from i_instrument import IInstrument
from enthought.traits.api import HasTraits, Instance, Float, Dict, \
    List, implements, Unicode, Str, Int, Event, Bool, Enum, Button
from enthought.traits.ui.api import View, Item, Group, ButtonEditor, Handler, EnumEditor, BooleanEditor
from pyface.timer.api import Timer
from pyvisa import visa
from time import sleep
import logging

logger = logging.getLogger(__name__)

DEFAULT_START_VOLTAGE = 0
DEFAULT_STOP_VOLTAGE = 5
DEFAULT_STEP_VOLTAGE = 0.01

class ViewHandler(Handler):
    def closed(self, info, is_ok):
        if info.object.timer is not None:
            info.object.timer.Stop()

class SourceMeter(HasTraits):

    implements(IInstrument)

    name = Unicode('SourceMeter I/V')

    x_units = Dict({0: 'Voltage'})
    y_units = Dict({0: 'Current'})
    acquired_data = List(Dict)
    start_stop = Event
    running = Bool
    output_channels = Dict({0: 'smua'})
    enabled_channels = List(Bool)
    timer = Instance(Timer)
    timer_dormant = Bool(False)
    update_interval = Float(0.2)

    start_voltage = Float
    step_voltage = Float
    stop_voltage = Float
    current_limit = Float(10.0)

    current_range = Enum('3A', '1A','100mA', '10mA', u'100\u00B5', u'10\u00B5A', u'1\u00B5A', '100nA')
    current_voltage= Float
    current_current = Float
    current_limit_exceeded = Bool(False)
    reading_overflow = Bool(False)

    sample_nr = Int(0)
    start_stop = Event
    button_label = Str('Start')

    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str
    identify_button = Button('Identify')
    instrument = Instance(visa.Instrument)

    traits_view = View(Group(Item('selected_device', label = 'Device', \
                                editor = EnumEditor(name='_available_devices_map'), \
                                enabled_when='not running'),
                            Item('identify_button', enabled_when = 'selected_device != \'\''),
                            label = 'Instrument', show_border=True),
                        Group(Item('start_voltage', enabled_when='not running'),
                            Item('step_voltage', enabled_when='not running'),
                            Item('stop_voltage', enabled_when='not running'),
                            Item('current_limit', enabled_when='not running', label = 'Current limit [mA]'),
                            Item('current_range', enabled_when='not running'),
                            Item('current_voltage', enabled_when='False', label = 'U [V]'),
                            Item('current_current', enabled_when='False', label = 'I [mA]'),
                            Item('reading_overflow', style = 'readonly', editor=BooleanEditor(mapping={'READING OVERFLOW':True, '':False})), # Does not work
                            Item('current_limit_exceeded', style = 'readonly', editor=BooleanEditor(mapping={'CURRENT TOO HIGH':True, '':False})),
                            label='I/V', show_border = True),
                        Item('update_interval'),
                        Item('start_stop', label = 'Start/Stop Acqusistion',
                                editor = ButtonEditor(label_value='button_label')),
                        handler = ViewHandler)

    def instrument_init(self):
        if self.instrument is not None:
            self.instrument.write('reset()')
            self.instrument.write('digio.writeprotect = 0')
            nplc = (self.update_interval * 0.8) / 0.02     # ADC time is 80% of self.updatE_interval (assuming 50Hz PLC)
            self.instrument.write('smua.measure.nplc = '+ str(nplc))
            self.instrument.write('smua.sense = smua.SENSE_REMOTE') # 4-wire measurement
            self.instrument.write('status.measurement.reading_overflow.enable =\
                status.measurement.reading_overflow.SMUA')
            self.instrument.write('status.measurement.voltage_limit.enable =\
                status.measurement.voltage_limit.SMUA')
            self.instrument.write('smua.source.autorangei = smua.AUTORANGE_ON')
            self.instrument.write('smua.source.autorangev = smua.AUTORANGE_ON')
            self.instrument.write('smua.measure.autorangei = smua.AUTORANGE_OFF')
            self.instrument.write('smua.measure.autorangev = smua.AUTORANGE_OFF')
            self.instrument.write('smua.source.func = smua.OUTPUT_DCVOLTS')
            self.instrument.write('smua.source.limiti = ' + str(self.current_limit/1000))
            tmp_str = '%e' % self.start_voltage
            self.instrument.write('smua.source.levelv = ' + tmp_str)
            self.instrument.write('smua.source.output = smua.OUTPUT_ON')

    def instrument_stop(self):
        if self.instrument is not None:
            self.instrument.write('smua.source.levelv = 0')
            self.instrument.write('smua.source.output = smua.OUTPUT_OFF')

    def start(self):
        self.button_label = 'Stop'
        self.sample_nr = 0
        self.running = True
        self.instrument_init()
        if self.timer is None:
            self.timer = Timer(self.update_interval * 1000, self._onTimer)
        else:
            self.timer.Start(self.update_interval * 1000)

    def stop(self):
        if self.timer is not None:
            self.timer.Stop()
        self.button_label = 'Start'
        self.running = False
        self.timer_dormant = False
        self.instrument_stop()

    def _onTimer(self):
        self.timer.Stop()
        self.timer_dormant = True
        d = dict()
        values = self.instrument.ask_for_values('print(smua.measure.iv())')
        self.current_voltage = values[1]
        self.current_current = values[0]
        values = self.instrument.ask_for_values('print(status.measurement.reading_overflow.condition)')
        if values[0] == 2:
            self.reading_overflow = True
        else:
            self.reading_overflow = False
        values = self.instrument.ask_for_values('print(status.measurement.current_limit.condition)')
        if values[0] == 2:
            self.current_limit_exceeded = True
        else:
            self.current_limit_exceeded = False

        d[self.output_channels[0]] = (dict({self.x_units[0] : self.current_voltage}),
                                        dict({self.y_units[0] : self.current_current}))
        self.acquired_data.append(d)

        calc_curr_voltage = self.start_voltage + self.sample_nr * self.step_voltage
        self.timer.Start(self.update_interval * 1000)
        self.timer_dormant = False
        if calc_curr_voltage <= self.stop_voltage:
            tmp_str = '%e' % (calc_curr_voltage + self.step_voltage)
            self.instrument.write('smua.source.levelv = ' + tmp_str)
            self.sample_nr += 1
        else:
            self.start_stop = True

    def _start_stop_fired(self):
        if self.instrument is None:
            return
        if self.timer is None:
            self.start()
            return
        if self.timer.isActive() or self.timer_dormant:
            self.stop()
        else:
            self.start()

    def _selected_device_changed(self, new):
        try:
            self.instrument = visa.Instrument(new, timeout = 2)
            self.instrument.write('*RST')
        except visa.VisaIOError as e:
            logger.error('Caught exception: %s', e)
            self.instrument = None

    def _identify_button_fired(self):
        if self.instrument is not None:
            self.instrument.write('beeper.enable = 1')
            self.instrument.write('beeper.beep(0.2, 621)')
            sleep(0.4)
            self.instrument.write('beeper.beep(0.2, 453)')

    def _enabled_channels_default(self):
        return [True]

    def __available_devices_map_default(self):
        try:
            instruments = visa.get_instruments_list()
        except visa.VisaIOError:
            return {}

        d = dict()
        candidates = [n for n in instruments if n.startswith('GPIB')]
        for instrument in candidates:
            temp_inst = visa.instrument(instrument)
            model = temp_inst.ask('*IDN?')
            if model.find('Keithley') == 0 and model.find('26') > 0:
                d[instrument] = model

        candidates = [n for n in instruments if n.startswith('USB') and n.find('0x26') > 0]
        for instrument in candidates:
            temp_inst = visa.instrument(instrument)
            model = temp_inst.ask('*IDN?')
            if model.find('Keithley') == 0 and model.find('26') > 0:
                d[instrument] = model

        candidates = [n for n in instruments if n.startswith('k-26')]
        for instrument in candidates:
            try:
                temp_inst = visa.instrument(instrument)
            except  visa.VisaIOError:
                pass
            model = 'asd'#temp_inst.ask('*IDN?')
            if model.find('Keithley') == 0 and model.find('26') > 0:
                d[instrument] = model

        candidates = [n for n in instruments if n.lower().startswith('sourcemeter')]
        for instrument in candidates:
            temp_inst = visa.instrument(instrument, timeout = 1)
            temp_inst.term_chars = '\n'
            model = temp_inst.ask('*IDN?')
            if model.find('Keithley') == 0 and model.find('26') > 0:
                d[instrument] = model
        return d

    def _start_voltage_default(self):
        return DEFAULT_START_VOLTAGE

    def _stop_voltage_default(self):
        return DEFAULT_STOP_VOLTAGE

    def _step_voltage_default(self):
        return DEFAULT_STEP_VOLTAGE


if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    s = SourceMeter()
    s.configure_traits()
