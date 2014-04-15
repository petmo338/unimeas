# -*- coding: utf-8 -*-
import logging
from traits.api import HasTraits, Range, \
    Unicode, Dict, Event, Bool, List
from traitsui.api import View, Item, Group, Label

from i_instrument import IInstrument

INFO_STRING = """
    First, select type of measurement (something over time or sweep type).
    Then, select the instrument you intend to use.
    """

#@provides(IInstrument)
class Blank(HasTraits):
    """Empty instrument"""

    some_parameter = Range(-10.0, 10.0, 3.1)

    parameter_group = Group(
        Item('some_parameter'),
        Item('start_stop', label = 'Start/Stop Acqusistion'),
        show_border = True)

    traits_view = View(Label(INFO_STRING))

    def __init__(self):
        self.logger = logging.getLogger('Blank')

    #### 'IInstrument' interface #############################################
    name = Unicode('Blank instrument')

    acquired_data = List(Dict)

    y_units = Dict({0: 'None'})
    x_units = Dict({0:'None'})
    measurement_info = Dict()
    start_stop = Event
    running = Bool
    output_channels = Dict({0: 'none'})
    enabled_channels = List(Bool)

    def start(self):
        self.logger.info('Blank start()')

    def stop(self):
        self.logger.info('Blank stop()')

    def _enabled_channels_default(self):
        return [False]

if __name__ is '__main__':

    b = Blank().configure_traits()
