# -*- coding: utf-8 -*-
from qtgraph_editor import QTGraphWidgetEditor
from traits.api import HasTraits, Int, Str, Instance, Dict, Array
from traitsui.api import Item, View, EnumEditor, HGroup, Label
from instruments.i_instrument import IInstrument
import pyqtgraph as pg
import numpy as np
import logging

logger = logging.getLogger(__name__)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

DATA_LINES = 172800
COLOR_MAP = [(255, 63, 0), (0, 63, 255), (63, 255, 0), (255, 255, 63), \
             (255, 63, 255), (63, 255, 255), (160, 0, 0), (0, 0, 160), \
             (0, 160, 0), (0, 160, 160), (160, 160, 0), (160, 0, 160), \
             (255, 160, 160), (160, 160, 255), (160, 255, 160), (0, 0, 63)]

SI_ACR = {'Voltage': 'V', 'Current': 'A', 'Resistance': u"\u2126", 'Time': 's',
          'SampleNumber': '', 'Capacitance': 'F', 'Frequency': 'Hz', 'BIAS': 'V', 'Temperature': u'\u00B0C',
          'Percent': '%'}


class PlotPanel(HasTraits):
    pane_name = Str('Plot')
    pane_id = Str('sensorscience.unimeas.plot_pane')
    plot_widget = Instance(pg.PlotWidget)
    plots = Dict
    data = Array
    x_units = Dict
    y_units = Dict
    index = Int(0)
    selected_x_unit = Int(0)
    selected_y_unit = Int(0)
    plot_size = Int(DATA_LINES)
    plot_increment = Int
    legend = Instance(pg.LegendItem)

    instrument = Instance(IInstrument)
    traits_view = View(Item('plot_widget', editor=QTGraphWidgetEditor(), show_label=False),
                       HGroup(Label('y-unit: '), Item('selected_y_unit',
                                                      editor=EnumEditor(name='y_units'), show_label=False),
                              Label('x-unit: '), Item('selected_x_unit',
                                                      editor=EnumEditor(name='x_units'), show_label=False)))

    def _plot_widget_default(self):
        plot = pg.PlotWidget()
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=({'color': '90909080', 'width': 1}))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=({'color': '90909080', 'width': 1}))
        plot.addItem(self.vLine, ignoreBounds=True)
        plot.addItem(self.hLine, ignoreBounds=True)
        self.label = pg.TextItem(anchor=(1, 1))
        plot.addItem(self.label)
        self.label.setPos(plot.getPlotItem().getViewBox().viewRect().right(), \
                          plot.getPlotItem().getViewBox().viewRect().top())
        self.proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved)
        plot.sigRangeChanged.connect(self.range_changed)
        return plot

    def range_changed(self, evt):

        self.label.setPos(self.plot_widget.getPlotItem().getViewBox().viewRect().right(), \
                          self.plot_widget.getPlotItem().getViewBox().viewRect().top())

    def mouse_moved(self, evt):

        pos = evt[0]  ## using signal proxy turns original arguments into a tuple

        if self.plot_widget.sceneBoundingRect().contains(pos):
            mousePoint = self.plot_widget.getPlotItem().getViewBox().mapSceneToView(pos)
            self.label.setText("x=%0.3e,  y=%0.3e" % (mousePoint.x(), mousePoint.y()), color='k')
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def update_visible_plots(self):
        if not hasattr(self.instrument, 'enabled_channels'):
            return
        self.plot_widget.clearPlots()
        for name in [l.text for a, l in self.legend.items]:
            self.legend.removeItem(name)
        for i in range(len(self.instrument.enabled_channels)):
            if self.instrument.enabled_channels[i]:
                self.plot_widget.addItem(self.plots[self.instrument.output_channels[i]])

    def configure_plots(self, instrument):
        self.instrument = instrument
        if self.legend is None:
            self.legend = self.plot_widget.getPlotItem().addLegend()
        for name in [l.text for a, l in self.legend.items]:
            self.legend.removeItem(name)

        self.plot_widget.enableAutoRange(True, True)

        self.plots = {}
        self.data = np.zeros(
            shape=(len(instrument.output_channels) * (len(instrument.x_units) + len(instrument.y_units)), DATA_LINES),
            dtype=np.float32)
        for i in range(len(instrument.output_channels)):
            self.plots[instrument.output_channels[i]] = pg.PlotCurveItem(x=[0], y=[0],
                                                                         pen=({'color': COLOR_MAP[i], 'width': 1}),
                                                                         name=instrument.output_channels[i])
        self.plot_increment = len(instrument.x_units) + len(instrument.y_units)
        self.x_units = instrument.x_units
        self.y_units = instrument.y_units
        self.update_visible_plots()

    def _selected_x_unit_changed(self, unit):
        self.plot_widget.setLabel('bottom', self.x_units[unit], units=SI_ACR.get(self.x_units[unit], unit))
        self.selected_x_unit = unit
        for channel in self.plots.keys():
            self.plots[channel].viewTransformChanged()

    def _selected_y_unit_changed(self, unit):
        self.plot_widget.setLabel('left', self.y_units[unit], units=SI_ACR.get(self.y_units[unit], unit))
        self.selected_y_unit = unit
        for channel in self.plots.keys():
            self.plots[channel].viewTransformChanged()

    def _x_units_changed(self):
        self._selected_x_unit_changed(0)

    def _y_units_changed(self):
        self._selected_y_unit_changed(0)

    def start_stop(self, starting):
        logger.info('start_stop')
        if starting is True:
            self.index = 0

    def add_data(self, data):
        #        logger.info('add_data %s', data)
        if self.index >= self.plot_size:
            lines = np.shape(self.data)[0]
            self.data = np.concatenate((self.data, np.zeros(shape=(lines,
                                                                   DATA_LINES), dtype=np.float32)), axis=1)
            self.plot_size = self.plot_size + DATA_LINES

        #        self.controller.plotting_allowed = False
        rows_inc = 0
        #        self.plot_widget.enableAutoRange(False, False)
        #        logging.getLogger(__name__).info('plots.keys: %s', self.controller.time_plot.plots.keys())

        for channel in self.plots.keys():

            channel_data = data[channel]
            channel_data_x = channel_data[0]
            channel_data_y = channel_data[1]
            for key in self.x_units:
                self.data[key + rows_inc][self.index] = channel_data_x[self.x_units[key]]
            for key in self.y_units:
                #                try:
                self.data[key + len(channel_data_x) + rows_inc][self.index] = channel_data_y[self.y_units[key]]
            # except KeyError:
            #    self.controller.time_plot.plots[channel][0].visible = False
            # else:
            #    self.controller.time_plot.plots[channel][0].visible = True
            self.plots[channel].setData(x=self.data[rows_inc + self.selected_x_unit][:self.index],
                                        y=self.data[rows_inc + len(channel_data_x) + self.selected_y_unit][:self.index])
            rows_inc += self.plot_increment

        #        self.controller.data[rows_inc][self.controller.index] = data['gasmixer'][1].values()[0]
        self.index += 1


# self.plot_widget.autoRange()
#        self.updatePlot()
#        self.controller.data_updated = True
#        self.controller.plotting_allowed = True
#        logging.getLogger(__name__).info('controller.data %s', self.controller.data)
#
#    def updatePlot(self):
#        for key, value in self.plots.items():
#            if value.opts['name'] == key:
#                value.setData(x=
#

if __name__ == '__main__':
    p = PlotPanel()
    p.configure_traits()
