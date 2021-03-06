import logging
from traits.api import HasTraits, Int, Bool, Str, Event, Instance, Dict, Tuple
from traitsui.api import Item, View, Handler, ButtonEditor, HGroup, spring, Label
from pyface.timer.api import Timer
import threading
import Queue
import json
import csv
from random import random

logger = logging.getLogger(__name__)
from time import time, sleep

try:
    import zmq
except ImportError as e:
    logger.warning(e)
    USE_ZMQ = False
else:
    USE_ZMQ = True

UPDATE_INTERVAL = 500
CONNECT_TIMEOUT = 5000
POLL_TIMEOUT = 10


class State:
    DISCONNECTED = 1
    CONNECTING = 2
    CONNECTED = 3
    STARTING = 4
    RUNNING = 5
    STOPPING = 6

    strings = {DISCONNECTED: 'Disconnected',
               CONNECTING: 'Connecting',
               CONNECTED: 'Connected',
               STARTING: 'Starting',
               RUNNING: 'Running',
               STOPPING: 'Stopping'}


class GasMixerSubscriber(threading.Thread):
    def __init__(self, sub_queue, control_queue):
        super(GasMixerSubscriber, self).__init__()
        self.exit_flag = False
        try:
            self.context = zmq.Context().instance()
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect('tcp://localhost:5561')
            self.subscriber.setsockopt(zmq.SUBSCRIBE, "")
            self.control = self.context.socket(zmq.REQ)
            self.control.connect('tcp://localhost:5562')
            self.poller = zmq.Poller()
            self.poller.register(self.subscriber, zmq.POLLIN)
            self.sub_queue = sub_queue
            self.control_queue = control_queue
        except:
            return None

    def run(self):
        while not self.exit_flag:
            socks = dict(self.poller.poll(POLL_TIMEOUT))
            if self.subscriber in socks and socks[self.subscriber] == zmq.POLLIN:
                msg = self.subscriber.recv()
                self.sub_queue.put_nowait(msg)

            if not self.control_queue.empty():
                self.control.send(self.control_queue.get())
                self.control_queue.task_done()
                msg = self.control.recv()
                self.sub_queue.put_nowait(msg)
        self.sub_queue.put_nowait('KILLINGMYSELF')


class GasMixerPanelHandler(Handler):
    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        if info.object.gasmixer_broker is not None:
            info.object.gasmixer_broker.exit_flag = True
            info.object.gasmixer_broker.join()
        return


class GasMixerPanel(HasTraits):
    """"########### Panel Interface ###########################"""

    pane_name = Str('Gasmixer control')
    pane_id = Str('sensorscience.unimeas.gasmixer_pane')

    running = Bool(False)
    timer = Instance(Timer)
    button = Event
    y_units = Dict({0: 'column'})
    x_units = Dict({0: 'time'})
    output_data = Tuple(Dict, Dict)
    current_column = Int(0)

    output_channels = Dict({0: 'gasmixer'})
    control_gasmixer = Bool(True)
    connected = Bool(False)
    running_label = Str
    state = Int(State.DISCONNECTED)
    connect_timeout = Int(0)
    gasmixer_broker = Instance(GasMixerSubscriber)
    subscribe_queue = Instance(Queue.Queue, ())
    control_queue = Instance(Queue.Queue, ())
    gas_mix = Dict()
    fake_gasmixer_connection = False
    log_gas_flow = Bool(True)


    traits_view = View(Item('control_gasmixer', label='Follow Start/Stop from GasMixer', enabled_when='state is 3'),
                       Item('log_gas_flow', label='Add gas flow to meas. data', enabled_when='not running'),
                       Item('current_column', label='Curr. column', style='readonly'),
                       Item('running_label', label='State', style='readonly'),
                       handler=GasMixerPanelHandler)

    def _on_timer(self):
        self.connect_timeout += UPDATE_INTERVAL
        while not self.subscribe_queue.empty():
            self.connect_timeout = 0
            msg = self.subscribe_queue.get()
            self.subscribe_queue.task_done()
            # logger.debug(msg)

            self.connect_timeout = 0
            if msg.find('NEWCOL') != -1:
                logger.info(msg)
                self.current_column = int(msg.strip('NEWCOL '))

            elif msg.find('STOP') != -1:
                logger.info(msg)
                for gas in self.gas_mix.values():
                    gas[1] = 0
                if self.control_gasmixer:
                    if hasattr(self, 'active_instrument'):
                        if self.active_instrument.running is True:
                            self.active_instrument.start_stop = True
            elif msg.find('START') != -1:
                logger.info(msg)
                if self.control_gasmixer:
                    if hasattr(self, 'active_instrument'):
                        if self.active_instrument.running is False:
                            self.active_instrument.start_stop = True
            elif msg.find('HEARTBEAT') != -1:
                logger.debug(msg)
                if self.state != State.CONNECTED:
                    self.control_queue.put('CONNECT')
            elif msg.find('CONFIG') != -1:
                logger.info('Found CONFIG i msg %s', msg)
                jpath = json.loads(msg[6:])
                self.parse_board_file(jpath.get("boardname", ""))
                self.state = State.CONNECTED
                self.running_label = 'GasMixer ' + State.strings[self.state]
            elif msg.find('FLOW') != -1:
                logger.debug(msg)
                if self.state == State.CONNECTED:
                    flow_string = msg.split(',')[0]
                    address_string = msg.split(',')[1]
                    flow = int(flow_string.split(':')[1])
                    address = int(address_string.split(':')[1])
                    self.gas_mix[address][1] = (flow / 32000.0) * float(self.gas_mix[address][2])

            elif msg.find('KILLINGMYSELF'):
                self.timer.stop()
        if self.connect_timeout > CONNECT_TIMEOUT:
            self.state = State.DISCONNECTED
            self.running_label = 'GasMixer ' + State.strings[self.state]
        self.timer = Timer.singleShot(UPDATE_INTERVAL, self._on_timer)

    def __init__(self, **traits):
        if USE_ZMQ is False:
            return None
        super(GasMixerPanel, self).__init__(**traits)
        self.gasmixer_broker = GasMixerSubscriber(self.subscribe_queue, self.control_queue)
        if self.gasmixer_broker is None:
            return None
        else:
            self.gasmixer_broker.start()
        self.state = State.DISCONNECTED
        self.timer = Timer.singleShot(UPDATE_INTERVAL, self._on_timer)

    def _output_data_default(self):
        return {self.x_units[0]: 0}, {self.y_units[0]: 0}

    def _running_label_default(self):
        return 'GasMixer ' + State.strings[self.state]

    def start_stop(self, starting):
        if starting:
            self.running = True
        else:
            self.running = False
        return

    def get_data(self):
        d = {'column': self.current_column}
        for gas in self.gas_mix.values():
            d[gas[0]] = gas[1]

        self.output_data = ({self.x_units[0]: 0}, d)
        return self.output_data

    def parse_board_file(self, path):
        try:
            with open(path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row[0] == 'Reg':
                        self.gas_mix[int(row[22])] = [row[2], 0, row[23]]
                self._update_y_units()
                logger.info('Gas concentratoions: %s', self.gas_mix)
        except IOError as e:
            logger.error('Can not parse %s', e)

    def _update_y_units(self):
        if self.log_gas_flow:
            for i, gas_mix in enumerate(self.gas_mix.values()):
                self.y_units[i+1] = gas_mix[0]
        else:
            self.y_units = {0: 'column'}
        logger.debug('Current Y units: %s', self.y_units)

    def _log_gas_flow_changed(self):
        self._update_y_units()

if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.INFO)
    l.info('test')
    g = GasMixerPanel()
    g.configure_traits()
    logging.shutdown()
