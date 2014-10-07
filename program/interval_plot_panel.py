# -*- coding: utf-8 -*-
from qtgraph_editor import QTGraphWidgetEditor
from traits.api import HasTraits, Int, Str, Instance, Dict, Array, Button, Bool, on_trait_change
from traitsui.api import Item, View, EnumEditor, HGroup, Label
from instruments.i_instrument import IInstrument
import pyqtgraph as pg
import numpy as np
import logging
import copy
logger = logging.getLogger(__name__)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

COLOR_MAP =[(255, 63, 0), (0, 63, 255), (63, 255, 0), (255, 255, 63),\
            (255, 63, 255), (63, 255, 255), (160, 0, 0), (0, 0, 160),\
            (0, 160, 0), (0, 160, 160), (160, 160, 0), (160, 0, 160),\
            (255, 160, 160), (160, 160, 255), (160, 255, 160), (0, 0, 63)]

SI_ACR = { 'Frequency':'Hz', 'Capacitance':'F', 'Resistance':u"\u2126", 'Current':'A', 'Voltage':'V'}
class IntervalPlotPanel(HasTraits):
    pane_name = Str('Plot')
    pane_id = Str('sensorscience.unimeas.plot_pane')
    plot_widget = Instance(pg.PlotWidget)
    plots = Dict
    data = Array
    x_units = Dict
    y_units = Dict
    index = Int(0)
    plot_index = Int(0)
    selected_x_unit = Int(0)
    selected_y_unit = Int(0)
    clear_plots = Button
    keep_plots = Bool(False)
    plot_color = Int(0)
    channel_name = Str

    data = np.zeros(shape=(2, 100000), dtype=np.float32)


    instrument = Instance(IInstrument)
    traits_view = View(Item('plot_widget', editor = QTGraphWidgetEditor(), show_label = False),
                       HGroup(Label('y-unit: '), Item('selected_y_unit',
                            editor = EnumEditor(name='y_units'), show_label = False),
                            Item('keep_plots'), Item('clear_plots', show_label = False)))

    def _plot_widget_default(self):
        plot = pg.PlotWidget()
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen = ({'color' : '90909080', 'width': 1}))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen = ({'color' : '90909080', 'width': 1}))
        plot.addItem(self.vLine, ignoreBounds=True)
        plot.addItem(self.hLine, ignoreBounds=True)
        self.label = pg.TextItem(anchor = (1,1), color = 'r')
        plot.addItem(self.label)
        self.label.setPos(plot.getPlotItem().getViewBox().viewRect().right(), \
                plot.getPlotItem().getViewBox().viewRect().top())
        self.proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        plot.sigRangeChanged.connect(self.rangeChanged)
        plot.getViewBox().setAutoPan(x=False, y=False)
        return plot

    def rangeChanged(self, evt):
        self.label.setPos(self.plot_widget.getPlotItem().getViewBox().viewRect().right(), \
            self.plot_widget.getPlotItem().getViewBox().viewRect().top())

    def mouseMoved(self, evt):

        pos = evt[0]  ## using signal proxy turns original arguments into a tuple

        if self.plot_widget.sceneBoundingRect().contains(pos):
            mousePoint = self.plot_widget.getPlotItem().getViewBox().mapSceneToView(pos)
            self.label.setText("x=%0.3e,  y=%0.3e" % (mousePoint.x(), mousePoint.y()), color='k')
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def _clear_plots_fired(self):
        self.plots = {}
        self.plot_index = 0
        if self.plot_widget is not None:
            self.plot_widget.clearPlots()
            legendNames = [l.text for a,l in self.legend.items]
            for name in legendNames:
                self.legend.removeItem(name)

    def configure_plots(self, instrument):

        if not hasattr(self, 'legend'):
            self.legend = self.plot_widget.getPlotItem().addLegend()
        legendNames = [l.text for a,l in self.legend.items]
        for name in legendNames:
            self.legend.removeItem(name)

        self.plot_widget.enableAutoRange(True, True)
        self.plot_widget.clearPlots()
        self._clear_plots_fired()
        self.x_units = instrument.x_units
        self.y_units = instrument.y_units
        try:
            channel_index = instrument.enabled_channels.index(True)
        except ValueError:
            logger.warning('Enabled channels: %s on instrument: %s', instrument.enabled_channels, instrument)
            return
        self.plot_widget.setLabel('bottom', self.x_units[0], units = SI_ACR.get(self.x_units[0], 0))
        self.channel_name = instrument.output_channels[channel_index]
        self._selected_y_unit_changed(0)

    def _selected_y_unit_changed(self, unit):
        self.plot_widget.setLabel('left', self.y_units[unit], units = SI_ACR.get(self.y_units[unit], unit))
        self.clear_plots = True

    def _x_units_changed(self):
        pass

    def _y_units_changed(self):
        self.selected_y_unit = 0

    def _y_units_default(self):
        return {0: 'None'}

    def start_stop(self, instrument):
        if instrument.running is True:
            if not self.keep_plots:
                self._clear_plots_fired()
                self.plot_index = 0
            self.plots[self.plot_index] = pg.PlotCurveItem(
                pen = ({'color':COLOR_MAP[self.plot_index % len(COLOR_MAP)], 'width':1}),
                name=instrument.measurement_info.get('name', str(self.plot_index)))
            self.plot_widget.addItem(self.plots[self.plot_index])
            self.index = 0
        else:
            if self.index > 0:
                self.plots[self.plot_index].updateData(copy.deepcopy(self.data[0][:self.index]),
                                                copy.deepcopy(self.data[1][:self.index]))
            self.plot_index += 1

    def add_data(self, data):
        self.index += 1
        channel_data_x = data[self.channel_name][0]
        channel_data_y = data[self.channel_name][1]
        self.data[0][self.index - 1] = channel_data_x.values()[0]
        self.data[1][self.index - 1] = channel_data_y.values()[self.selected_y_unit]
        self.plots[self.plot_index].updateData(self.data[0][:self.index],
                                            self.data[1][:self.index])


if __name__ == '__main__':
    p = IntervalPlotPanel()
    p.configure_traits()
