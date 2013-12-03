# Enthought library imports.
from pyface.tasks.api import TraitsDockPane
from traits.api import HasTraits, Instance
from traitsui.api import Item, View


class GenericPane(TraitsDockPane):
    """ A simple dock pane for editing instrument configuration
        options.
    """

    #### 'ITaskPane' interface ################################################

    id = 'sensorscience.unimeas.generic_pane'
    name = 'EMPTY! FIXME'

    #### 'InstrumentConfigPane' interface ##########################################

    panel = Instance(HasTraits)

    view = View(Item('panel',
                     style = 'custom',
                     show_label = False),
                resizable = True)
