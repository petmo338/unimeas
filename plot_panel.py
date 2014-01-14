# -*- coding: utf-8 -*-
from qtgraph_editor import QTGraphWidgetEditor
from traits.api import HasTraits, Int, Str, Instance, Dict, Array
from traitsui.api import Item, View, EnumEditor, HGroup, Label
from instruments.i_instrument import IInstrument
import pyqtgraph as pg
import numpy as np
import logging
logger = logging.getLogger(__name__)

DATA_LINES = 172800
COLOR_MAP = ['FFA0FFFF', 'FF8080FF', 'FF40FFFF', 'FF0080FF',\
            '00FFFFFF','00FF90FF','00FF40FF','00FF00FF',\
            'A0FFFFFF','80FFFFFF','40FFFFFF','00FFFFFF',\
            '0000FFFF','0000A0FF','800080FF','A00040FF',]

SI_ACR = { 'Voltage':'V', 'Current':'A', 'Resistance':u"\u2126", 'Time':'s', 'SampleNumber':''}
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

    instrument = Instance(IInstrument)
    traits_view = View(Item('plot_widget', editor = QTGraphWidgetEditor(), show_label = False),
                       HGroup(Label('y-unit: '), Item('selected_y_unit',
                            editor = EnumEditor(name='y_units'), show_label = False),
                            Label('x-unit: '), Item('selected_x_unit',
                            editor = EnumEditor(name='x_units'), show_label = False)))

    def _plot_widget_default(self):
        plot = pg.PlotWidget()
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen = ({'color' : '80808080', 'width': 1}))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen = ({'color' : '80808080', 'width': 1}))
        plot.addItem(self.vLine, ignoreBounds=True)
        plot.addItem(self.hLine, ignoreBounds=True)
        self.label = pg.TextItem(anchor = (1,1))
        plot.addItem(self.label)
        self.label.setPos(plot.getPlotItem().getViewBox().viewRect().right(), \
                plot.getPlotItem().getViewBox().viewRect().top())


#        logger.info('_plot_default')

        self.proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        plot.sigRangeChanged.connect(self.rangeChanged)
        return plot

    def rangeChanged(self, evt):
#        logger.info('rangeChanged x %f, y: %f', self.plot_widget.getPlotItem().getViewBox().viewRect().right(),\
#            self.plot_widget.getPlotItem().getViewBox().viewRect().top())

        self.label.setPos(self.plot_widget.getPlotItem().getViewBox().viewRect().right(), \
            self.plot_widget.getPlotItem().getViewBox().viewRect().top())


    def mouseMoved(self, evt):

        pos = evt[0]  ## using signal proxy turns original arguments into a tuple

        if self.plot_widget.sceneBoundingRect().contains(pos):
            mousePoint = self.plot_widget.getPlotItem().getViewBox().mapSceneToView(pos)
#            logger.info(mousePoint)
            self.label.setText("x=%0.3f,  y=%0.3f" % (mousePoint.x(), mousePoint.y()))
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def update_visible_plots(self, instrument, name, old, new):
        if not hasattr(instrument, 'enabled_channels'):
            return
#        logger.info('otc update_visible_plots')

        self.plot_widget.clearPlots()
#        for plot in self.plots:
#            self.plot_widget.removeItem(plot)
#        for i in xrange(len(instrument.enabled_channels)):
#            self.plot_widget.removeItem(self.plots[instrument.output_channels[i]])
#            logger.info('%s', self.plot_widget.getPlotItem().legend.items)
#            self.plot_widget.getPlotItem().legend.removeItem(instrument.output_channels[i])
        legendNames = [l.text for a,l in self.legend.items]
 #       logger.info('legendNames: %s', legendNames)
        for name in legendNames:
            self.legend.removeItem(name)
#        for sample, label in self.legend.items:
#            logger.info('label.text %s', label.text)
#            self.legend.removeItem(label.text)
#        logger.info('items: %s', self.legend.items)
        for i in xrange(len(instrument.enabled_channels)):
            if instrument.enabled_channels[i] == True:
                self.plot_widget.addItem(self.plots[instrument.output_channels[i]])
#                self.legend.addItem(self.plots[instrument.output_channels[i]],
#                    instrument.output_channels[i])


    def configure_plots(self, instrument):
        if not hasattr(self, 'legend'):
            self.legend = self.plot_widget.getPlotItem().addLegend()
        legendNames = [l.text for a,l in self.legend.items]
        for name in legendNames:
            self.legend.removeItem(name)
#        logger.info('configure_plots, legend: %s', self.legend.items)
        #plotnames = self.controller.time_plot.plots.keys()
        #for plot in plotnames:
        #    self.controller.time_plot.delplot(plot)
        #for data in [n for n in self.controller.time_data.list_data() if not n.startswith('index')]:
        #    self.controller.time_data.del_data(data)


        self.plot_widget.enableAutoRange(True, True)

        self.plots = {}
        self.data = np.zeros(shape=(len(instrument.output_channels) * (len(instrument.x_units) + len(instrument.y_units)), DATA_LINES), dtype=np.float32)
        for i in xrange(len(instrument.output_channels)):
            self.plots[instrument.output_channels[i]] = pg.PlotCurveItem(x=[0], y=[0],
                pen = COLOR_MAP[i], name=instrument.output_channels[i])
            #if instrument.enabled_channels[i] == True:
            #    self.plot_widget.addItem(self.plots[instrument.output_channels[i]])


        #self.controller.data = array(zeros((len(data_units), MAX_PLOT_LENGTH), dtype=float32))
        self.plot_increment = len(instrument.x_units) + len(instrument.y_units)
        #self.controller.number_of_x_units = len(x_units)
        self.x_units = instrument.x_units
        self.y_units = instrument.y_units
        self.update_visible_plots(instrument, False, False, False)



    def _selected_x_unit_changed(self, unit):
        self.plot_widget.setLabel('bottom', self.x_units[unit], units = SI_ACR.get(self.x_units[unit], unit))
        self.selected_x_unit = unit

    def _selected_y_unit_changed(self, unit):
        self.plot_widget.setLabel('left', self.y_units[unit], units = SI_ACR.get(self.y_units[unit], unit))
        self.selected_y_unit = unit

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
                #except KeyError:
                #    self.controller.time_plot.plots[channel][0].visible = False
                #else:
                #    self.controller.time_plot.plots[channel][0].visible = True
            self.plots[channel].setData(x=self.data[rows_inc + self.selected_x_unit][:self.index],\
                                        y=self.data[rows_inc + len(channel_data_x) + self.selected_y_unit][:self.index])
            rows_inc += self.plot_increment

#        self.controller.data[rows_inc][self.controller.index] = data['gasmixer'][1].values()[0]
        self.index += 1
#        self.plot_widget.autoRange()
#        self.updatePlot()
#        self.controller.data_updated = True
#        self.controller.plotting_allowed = True
##        logging.getLogger(__name__).info('controller.data %s', self.controller.data)
#
#    def updatePlot(self):
#        for key, value in self.plots.items():
#            if value.opts['name'] == key:
#                value.setData(x=
#

if __name__ == '__main__':
    p = PlotPanel()
    p.configure_traits()
