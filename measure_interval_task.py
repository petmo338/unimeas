from pyface.tasks.action.api import SMenu, SMenuBar, DockPaneToggleGroup, TaskToggleGroup
from pyface.tasks.api import Task, TaskLayout, Tabbed, PaneItem, Splitter, TraitsTaskPane
from traits.api import List, Instance, on_trait_change
from traitsui.api import View
from generic_pane import GenericPane
from instrument_help_pane import InstrumentHelpPane
from instrument_show_group import InstrumentShowGroup
from interval_plot_panel import IntervalPlotPanel
from instruments.i_instrument import IInstrument
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
                        SMenu(TaskToggleGroup(), id='Tasks', name='&Tasks'),
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
            from instruments.dummy_interval_instrument import DummyIntervalInstrument
        except ImportError as e:
            logger.warning('Unable to import DummyIntervalInstrument: %s', e)
            pass
        else:
            instruments.append(DummyIntervalInstrument())
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
        self.plot_panel.configure_plots(self.active_instrument)

    def _dispatch_data(self, data):
        for subscriber in self.data_subscribers:
            subscriber.add_data(data)

    def _start_stop(self):
        for subscriber in self.start_stop_subscribers:
            subscriber.start_stop(self.active_instrument.running)
