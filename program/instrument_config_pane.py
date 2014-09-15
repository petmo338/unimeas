# Enthought library imports.
from pyface.tasks.api import TraitsDockPane
from traits.api import HasTraits, Instance
from traitsui.api import Item, View


class InstrumentConfigPane(TraitsDockPane):
    """ A simple dock pane for editing instrument configuration
        options.
    """

    #### 'ITaskPane' interface ################################################

    id = 'sensorscience.unimeas.instrument_config_pane'
    name = 'Instrument Configuration'

    #### 'InstrumentConfigPane' interface ##########################################

    instrument = Instance(HasTraits)

    view = View(Item('instrument',
                     style = 'custom',
                     show_label = False),
                resizable = True)
