from pyface.tasks.action.api import SMenu, SMenuBar, DockPaneToggleGroup, TaskToggleGroup
from pyface.tasks.api import Task, TaskLayout, Tabbed, PaneItem, Splitter, TraitsTaskPane
from traits.api import List, Instance, on_trait_change
from traitsui.api import View
from . generic_pane import GenericPane
from . instrument_help_pane import InstrumentHelpPane
from . instrument_show_group import InstrumentShowGroup
from . interval_plot_panel import IntervalPlotPanel
from . instruments.i_instrument import IInstrument
import logging
logger = logging.getLogger(__name__)

class EmptyCentralPane(TraitsTaskPane):
    id = 'sensorscience.unimeas.empty_central_pane'
    name = 'Empty central pane'
    traits_view = View(resizable = False, width = 5)

class MeasureIntervalTask(Task):
    """A Task for measuring over an interval. Voltage ramp, frequency interval etc..
    """
    id = 'sensorscience.unimeas.measureinterval'
    name = 'Measure interval/ramp'

    instruments = List
    panels = List
    start_stop_subscribers = List
    data_subscribers = List
    plot_panel = Instance(IntervalPlotPanel)
    active_instrument = Instance(IInstrument)

    menu_bar = SMenuBar(SMenu(id='File', name='&File'),
                        SMenu(id='Edit', name='&Edit'),
                        SMenu(TaskToggleGroup(), id='Tasks', name='&Measurement type'),
                        SMenu(DockPaneToggleGroup(),  id='Measurement', name='&Panels'),
                        SMenu(InstrumentShowGroup(), id='Instrument', name='&Instrument'))


    def create_central_pane(self):
        """ Create a plot pane with a list of instruments. Keep track of which
            instrument is active so that dock panes can introspect it.
        """
        return EmptyCentralPane()

    def create_dock_panes(self):
        return [ GenericPane(panel=self.active_instrument,
                                id = 'sensorscience.unimeas.instrument_config_pane',
                                name = 'Instrument configuration'),
                 InstrumentHelpPane(instrument=self.active_instrument),
                 GenericPane(panel=self.panels[0],
                                id = self.panels[0].pane_id,
                                name = self.panels[0].pane_name)]

    def initialized(self):
        self.update_active_instrument(self, 'from_init', None, self.active_instrument)

    def set_active_instrument(self, instrument):
        self.active_instrument = instrument

    def _default_layout_default(self):
        return TaskLayout(
            left=Splitter(Tabbed(PaneItem('sensorscience.unimeas.instrument_config_pane'),
                        PaneItem('sensorscience.unimeas.instrument_help_pane')),
                        PaneItem(self.panels[0].pane_id),
#                        PaneItem(self.panels[1].pane_id),
                        orientation = 'vertical'),
            right=PaneItem('sensorscience.unimeas.interval_plot_pane')
            )

    def _instruments_default(self):
        instruments = []
        try:
            from . instruments.blank import Blank
        except ImportError:
            pass
        else:
            instruments.append(Blank())
        
        try:
            from . instruments.dummy_interval_instrument import DummyIntervalInstrument
        except ImportError as e:
            logger.warning('Unable to import DummyIntervalInstrument: %s', e)
            pass
        else:
            instruments.append(DummyIntervalInstrument())
        try:
            from . instruments.agilent_4284 import Agilent4284
        except ImportError as e:
            logger.warning('Unable to import: %s', e)
            pass
        else:
            instruments.append(Agilent4284())
        try:
            from . instruments.interval_sourcemeter import SourceMeter
        except ImportError as e:
            logger.warning('Unable to import: %s', e)
            pass
        else:
            instruments.append(SourceMeter())
        try:
            from . instruments.interval_ni6215 import NI6215
        except ImportError as e:
            logger.warning('Unable to import: %s', e)
            pass
        else:
            instruments.append(NI6215())
        return instruments

    def _active_instrument_default(self):
        if self.instruments is not None:
            return self.instruments[0]
        else:
            return None

    def _panels_default(self):
        panels = []
        self.plot_panel = IntervalPlotPanel()
        panels.append(self.plot_panel)
        self.start_stop_subscribers.append(self.plot_panel)
        self.data_subscribers.append(self.plot_panel)
        return panels

    @on_trait_change('active_instrument')
    def update_active_instrument(self, obj, name, old, new):
        self.on_trait_change(self._dispatch_data, 'active_instrument.acquired_data[]')
        self.on_trait_change(self._start_stop, 'active_instrument.start_stop')
        self.on_trait_change(self._configure_plots, 'active_instrument.enabled_channels[]')
        self.plot_panel.configure_plots(self.active_instrument)
        for dock_pane in self.window.dock_panes:
            if dock_pane.id.find('instrument_config_pane') != -1:
                dock_pane.panel = self.active_instrument

    def _dispatch_data(self):
         while len(self.active_instrument.acquired_data) > 0:
            data = self.active_instrument.acquired_data.pop(0).copy()
            for subscriber in self.data_subscribers:
                subscriber.add_data(data)

    def _configure_plots(self):
        self.plot_panel.configure_plots(self.active_instrument)

    def _start_stop(self):
        if not self.active_instrument.running:
            self._dispatch_data()
        for subscriber in self.start_stop_subscribers:
            subscriber.start_stop(self.active_instrument)
