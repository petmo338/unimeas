from traits.api import Unicode, Dict, Int, Event, Bool, List,\
    HasTraits, Str, Button, Float,  Instance, on_trait_change

from traitsui.api import Group, HGroup, Item, View, Handler, \
    ButtonEditor, EnumEditor

from i_instrument import IInstrument
import logging
import visa
from time import sleep, time
#from threading import Thread
from ..generic_popup_message import GenericPopupMessage

from serial_util import SerialUtil
from pyface.timer.api import Timer

ID_STRING_LENGTH = 30
INSTRUMENT_IDENTIFIER = ['Keithley', '26']
visa.logger.level=logging.ERROR
logger = logging.getLogger(__name__)

class SourceMeterHandler(Handler):
    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        logger.info('SourcemeterHandler.closed()')
        info.object.stop()

#@provides(IInstrument)
class SourceMeter(HasTraits):

#    implements(IInstrument)
    name = Unicode('SourceMeter 2600')
    measurement_info = Dict()
    x_units = Dict({0:'SampleNumber', 1:'Time'})
    y_units = Dict({0: 'Voltage', 1: 'Current', 2: 'Resistance'})

    acquired_data = List(Dict)

    start_stop = Event
    running = Bool

#    output_channels = Dict({0: 'smua0', 1: 'smua1', 2: 'smua2', 3: 'smua3'})
    output_channels = Dict({0: 'smua0'})
    """ Must not have overlapping names/numbers \
        i.e. ai1, ai12, ai13 will generate error """
    smua0_enabled = Bool(True)
    smua1_enabled = Bool(False)
    smua2_enabled = Bool(False)
    smua3_enabled = Bool(False)
    enabled_channels = List(Bool)
    visa_resource = Instance(visa.ResourceManager, ())
    instrument = Instance(visa.Resource)

    selected_device = Str
    identify_button = Button('Identify')
    constant_current_mode = Bool(True)
    constant_voltage_mode = Bool(False)

    current = Float(0.1)
    voltage = Float(1)

    current_limit = Float(100.0)
    voltage_limit = Float(5.0)

    _current_range_map = Dict({'Auto':'Auto', '3':'3A', '1':'1A', '0.1':'100mA', \
        '0.01':'10mA', '1e-3':'1mA', '1e-4':u'100\u00B5A', '1e-5':u'10\u00B5A', \
        '1e-6':u'1\u00B5A', '1e-7':'100nA'})
    _voltage_range_map = Dict({'Auto':'Auto', '40':'40 V', '6':'6 V', '1':'1 V', '0.1':'0.1 V'})
    current_range = Str('Auto')
    voltage_range = Str('Auto')
    sampling_interval = Float(1.0)
    sample_number = Int
    button_label = Str('Start')
    _available_devices_map = Dict(Unicode, Unicode)
    running = Bool(False)
    timer = Instance(Timer)


    measurement_settings_group = Group(HGroup(Item('constant_current_mode', show_label = False), \
                                            Item('current', label = 'Current [mA]'), \
                                            Item('voltage_limit', label = 'Voltage limit [V]'), enabled_when = 'not running'), \
                                        HGroup(Item('constant_voltage_mode', show_label = False), \
                                            Item('voltage', label = 'Voltage [V]'), \
                                            Item('current_limit', label = 'Current limit [mA]'), enabled_when = 'not running'), \
                                            show_border = True, label = 'Setup')

    instrument_settings_group = Group(HGroup(Item('current_range', \
                            editor = EnumEditor(name='_current_range_map')), \
                            Item('voltage_range', \
                            editor = EnumEditor(name='_voltage_range_map'))), \
                                    Item('sampling_interval'), show_border = True, \
                                    label = 'Measurement ranges')
    enabled_channels_group = HGroup(Item('smua0_enabled', label = '0'),
                                    Item('smua1_enabled', label = '1', enabled_when = 'False'),
                                    Item('smua2_enabled', label = '2', enabled_when = 'False'),
                                    Item('smua3_enabled', label = '3', enabled_when = 'False'),
                                    show_border = True, label = 'Enabled channels',
                                    enabled_when = 'not running')
    traits_view = View(HGroup(Item('selected_device', label = 'Device', \
                                editor = EnumEditor(name='_available_devices_map'), \
                                enabled_when='not running'), Item('identify_button',
                                enabled_when = 'selected_device != \'\'')), \
                        measurement_settings_group,
                        instrument_settings_group,
                        enabled_channels_group,
                        Item('start_stop', label = 'Start/Stop Acqusistion',\
                            editor = ButtonEditor(label_value='button_label'),
                            enabled_when = 'selected_device != \'\''),\
                        handler = SourceMeterHandler)

    def __available_devices_map_default(self):
        try:
            instruments_info = self.visa_resource.list_resources_info()
        except visa.VisaIOError:
            return {}

        d = {}
        candidates = [n for n in instruments_info.values() if n.resource_name.upper().startswith('GPIB')]
        d.update(SerialUtil.probe(candidates, self.visa_resource, INSTRUMENT_IDENTIFIER))

        candidates = [n for n in instruments_info.values() if n.resource_name.upper().startswith('USB')]
        d.update(SerialUtil.probe(candidates, self.visa_resource, INSTRUMENT_IDENTIFIER))

        candidates = [n for n in instruments_info.values() if n.resource_name.lower().startswith('k-26')]
        d.update(SerialUtil.probe(candidates, self.visa_resource, INSTRUMENT_IDENTIFIER))

        candidates = [n for n in instruments_info.values() if n.alias is not None and n.alias.lower().startswith('sourcemeter')]
        d.update(SerialUtil.probe(candidates, self.visa_resource, INSTRUMENT_IDENTIFIER))

        return d

    def _selected_device_changed(self, new):
        logger.info('New instrument %s', new)
        if self.instrument is not None:
            self.instrument.close()
        if new is not '':
            self.instrument = SerialUtil.open(new, self.visa_resource)
            if self.instrument is None:
                popup = GenericPopupMessage()
                popup.message = 'Error opening ' + new
                popup.configure_traits()
                self.instrument = None
                self.selected_device = ''

    def _selected_device_default(self):
        try:
            device = self._available_devices_map.items()[0][0]
        except IndexError:
            return ''
        self._selected_device_changed(device)
        return device

    def _identify_button_fired(self):
        if self.selected_device != '':
            self.instrument.write('beeper.enable = 1')
            self.instrument.write('beeper.beep(0.2, 621)')
            sleep(0.4)
            self.instrument.write('beeper.beep(0.2, 453)')

    def _start_stop_fired(self):
        if self.running:
              self.stop()
              self.button_label= 'Start'
        else:
            self.start()
            self.button_label = 'Stop'

    def _enabled_channels_default(self):
        return [self.smua0_enabled]#, self.smua1_enabled,
#                self.smua2_enabled, self.smua3_enabled]

    def start(self):
        self.instrument.write('reset()')
        self.instrument.write('digio.writeprotect = 0')
        self.instrument.write('smua.measure.nplc = 5')
        self.instrument.write('smua.sense = smua.SENSE_REMOTE')
        self.instrument.write('smua.source.autorangei = smua.AUTORANGE_ON')
        self.instrument.write('smua.source.autorangev = smua.AUTORANGE_ON')
        self.instrument.write('smua.measure.autorangei = smua.AUTORANGE_OFF')
        self.instrument.write('smua.measure.autorangev = smua.AUTORANGE_OFF')

        if self.constant_current_mode:
            self.instrument.write('smua.source.func = smua.OUTPUT_DCAMPS')
            self.instrument.write('smua.source.limitv = ' + str(self.voltage_limit))
            tmp_str = '%e' % (self.current / 1000)
            self.instrument.write('smua.source.leveli = ' + tmp_str)
            if self.voltage_range == 'Auto':
                self.instrument.write('smua.measure.autorangev = smua.AUTORANGE_ON')
            else:
                self.instrument.write('smua.measure.rangev = ' + self.voltage_range)
            self.instrument.write('display.smua.measure.func = smua.OUTPUT_DCVOLTS')
        else:
            self.instrument.write('smua.source.func = smua.OUTPUT_DCVOLTS')
            self.instrument.write('smua.source.limiti = ' + str(self.current_limit/1000))
            tmp_str = '%e' % self.voltage
            self.instrument.write('smua.source.levelv = ' + tmp_str)
            if self.current_range == 'Auto':
                self.instrument.write('smua.measure.autorangei = smua.AUTORANGE_ON')
            else:
                self.instrument.write('smua.measure.rangei = ' + self.current_range)
            self.instrument.write('display.smua.measure.func = smua.OUTPUT_DCAMPS')

        self.instrument.write('smua.source.output = smua.OUTPUT_ON')
        self.running = True
        self.start_time = time()
        self.sample_number = 0

        if self.timer is None:
            self.timer = Timer(self.sampling_interval * 1000, self._onTimer)
        else:
            self.timer.Start(self.sampling_interval * 1000)

    def stop(self):
        if self.timer is not None:
            self.timer.Stop()

        if self.instrument is not None:
            self.instrument.write('smua.source.output = smua.OUTPUT_OFF')
        self.running = False


    def _onTimer(self):
        self.sample_number += 1
        data = [self.sample_number, time() - self.start_time]
        values = self.instrument.query_ascii_values('print(smua.measure.iv())')
        data.append(values[1])
        data.append(values[0])
        data.append(values[1]/values[0])
        self.voltage = values[0]
        self.current = values[1]
        self.dispatch_data(data)

    def dispatch_data(self, data):
        d = dict()
        d[self.output_channels[0]] = (dict({self.x_units[0]:data[0], self.x_units[1]:data[1],}),\
                                dict({self.y_units[0]:data[2], \
                                   self.y_units[1]:data[3], \
                                   self.y_units[2]:data[4],}))
        #d[self.output_channels[1]] = (dict({}), dict({}))
        #d[self.output_channels[2]] = (dict({}), dict({}))
        #d[self.output_channels[3]] = (dict({}), dict({}))

        self.acquired_data.append(d)

    @on_trait_change('constant_current_mode, constant_voltage_mode')
    def _toggle_mode(self, obj, name, new):
        if name == 'constant_current_mode':
            self.constant_voltage_mode = not new
        elif name == 'constant_voltage_mode':
            self.constant_current_mode = not new


if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    s = SourceMeter()
    s.configure_traits()
