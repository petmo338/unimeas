import logging
from enthought.traits.api import HasTraits, Range, Instance, Float, Dict, \
    List, implements, Unicode, Str, Array, Int, \
   Event, Bool
from enthought.traits.ui.api import View, Item, Group, ButtonEditor, HGroup, Handler
from threading import Thread
from time import sleep, time
from numpy import random
#import pdb
import Queue

from i_instrument import IInstrument

class AcquisitionThread(Thread, HasTraits):
    """ Acquisition loop. """
    wants_abort = False
    config = {}
    x_data = Array(float, shape=(1,2))
    y_data_ch0 = Array(float, shape=(1,3))
    y_data_ch1 = Array(float, shape=(1,3))
    start_time = Float
    sample_no = Int(0)
    def __init__(self, queue):
        super(AcquisitionThread, self).__init__()
        self.queue = queue

    def run(self):
        while not self.wants_abort:
            self.sample_no += 1
            sleep(self.config['sampling_interval'])
            retval = [self.sample_no, time() - self.start_time]
            retval.append(self.config['mean_voltage'] +
                           self.config['stdev_voltage'] *
                             random.random_sample())
            retval.append(self.config['mean_current'] +
                           self.config['stdev_current'] *
                             random.random_sample())
            retval.append(self.config['mean_resistance'] +
                           self.config['stdev_resistance'] *
                             random.random_sample())
            retval.append(self.config['mean_voltage'] +
                           self.config['stdev_voltage'] *
                             random.random_sample())
            retval.append(self.config['mean_current'] +
                           self.config['stdev_current'] *
                             random.random_sample())
            retval.append(self.config['mean_resistance'] +
                           self.config['stdev_resistance'] *
                             random.random_sample())
            self.queue.put(retval)
#            logging.getLogger(__name__).info('adding data %s', retval)


class DummySourcemeterTimeHandler(Handler):

#    def init(self, info):
#        logging.getLogger(__name__).info('DummySourcemeterTimeHandler init, info: %s', info)

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        logging.getLogger(__name__).info('DummySourcemeterTimeHandler.closed()')
        info.object.stop()
        #if isinstance(info.object.acquisition_thread, AcquisitionThread):
        #    logging.getLogger(__name__).info('DummySourcemeterTimeHandler killing thread')
        #    info.object.acquisition_thread.wants_abort = True
        #    while info.object.acquisition_thread.isAlive():
        #        info.object.trace('Waiting for acq-thread to give up')
        #        sleep(0.1)
#        return

class DummySourcemeterTime(HasTraits):
    """Dummy instrument for generation of values (V, I, R) over time"""

    implements(IInstrument)

    mean_voltage = Range(-10.0, 10.0, 3.1)
    mean_current = Range(0, .1, 0.0034)
    mean_resistance = Range(0, 10e9, 1e6)
    sampling_interval = Range(0.05, 10, 1)
    stdev_voltage = Range(0.0, 1.0, .1)
    stdev_current = Range(0, .1, .005)
    stdev_resistance = Range(0, 100000, 10000)
    channel_0 = Bool(True)
    channel_1 = Bool(True)
    start_stop = Event
    button_label = Str('Start')
    acquisition_thread = Instance(AcquisitionThread)
    running = False
    output_unit = 0
    timebase = 0

    queue = Queue.Queue()

    parameter_group = Group(
        Item('mean_voltage'),
        Item('mean_current'),
        Item('mean_resistance'),
        Item('stdev_voltage'),
        Item('stdev_current'),
        Item('stdev_resistance'),
        Item('sampling_interval'),
        HGroup(Item('channel_0', enabled_when = 'not running'),
            Item('channel_1', enabled_when = 'not running')),
        show_border = True)

    traits_view = View(parameter_group,
                        Item('start_stop', label = 'Start/Stop Acqusistion',
                                editor = ButtonEditor(label_value='button_label')), \
                                handler=DummySourcemeterTimeHandler)

    def __init__(self, **traits):
        super(DummySourcemeterTime, self).__init__(**traits)
        self.logger = logging.getLogger('dummysourcermeter')
        self.on_trait_change(self.add_data, 'acquisition_thread.sample_no')
        self.on_trait_change(self.update_config, 'sampling_interval, mean_+, stdev_+')
        self.on_trait_change(self.channel_changed, 'channel_+')
#        self.on_trait_change(self._tmp, 'acquired_data[]')



    def add_data(self):
        if self.acquisition_thread.sample_no is 0:
            return
#        pdb.set_trace()
#        self.logger.info("Size %d", self.x_data.shape[0])
#        logging.getLogger(__name__).info('add_data')
        while self.queue.empty() is False:
            item = self.queue.get()
            self.queue.task_done()
#            logging.getLogger(__name__).info('add_data, item: %s', item)

            self.dispatch_data(item)

    def dispatch_data(self, data):
        d = dict()
#        if self.channel_0:
        d[self.output_channels[0]] = (dict({self.x_units[0]:data[0], self.x_units[1]:data[1],}),\
                            dict({self.y_units[0]:data[2], \
                                self.y_units[1]:data[3], \
                                self.y_units[2]:data[4],}))
#            logging.getLogger(__name__).info('y: %s', d['ch0'][1])
        #else:
        #    d[self.output_channels[0]] = (dict({self.x_units[0]:data[0], self.x_units[1]:data[1],}),\
#                                dict())
#        if self.channel_1:
        d[self.output_channels[1]] = (dict({self.x_units[0]:data[0], self.x_units[1]:data[1],}),\
                            dict({self.y_units[0]:data[5], \
                                self.y_units[1]:data[6], \
                                self.y_units[2]:data[7],}))
        #else:
        #    d[self.output_channels[1]] = (dict({self.x_units[0]:data[0], self.x_units[1]:data[1],}),\
        #                        dict())

        self.acquired_data.append(d)
#        logging.getLogger(__name__).info('acquired_data: %s', self.acquired_data)


    def initialize(self):
        self.logger.info('DummySourcemeterTime initialize()')

    def identify(self):
        self.logger.info('BEEP')

    def close(self):
        self.logger.info('DummySourcemeterTime close()')

    def start(self):
#        self.logger.info('DummySourcemeterTime start()')

        self.acquisition_thread = AcquisitionThread(self.queue)
        self.acquisition_thread.config['stdev_current'] = self.stdev_current
        self.acquisition_thread.config['stdev_voltage'] = self.stdev_voltage
        self.acquisition_thread.config['stdev_resistance'] = self.stdev_resistance
        self.acquisition_thread.config['mean_current'] = self.mean_current
        self.acquisition_thread.config['mean_voltage'] = self.mean_voltage
        self.acquisition_thread.config['mean_resistance'] = self.mean_resistance
        self.acquisition_thread.config['sampling_interval'] = self.sampling_interval
        self.acquisition_thread.start_time = time()
        self.acquisition_thread.start()
        self.running = True


    def stop(self):
        self.logger.info('DummySourcemeterTime stop()')
        if isinstance(self.acquisition_thread, AcquisitionThread):
            self.logger.info('DummySourcemeterTime stopping acq thread')
            self.acquisition_thread.wants_abort = True
            while self.acquisition_thread.isAlive():
                self.logger.info('Waiting for acq-thread to give up')
                sleep(0.1)
        self.running = False

    #### 'IInstrument' interface #############################################
    name = Unicode('Dummy Sourcemeter')
    output_channels = Dict({0: 'ch0', 1: 'ch1'})
    enabled_channels = List(Bool)
    acquired_data = List(Dict)

    y_units = Dict({0:'Voltage', 1:'Current', 2:'Resistance'})
    x_units = Dict({0:'SampleNumber', 1:'Time'})


    ##########################################################################

    def _start_stop_changed(self, old, new):
        self.logger.info('start_stop_acq_fired, %s, %s', old, new)
        if self.running:
            self.button_label= 'Start'
            self.stop()
        else:
            self.button_label = 'Stop'
            self.start()

    def _enabled_channels_default(self):
        return [True] * 2

    def channel_changed(self, obj, name, new):
        self.enabled_channels[int(name[8:])] = new

    def update_config(self):
        if hasattr(self.acquisition_thread, 'config'):
            self.acquisition_thread.config['stdev_current'] = self.stdev_current
            self.acquisition_thread.config['stdev_voltage'] = self.stdev_voltage
            self.acquisition_thread.config['stdev_resistance'] = self.stdev_resistance
            self.acquisition_thread.config['mean_current'] = self.mean_current
            self.acquisition_thread.config['mean_voltage'] = self.mean_voltage
            self.acquisition_thread.config['mean_resistance'] = self.mean_resistance
            self.acquisition_thread.config['sampling_interval'] = self.sampling_interval

#    @on_trait_change('acquired_data[]')
#    def _tmp(self):
#        logging.getLogger(__name__).info(' @on_trait_change(acquired_data)')
#if __name__ == '__main__':
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
