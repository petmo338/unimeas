import logging
import os
from traits.api import HasTraits, Range, Instance, Bool, Dict, \
    List, Float, Unicode, Str, Int, on_trait_change, Event, Button, Enum
from traitsui.api import View, Item, Group, ButtonEditor, \
    EnumEditor, Label, HGroup, spring, VGroup, Handler
import traits.has_traits
#traits.has_traits.CHECK_INTERFACES = 2
from time import time
from serial_util import SerialUtil
from pyface.timer.api import Timer
import visa

from i_instrument import IInstrument
logger = logging.getLogger(__name__)
INSTRUMENT_IDENTIFIER = ['KEITHLEY', '21']


class K2100Handler(Handler):
    def closed(self, info, is_ok):
        if info.object.instrument is not None:
            info.object.instrument.close()

#@provides(IInstrument)
class K2100(HasTraits):
    """Keithley 2100 multimeter driver"""
    sampling_interval = Range(0.05, 10, 1)
    start_stop = Event
    refresh_list = Button
    button_label = Str('Start')
    acquired_data = List(Dict)
    _available_devices_map = Dict(Unicode, Unicode)
    selected_device = Str

    
    measurement_info = Dict()
    visa_resource = Instance(visa.ResourceManager, ())
    instrument = Instance(visa.Resource)
    measurement_mode = Str('RES')
    measurement_map_mode = Dict({'RES': 'Resistance', 'VOLT:DC': 'Voltage DC',
                                'VOLT:AC': 'Voltage AC', 'CURR:DC': 'Current DC',
                                'CURR:AC': 'Current AC', 'FREQ': 'Frequency',
                                'TEMP': 'Temperature'})
    x_units = Dict({0:'SampleNumber', 1:'Time'})
    y_units = Dict({0: 'Resistance', 1: 'Voltage', 2: 'Current',
           3: 'Frequency', 4: 'Temp'})
    acq_value = Float
    measurement_time = Float
    sample_nr = Int
    
    #### 'IInstrument' interface #############################################
    name = Unicode('Keithley 2100')
    measurement_info = Dict()
    running = Bool(False)
    output_channels = Dict({0:'chan0'})
    enabled_channels = List(Bool)
    
    traits_view = View(HGroup(Label('Device: '), Item('selected_device',
                        show_label = False,
                            editor = EnumEditor(name='_available_devices_map'),
                            enabled_when='not running'),
                            Item('refresh_list')),
                        Item('measurement_mode',
                            editor = EnumEditor(name='measurement_map_mode'),
                            enabled_when='False'),
                        Item('sampling_interval', enabled_when='not running'),
                        Item('start_stop', label = 'Start/Stop Acqusistion',
                                editor = ButtonEditor(label_value='button_label')),
                        Item('acq_value', style = 'readonly'),
                        Item('measurement_time', style = 'readonly', format_str = '%.2f'),
                        Item('sample_nr', style = 'readonly'),
                        handler=K2100Handler)

    def _enabled_channels_default(self):
        return [True]

#    def _measurement_mode_default(self):
#        return self.y_units.values()

    def __available_devices_map_default(self):
        try:
            instruments_info = self.visa_resource.list_resources_info()
        except visa.VisaIOError:
            return {}

        d = {}
        candidates = [n for n in instruments_info.values() if n.resource_name.upper().startswith('USB')]
        d.update(SerialUtil.probe(candidates, self.visa_resource, INSTRUMENT_IDENTIFIER))

        return d

    def _refresh_list_fired(self):
        self._available_devices = self.__available_ports_default()

    def _fix_output_dict(self, data):
        d = {}
        for unit in self.y_units.values():
            d[unit] = 0.0
            
        for mode in self.measurement_map_mode:
            if mode == self.measurement_mode:
                d[self.measurement_map_mode[mode]] = data
        return d


    def add_data(self):
        if not self.running:
            return
        self.sample_nr += 1
        try:
            data = self.instrument.query('READ?')     
        except visa.VisaIOError:
            data = self.acq_value
            pass
        self.acq_value = float(data)
        logger.info(data)
        self.measurement_time = time() - self.acq_start_time   
        d = dict()
        for i, enabled in enumerate(self.enabled_channels):

            d[self.output_channels[i]] = (dict({self.x_units[0]:self.sample_nr,
                                            self.x_units[1]:self.measurement_time}),\
                            self._fix_output_dict(self.acq_value))                           
        self.timer = Timer.singleShot(max(0,
            ((float(self.sample_nr) * self.sampling_interval) - self.measurement_time) * 1000),
            self.add_data)
        self.acquired_data.append(d)



    def start(self):
        self.running = True
        self.acq_start_time = time()
        self.sample_nr = 0
        self.instrument = SerialUtil.open(self.selected_device, self.visa_resource)
        self.instrument_init()
        if self.instrument is None:
#            GenericPopupMessage(message ='Error opening ' + new).edit_traits()
            self.instrument = None
            self.selected_device = ''

        self.timer = Timer.singleShot(self.sampling_interval * 1000, self.add_data)


    def stop(self):
        logger.info('stop()')
        self.running = False
        self.instrument.close()
            

    def instrument_init(self):
        self.instrument.write('FUNC "' + self.measurement_mode + '"')
        self.instrument.write(self.measurement_mode + ':RANG:AUTO ON')
        self.instrument.write('TRIG:SOUR IMM')
        
 

    ##########################################################################

    def _start_stop_fired(self, old, new):
        if self.selected_device == '':
            return
        if self.running:
            self.button_label= 'Start'
            self.stop()
        else:
            self.button_label = 'Stop'
            self.start()


    #def channel_changed(self, obj, name, new):
    #    self.enabled_channels[int(name[2:])] = new



if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    n = K2100()
    n.configure_traits()

#    a = AcquisitionThread()
#    d = DummySourcemeterTime()
#    d.tracer = SimpleTracer()
#    d.on_trait_change(d._log_changed)
#    d.traits_view = View(d.parameter_group)

#    d.tracer.configure_traits()
#    d.configure_traits()

    #d.start()
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
