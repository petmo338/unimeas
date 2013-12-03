from pyface.tasks.api import TraitsTaskPane, TraitsDockPane
from traits.api import Dict, Instance, List, Property, \
     Unicode, on_trait_change, Str, Int, HasTraits
from traitsui.api import EnumEditor, HGroup, Item, Label, View, UI

# Local imports.
from instruments.i_instrument import IInstrument
from plotter import Plotter

import logging
logger = logging.getLogger(__name__)

#class MeasureOverTimePane(TraitsTaskPane):
class MeasureOverTimePane(TraitsDockPane):
     
    plotter = Instance(Plotter)

    """ A TaskPane that displays a Traits UI View.
    """

    

    #### 'ITaskPane' interface ################################################

    id = 'sensorscience.unimeas.measure_over_time_pane'
    name = 'Measure over time pane'

    active_instrument = Instance(IInstrument)
    instruments = List(IInstrument)
    selected_unit = Int
    y_units = Property(depends_on='active_instrument.y_units')
    timebase = Int
    x_units = Property(depends_on='active_instrument.x_units')
        
    title = Property(Unicode, depends_on='active_instrument.name')

    x_label = Str
    y_label = Str
    
    view = View(HGroup(Label('Instrument: '), Item('active_instrument',
                            editor = EnumEditor(name='_enum_map'), \
                            enabled_when = 'not active_instrument.running'),
                            Label('Unit: '), Item('selected_unit',
                            editor = EnumEditor(name='_enum_map_unit')),
                            Label(' Timebase: '), Item('timebase',
                            editor = EnumEditor(name='x_units')),
                       show_labels=False),
#                 Item('plotter', dock='vertical', show_label=False, style='custom'),
                resizable = True)

    #### Private traits #######################################################

    _enum_map = Dict(IInstrument, Unicode)
    _enum_map_unit = Dict(Int, Unicode)

    def _plotter_default(self):
        return Plotter()

    ###########################################################################
    # Protected interface.
    ###########################################################################

    #### Trait property getters/setters #######################################

    def _get_title(self):
        return self.active_instrument.name if self.active_instrument else ''
        
    def _get_y_units(self):
        return self.active_instrument.y_units if self.active_instrument else {}

    def _get_x_units(self):
        return self.active_instrument.x_units if self.active_instrument else {}

    #### Trait change handlers ################################################

    def _title_changed(self, name, old, new):
        if hasattr(self.plotter.controller, 'time_plot'):
            self.plotter.controller.time_plot.title = self._get_title()
                
    @on_trait_change('instruments[]')
    def _update_instruments(self):        
        if self.active_instrument not in self.instruments:
            self.active_instrument = self.instruments[0] if self.instruments else None
        self._enum_map = dict((instrument, instrument.name) for instrument in self.instruments)

    @on_trait_change('y_units')
    def _update_y_units(self):
        self._enum_map_unit = dict((unit, self.y_units[unit]) for unit in self.y_units)
        self.selected_unit = 0

    @on_trait_change('x_units')
    def _update_x_units(self):
        self.timebase = 0
 
    @on_trait_change('selected_unit')        
    def update_selected_unit(self):
        self.plotter.set_y_unit(self.selected_unit)

    @on_trait_change('timebase')
    def update_timebase(self):
        self.plotter.set_x_unit(self.timebase)
