# -*- coding: utf-8 -*-
import logging
from enthought.traits.api import HasTraits, Range, implements, \
    Unicode, Int, Dict, Event, Bool, List
from enthought.traits.ui.api import View, Item, Group

from i_instrument import IInstrument

class Blank(HasTraits):
    """Empty instrument"""

    implements(IInstrument)

    some_parameter = Range(-10.0, 10.0, 3.1)

    parameter_group = Group(
        Item('some_parameter'),
        Item('start_stop', label = 'Start/Stop Acqusistion'),
        show_border = True)

    traits_view = View(parameter_group)

    def __init__(self):
        self.logger = logging.getLogger('Blank')

    def _enabled_channels_default(self):
        return [True] * 1

    #### 'IInstrument' interface #############################################
    name = Unicode('Blank instrument')

    acquired_data = List(Dict)

    y_units = Dict({0: 'Apor', 1: 'Rumpor', 2: 'loppor'})
    x_units = Dict({0:'SampleNumber', 1:'Time'})

    start_stop = Event
    running = Bool
    output_channels = Dict({0: 'ch0'})
    enabled_channels = List(Bool)

    def start(self):
        self.logger.info('Blank start()')

    def stop(self):
        self.logger.info('Blank stop()')

    def _enabled_channels_default(self):
        return [True]
