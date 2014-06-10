from pyface.tasks.action.api import SMenu, SMenuBar, DockPaneToggleGroup, TaskToggleGroup
from pyface.tasks.api import Task, TaskLayout, Tabbed, PaneItem, Splitter, TraitsTaskPane
from traits.api import List, Instance, on_trait_change
from traitsui.api import View
from generic_pane import GenericPane
from instrument_help_pane import InstrumentHelpPane
from instruments.i_instrument import IInstrument
from sql_panel import SQLPanel
from gasmixer_panel import GasMixerPanel
from gpio_panel import GPIOPanel
from plot_panel import PlotPanel
from temperature_control_panel import TemperatureControlPanel
from instrument_show_group import InstrumentShowGroup
#import pdb
import logging

logger = logging.getLogger(__name__)

class EmptyCentralPane(TraitsTaskPane):
    id = 'sensorscience.unimeas.empty_central_pane'
    name = 'Empty central pane'
    traits_view = View(resizable = False, width = 5)

class MeasureOverTimeTask(Task):
    """ A task for measure something over time.
    """

    #### 'Task' interface #####################################################

    id = 'sensorscience.unimeas.measureovertime'
    name = 'Measure over time'

    menu_bar = SMenuBar(SMenu(id='File', name='&File'),
                        SMenu(id='Edit', name='&Edit'),
                        SMenu(TaskToggleGroup(), id='Tasks', name='&Measurement type'),
                        SMenu(DockPaneToggleGroup(),  id='Measurement', name='&Panels'),
                        SMenu(InstrumentShowGroup(), id='Instrument', name='&Instrument'))

    active_instrument = Instance(IInstrument)
    sql_panel = Instance(SQLPanel)
    gasmixer_panel = Instance(GasMixerPanel)
    gpio_panel = Instance(GPIOPanel)
    plot_panel = Instance(PlotPanel)
    temperature_control_panel = Instance(TemperatureControlPanel)
    pane = Instance(EmptyCentralPane)
    instruments = List
    panels = List
    data_units = List

    start_stop_subscribers = List
    data_subscribers = List
    data_suppliers = List

    ###########################################################################
    # 'Task' interface.
    ###########################################################################

    def create_central_pane(self):
        """ Create a plot pane with a list of instruments. Keep track of which
            instrument is active so that dock panes can introspect it.
        """
        return EmptyCentralPane()

    def create_dock_panes(self):
        self.active_instrument = self.instruments[0]
        return [ GenericPane(panel=self.active_instrument,
                                id = 'sensorscience.unimeas.instrument_config_pane',
                                name = 'Instrument configuration'),
                 InstrumentHelpPane(instrument=self.active_instrument),
                 GenericPane(panel=self.panels[0],
                                id = self.panels[0].pane_id,
                                name = self.panels[0].pane_name),
                 GenericPane(panel=self.panels[1],
                                id = self.panels[1].pane_id,
                                name = self.panels[1].pane_name),
                 GenericPane(panel=self.panels[2],
                                id = self.panels[2].pane_id,
                                name = self.panels[2].pane_name),
                 GenericPane(panel=self.panels[3],
                                id = self.panels[3].pane_id,
                                name = self.panels[3].pane_name),
                GenericPane(panel=self.panels[4],
                                id = self.panels[4].pane_id,
                                name = self.panels[4].pane_name),                 ]

    def activated(self):
        self._update_active_instrument(None, None, None, None)

    def set_active_instrument(self, instrument):
        self.active_instrument = instrument

    #### Trait initializers ###################################################

    def _default_layout_default(self):
        return TaskLayout(
            left=Splitter(Tabbed(PaneItem('sensorscience.unimeas.instrument_config_pane'),
                        PaneItem('sensorscience.unimeas.instrument_help_pane')),
                        PaneItem(self.panels[0].pane_id),
                        PaneItem(self.panels[1].pane_id),
                        orientation = 'vertical'),
            right=PaneItem('sensorscience.unimeas.plot_pane')
            )

    def _instruments_default(self):
        instruments = []
        try:
            from instruments.blank import Blank
        except ImportError:
            pass 
        else:
            instruments.append(Blank())

        try:
            from instruments.dummysourcemetertime import DummySourcemeterTime
        except ImportError:
            pass
        else:
            instruments.append(DummySourcemeterTime())
        
        try:
            from instruments.sourcemeter import SourceMeter
        except ImportError:
            pass
        #except WindowsError:
        #    pass
        else:
            instruments.append(SourceMeter())

        try:
            from instruments.ni6215 import NI6215
        except ImportError:
            pass
        else:
            instruments.append(NI6215())

        try:
            from instruments.SB50_moslab import NI6215_MOSLab
        except ImportError:
            pass
        else:
            instruments.append(NI6215_MOSLab())

        try:
            from instruments.time_boonton7200 import Boonton7200
        except ImportError:
            pass
        #except WindowsError:
        #    pass
        else:
            instruments.append(Boonton7200())
            
        try:
            from instruments.time_agilent_4284 import Agilent4284
        except ImportError:
            pass
        #except WindowsError:
        #    pass
        else:
            instruments.append(Agilent4284())

        return instruments

    def _panels_default(self):
        self.sql_panel = SQLPanel()
        self.gasmixer_panel = GasMixerPanel()
        self.gpio_panel = GPIOPanel()
        self.plot_panel = PlotPanel()
        self.temperature_control_panel = TemperatureControlPanel()
        self.data_subscribers.append(self.sql_panel)
        self.data_subscribers.append(self.gpio_panel)
        self.data_subscribers.append(self.plot_panel)
        self.data_suppliers.append(self.gasmixer_panel)
        self.data_suppliers.append(self.temperature_control_panel)        
        self.start_stop_subscribers.append(self.sql_panel)
        self.start_stop_subscribers.append(self.gasmixer_panel)
        self.start_stop_subscribers.append(self.gpio_panel)
        self.start_stop_subscribers.append(self.plot_panel)
        self.start_stop_subscribers.append(self.temperature_control_panel) 
        return [self.sql_panel,
                self.gasmixer_panel,
                self.gpio_panel,
                self.plot_panel,
                self.temperature_control_panel]

    #### Trait change handlers ################################################

    @on_trait_change('active_instrument')
    def _update_active_instrument(self, obj, name, old, new):
        #try:
        #    self.data_suppliers.remove(old)
        #except ValueError:
        #    pass
        #self.data_suppliers.append(new)
        self.on_trait_change(self._dispatch_data, 'active_instrument.acquired_data[]')
        self.on_trait_change(self._start_stop, 'active_instrument.start_stop')
        self.on_trait_change(self.plot_panel.update_visible_plots, 'active_instrument.enabled_channels[]')
        self.configure_new_instrument()
        self.plot_panel.configure_plots(self.active_instrument)
        self.gpio_panel.active_instrument = self.active_instrument
        for dock_pane in self.window.dock_panes:
            if dock_pane.id.find('instrument_config_pane') != -1:
                dock_pane.panel = self.active_instrument

    def configure_new_instrument(self):
        self.data_units = []
        for i in xrange(len(self.active_instrument.output_channels)):
            for x_unit in self.active_instrument.x_units.values():
                self.data_units.append(self.active_instrument.output_channels[i] + x_unit)
            for y_unit in self.active_instrument.y_units.values():
                self.data_units.append(self.active_instrument.output_channels[i] + y_unit)
        self.data_units.append(self.gasmixer_panel.output_channels[0] + \
        self.gasmixer_panel.y_units.values()[0])
        self.sql_panel.set_column_names(self.data_units)

    @on_trait_change('active_instrument.start_stop')
    def _start_stop(self):
        logger.info('otc, active_instrument.start_stop')
        for subscriber in self.start_stop_subscribers:
            subscriber.start_stop(self.active_instrument.running)

    def _dispatch_data(self):
        while len(self.active_instrument.acquired_data) > 0:
            data = self.active_instrument.acquired_data.pop(0).copy()
            for supplier in self.data_suppliers:
                data[supplier.output_channels[0]] = supplier.get_data()
#            data['gasmixer'] = self.gasmixer_panel.current_column
            for subscriber in self.data_subscribers:
                subscriber.add_data(data)
