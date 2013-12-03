import zmq
import logging
logger = logging.getLogger(__name__)
from traits.api import HasTraits, Int, Bool, Str, Event, Instance, Dict, Tuple
from traitsui.api import Item, View, Handler, ButtonEditor,  HGroup, spring
from pyface.timer.api import Timer

UPDATE_INTERVAL = 500
CONNECT_TIMEOUT = 5000
class State:
    DISCONNECTED = 1
    CONNECTING = 2
    CONNECTED = 3
    STARTING = 4
    RUNNING = 5
    STOPPING = 6
    
    strings = dict({DISCONNECTED:'Disconnected',
                    CONNECTING:'Connecting',
                    CONNECTED:'Connected',
                    STARTING:'Starting',
                    RUNNING:'Running',
                    STOPPING:'Stopping'})

class GasMixerPanelHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        info.object.timer.Stop()
        return

class GasMixerPanel(HasTraits):
    
    ############ Panel Interface ###########################3
    
    pane_name = Str('Gasmixer control')
    pane_id = Str('sensorscience.unimeas.gasmixer_pane')

    
    running = Bool(False)
    timer = Instance(Timer)
    button = Event
    y_units = Dict({0 : 'column'})
    x_units = Dict({0 : 'time'})
    current_column = Tuple(Dict, Dict)
    current_column_int = Int(0)
    button_label = Str('Connect')
    output_channels = Dict({0:'gasmixer'})
    control_gasmixer = Bool(False)
    connected = Bool(False)
    running_label = Str('GasMixer stopped')
    state = Int(State.DISCONNECTED)
    connect_timeout = Int(0)
    
    traits_view = View(HGroup(Item('control_gasmixer', label = 'Control GasMixer'), spring, 
                        Item('running_label', show_label = False, style='readonly')),
                        Item('current_column_int'), 
                        Item('button', label = 'Control GasMixer',
                            editor = ButtonEditor(label_value = 'button_label')),
                            handler = GasMixerPanelHandler)
                       
    def _onTimer(self):
        self.running_label = 'GasMixer ' + State.strings[self.state]
        if self.state > 0: # State.DISCONNECTED: # Always recieive
            socks = dict(self.subscriber_poller.poll(1))
            if self.subscriber in socks and socks[self.subscriber] == zmq.POLLIN:
                msg = self.subscriber.recv()
                logging.getLogger('GasMixerPanel').info('_onTimer(), msg %s', msg)            
                if msg.find('NEWCOL') != -1:
                    self.current_column = ({self.x_units[0]:0}, \
                        {self.y_units[0]:int(msg.strip('NEWCOL '))})
                if msg.find('STOP') != -1:
                    if self.state != State.STOPPING:
                        self.state = State.CONNECTED
                if msg.find('START') != -1:
                    if self.state != State.STARTING:
                        self.state = State.STARTED


        if self.state == State.CONNECTING:
            socks = dict(self.sync_poller.poll(1))
            if self.syncclient in socks and socks[self.syncclient] == zmq.POLLIN:
                response = self.syncclient.recv()
                if response == 'CONNECT OK':
                    self.state = State.CONNECTED
                    self.button_label = 'Connected'
                    self.control_gasmixer = True
                    self.connect_timeout = 0
            else:
                if self.connect_timeout > CONNECT_TIMEOUT:
                    logging.getLogger(__name__).error('No response to CONNECT \
                        from GasMixer in %d ms, disconnecting', CONNECT_TIMEOUT )
                    self._disconnect()
                else:
                    self.connect_timeout += UPDATE_INTERVAL

        if self.state == State.STARTING:
            socks = dict(self.sync_poller.poll(1))
            if self.syncclient in socks and socks[self.syncclient] == zmq.POLLIN:
                response = self.syncclient.recv()
                if response == 'START OK':
                    self.state = State.RUNNING
                    self.connect_timeout = 0
            else:
                if self.connect_timeout > CONNECT_TIMEOUT:
                    logging.getLogger(__name__).error('No response to START \
                        from GasMixer in %d ms, disconnecting', CONNECT_TIMEOUT )
                    self._disconnect()
                else:
                    self.connect_timeout += UPDATE_INTERVAL
                    
        if self.state == State.STOPPING:
            socks = dict(self.sync_poller.poll(1))
            if self.syncclient in socks and socks[self.syncclient] == zmq.POLLIN:
                response = self.syncclient.recv()
                if response == 'STOP OK':
                    self.state = State.CONNECTED
                    self.connect_timeout = 0
            else:
                if self.connect_timeout > (2 * CONNECT_TIMEOUT):
                    logging.getLogger(__name__).error('No response to STOP \
                        from GasMixer in %d ms, disconnecting', 2 * CONNECT_TIMEOUT )
                    self._disconnect()
                else:
                    self.connect_timeout += UPDATE_INTERVAL
                                                            
    def __init__(self, **traits):
        super(GasMixerPanel, self).__init__(**traits)
        self.context = zmq.Context()

        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect('tcp://localhost:5561')
        self.subscriber.setsockopt(zmq.SUBSCRIBE, "")
        self.subscriber_poller = zmq.Poller()
        self.subscriber_poller.register(self.subscriber, zmq.POLLIN)
                
        self.timer = Timer(UPDATE_INTERVAL, self._onTimer)

    def _disconnect(self):
        logging.getLogger(__name__).info('_disconnect')
        self.sync_poller.unregister(self.syncclient)
        self.syncclient.close()
        self.button_label = 'Connect'
        self.state = State.DISCONNECTED
        self.connect_timeout = 0
        
    def _connect(self):
        logging.getLogger(__name__).info('_connect')
        if self.state == State.CONNECTING:
            return
        if self.state >= State.CONNECTED:
            self._disconnect()
        self.syncclient = self.context.socket(zmq.REQ)
        self.syncclient.connect('tcp://localhost:5562')
        self.sync_poller = zmq.Poller()
        self.sync_poller.register(self.syncclient, zmq.POLLIN)
        self.syncclient.send('CONNECT')
        self.state = State.CONNECTING         

    def _button_fired(self):
        self._connect()
        
    def _current_column_changed(self, old, new):
        self.current_column_int = new[1][self.y_units[0]]
    
    def _current_column_default(self):
        return ({self.x_units[0]:0},{self.y_units[0]:0})
            
    def start_stop(self, starting):
        if self.control_gasmixer:
            if not starting and self.state == State.RUNNING:
                self.syncclient.send('STOP')
                self.state = State.STOPPING         
            elif starting and self.state == State.CONNECTED:
                self.syncclient.send('START')
                self.state = State.STARTING         
                   
if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    g = GasMixerPanel()
    g.configure_traits()
    logging.shutdown()