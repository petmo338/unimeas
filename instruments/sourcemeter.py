from traits.api import Unicode, Dict, Int, Event, Bool, List,\
    HasTraits, Str, Button, Float, implements, Instance, on_trait_change
    
from enthought.traits.ui.api import Group, HGroup, Item, View, Handler, \
    ButtonEditor, EnumEditor
from i_instrument import IInstrument
import logging
import visa
from time import sleep, time
from threading import Thread
import Queue

class AcquisitionThread(Thread, HasTraits):
    wants_abort = Bool(False)
    sample_number = Int(0)
    
    def __init__(self, queue, instrument, sampling_interval):
        super(AcquisitionThread, self).__init__()
        self.queue = queue
        self.instrument = instrument
        self.sampling_interval = sampling_interval
    
    def run(self):
        start_time = time()
        while not self.wants_abort:
            sleep(self.sampling_interval)
            self.sample_number += 1
            retval = [self.sample_number, time() - start_time]
            values = self.instrument.ask_for_values('print(smua.measure.iv())')
            retval.append(values[1])
            retval.append(values[0])
            retval.append(values[1]/values[0])           
            self.queue.put(retval)
            #logging.getLogger(__name__).info('Values from sourcemeter %s', values)
            #self.instrument.write('print(status.measurement.instrument.condition)')
            #condition = self.instrument.read_raw() 
            
            #logging.getLogger(__name__).info('Condition from sourcemeter %s', condition)
            

class SourceMeterHandler(Handler):
    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        logging.getLogger(__name__).info('SourcemeterHandler.closed()')
        info.object.stop()
  

class SourceMeter(HasTraits):

    implements(IInstrument)
    # The user-visible name of the instrument.
    name = 'Keithley SourceMeter'
    
    x_units = Dict({0:'SampleNumber', 1:'Time'})
    y_units = Dict({0: 'Voltage', 1: 'Current', 2: 'Resistance'})

    acquired_data = List(Dict)
    
    start_stop = Event
    running = Bool
    
    output_channels = Dict({0: 'smua'})
    """ Must not have overlapping names \ 
        i.e. ai1, ai12, ai13 will generate error """
    enabled_channels = List(Bool)
    instrument = Instance(visa.Instrument)
    acquisition_thread = Instance(AcquisitionThread)
    selected_device = Str 
    identify_button = Button('Identify')
    constant_current_mode = Bool(True)
    constant_voltage_mode = Bool(False)
    
    current = Float(0.1)
    voltage = Float(1)
    
    current_limit = Float(100.0)
    voltage_limit = Float(5.0)
    
    _current_range_map = Dict({'Auto':'Auto', '3':'3 A', '1':'1 A', '0.1':'100 mA', \
        '0.01':'10 mA', '1e-3':'1 mA', '1e-4':'100 uA', '1e-5':'10 uA', \
        '1e-6':'1 uA', '1e-7':'100 nA'})
    _voltage_range_map = Dict({'Auto':'Auto', '40':'40 V', '6':'6 V', '1':'1 V', '0.1':'0.1 V'})
    current_range = Str('Auto')
    voltage_range = Str('Auto')
    sampling_interval = Float(1.0)
    start_stop = Event
    button_label = Str('Start')
    _available_devices_map = Dict(Unicode, Unicode)
    running = Bool(False)
    queue = Instance(Queue.Queue)
    
    measurement_settings_group = Group(HGroup(Item('constant_current_mode', show_label = False), \
                                            Item('current', label = 'Current [mA]'), \
                                            Item('voltage_limit', label = 'Voltage limit [V]')), \
                                        HGroup(Item('constant_voltage_mode', show_label = False), \
                                            Item('voltage', label = 'Voltage [V]'), \
                                            Item('current_limit', label = 'Current limit [mA]')), \
                                            show_border = True, label = 'Setup')
                                        
    instrument_settings_group = Group(HGroup(Item('current_range', \
                            editor = EnumEditor(name='_current_range_map')), \
                            Item('voltage_range', \
                            editor = EnumEditor(name='_voltage_range_map'))), \
                                    Item('sampling_interval'), show_border = True, \
                                    label = 'Measurement ranges')
    
    traits_view = View(HGroup(Item('selected_device', label = 'Device', \
                                editor = EnumEditor(name='_available_devices_map'), \
                                enabled_when='not running'), Item('identify_button', enabled_when = 'selected_device != \'\'')), \
                        measurement_settings_group,\
                        instrument_settings_group,\
                        Item('start_stop', label = 'Start/Stop Acqusistion',\
                            editor = ButtonEditor(label_value='button_label'), enabled_when = 'selected_device != \'\''),\
                        handler = SourceMeterHandler)
    def __init__(self, **traits):
        super(SourceMeter, self).__init__(**traits)
        self.logger = logging.getLogger(__name__)
        self.on_trait_change(self.add_data, 'acquisition_thread.sample_number')
                                
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
                
        candidates = [n for n in instruments if n.startswith('SourceMeter')]
        for instrument in candidates:
            temp_inst = visa.instrument(instrument, timeout = 1)
            temp_inst.term_chars = '\n'
            model = temp_inst.ask('*IDN?')
            if model.find('Keithley') == 0 and model.find('26') > 0:
                d[instrument] = model    
        return d

    def _selected_device_changed(self, new):
        self.instrument = visa.Instrument(new, timeout = 2)
        self.instrument.write('reset()')
                       
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
        return [True] * 1
                                                      
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
        self.queue = Queue.Queue()

        self.acquisition_thread = AcquisitionThread(self.queue, self.instrument, \
            self.sampling_interval)
        self.acquisition_thread.start()
                        
    def stop(self):
        if isinstance(self.acquisition_thread, AcquisitionThread):
            logging.getLogger(__name__).info('Sourcemeter stop')
            self.acquisition_thread.wants_abort = True
            while self.acquisition_thread.isAlive():
                sleep(0.1)
        
        if type(self.instrument) == visa.Instrument:
            self.instrument.write('smua.source.output = smua.OUTPUT_OFF')
        self.running = False

        
    def add_data(self):
        if self.acquisition_thread.sample_number is 0:
            return

        while self.queue.empty() is False:
            item = self.queue.get()
            self.queue.task_done()
            self.dispatch_data(item)
    
    def dispatch_data(self, data):
        d = dict()
        d[self.output_channels[0]] = (dict({self.x_units[0]:data[0], self.x_units[1]:data[1],}),\
                                dict({self.y_units[0]:data[2], \
                                   self.y_units[1]:data[3], \
                                   self.y_units[2]:data[4],}))
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