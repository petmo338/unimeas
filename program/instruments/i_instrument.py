# Enthought library imports.
from traits.api import Interface, Unicode, Dict, Int, Event, Bool, List

class IInstrument(Interface):

    # The user-visible name of the instrument.
    name = Unicode
    measurement_info = Dict()
    x_units = Dict
    y_units = Dict

    acquired_data = List(Dict)
    
    start_stop = Event
    running = Bool
    
    output_channels = Dict
    """ Must not have overlapping names \ 
        i.e. ai1, ai12, ai13 will generate error """

    enabled_channels = List(Bool)
    
    def start(self):
        """ Start the measurement """
        raise NotImplementedError("Subclasses should implement this!")
        
    def stop(self):
        """ Stop the measurement """
        raise NotImplementedError("Subclasses should implement this!")
    