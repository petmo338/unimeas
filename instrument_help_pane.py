# Standard library imports.
import codecs
import os.path

# Enthought library imports.
from pyface.tasks.api import TraitsDockPane
from traits.api import HasTraits, Instance, Property, Unicode, \
     cached_property
from traitsui.api import HTMLEditor, Item, View

# Constants.
HELP_PATH = os.path.join(os.path.dirname(__file__), 'help')


class InstrumentHelpPane(TraitsDockPane):
    """ A dock pane for viewing any help associated with an instrument.
    """

    #### 'ITaskPane' interface ################################################

    id = 'sensorscience.unimeas.instrument_help_pane'
    name = 'Instrument Information'

    #### 'MeasurementConfigPane' interface ##########################################

    instrument = Instance(HasTraits)

    html = Property(Unicode, depends_on='instrument')

    view = View(Item('html',
                     editor = HTMLEditor(base_url=HELP_PATH,
                                         open_externally=True),
                     show_label = False),
                width = 300,
                resizable = True)

    ###########################################################################
    # Protected interface.
    ###########################################################################

    @cached_property
    def _get_html(self):
        """ Fetch the help HTML for the current instrument.
        """
        if self.instrument is None:
            return 'No instrument selected.'

        # Determine the name of the model.
        instrument = self.instrument
        while hasattr(instrument, 'adaptee'):
            instrument = instrument.adaptee
        name = instrument.__class__.__name__.lower()

        # Load HTML file, if possible.
        path = os.path.join(HELP_PATH, name + '.html')
        if os.path.isfile(path):
            with codecs.open(path, 'r', 'utf-8') as f:
                return f.read()
        else:
            return 'No information available for instrument.'

