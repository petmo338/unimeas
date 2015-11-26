#from pyface.qt import QtGui, QtCore
from pyqtgraph.Qt import QtGui, QtCore
#from traits.etsconfig.api import ETSConfig
#ETSConfig.toolkit = 'qt4'

#import matplotlib as mpl
#import matplotlib
#mpl.rcParams['backend.qt4']='PySide'

# We want matplotlib to use a QT backend
#mpl.use('Qt4Agg')
#from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.figure import Figure
#from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea
from traits.api import Any, Instance, Array, Int
from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory
from traitsui.api import Handler

import logging
logger = logging.getLogger(__name__)

class _QTGraphWidgetEditor(Editor):

    def init(self, parent):
        logger.info(self.value)
        self.control = self._create_widget(parent)
        self.set_tooltip()
#        self.logger = logging.getLogger('MPLFigureEditor')

    def update_editor(self):
        pass
    
    def _create_widget(self, parent):
        """ Create the widget. """
        frame = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()        
        pw = self.value        
        vbox.addWidget(pw)
        frame.setLayout(vbox)
   
        return frame
        
    #def wheelEvent(self, event):
    #    self.mouse_delta = event.delta()
    #    self.mouse_x = event.x()
    #    self.mouse_y = event.y()
               
    def set_size_policy(self, direction, resizable, springy, stretch):
        """ Set the size policy of the editor's controller.
    
        Based on the "direction" of the group that contains this editor
        (VGroup or HGroup), set the stretch factor and the resizing
        policy of the control.
    
        Parameters
        ----------
        direction : QtGui.QBoxLayout.Direction
            Directionality of the group that contains this edito. Either
            QtGui.QBoxLayout.LeftToRight or QtGui.QBoxLayout.TopToBottom
    
        resizable : bool
            True if control should be resizable in the orientation opposite
            to the group directionality
    
        springy : bool
            True if control should be resizable in the orientation equal
            to the group directionality
    
        stretch : int
            Stretch factor used by Qt to distribute the total size to
            each component.
        """
    
        policy = self.control.sizePolicy()
    
        if direction == QtGui.QBoxLayout.LeftToRight:
            if springy:
                policy.setHorizontalStretch(stretch)
                policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
            if resizable:
                policy.setVerticalStretch(stretch)
                policy.setVerticalPolicy(QtGui.QSizePolicy.Expanding)
    
        else: # TopToBottom
            if springy:
                policy.setVerticalStretch(stretch)
                policy.setVerticalPolicy(QtGui.QSizePolicy.Expanding)
            if resizable:
                policy.setHorizontalStretch(stretch)
                policy.setHorizontalPolicy(QtGui.QSizePolicy.Expanding)
    
        self.control.setSizePolicy(policy)
    
class QTGraphWidgetEditor(BasicEditorFactory):
    
   klass = _QTGraphWidgetEditor

class QTGraphWidgetInitHandler(Handler):
    """Handler calls mpl_setup() to initialize mpl events"""
    
    def init(self, info):
        """This method gets called after the controls have all been
        created but before they are displayed.
        """
#        info.object.mpl_setup()
        return True

if __name__ == "__main__":
    # Create a window to demo the editor
    from traits.api import HasTraits
    from traits.ui.api import View, Item
    from numpy import sin, cos, linspace, pi
#    from matplotlib.widgets import  RectangleSelector

    class Test(HasTraits):

#        figure = Instance(pg.PlotWidget, ())
        figure = Instance(pg.PlotWidget)
#        test_nr = Int(123)

        traits_view = View(Item('figure', editor=QTGraphWidgetEditor(),
                         show_label=False),
                    handler = QTGraphWidgetInitHandler,
                    resizable=True)

        def __init__(self):
            super(Test, self).__init__()
            self.p1 = self.figure.plot()
            t = linspace(0, 2*pi, 200)
            self.p1.setData(sin(t)*(1+0.5*cos(11*t)), cos(t)*(1+0.5*cos(11*t)))
#            self.on_trait_change(self.handle_scroll, 'view.figure.mouse_delta')
        
        def _figure_default(self):
            plot = pg.PlotWidget()
            self.vLine = pg.InfiniteLine(angle=90, movable=False)
            self.hLine = pg.InfiniteLine(angle=0, movable=False)
            plot.addItem(self.vLine, ignoreBounds=True)
            plot.addItem(self.hLine, ignoreBounds=True)
            self.label = pg.LabelItem(justify='right')
            plot.addItem(self.label)              
#            plot.scene().sigMouseMoved.connect(mouseMoved)

            self.proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
            return plot
        
        def mouseMoved(self, evt):
            pos = evt[0]  ## using signal proxy turns original arguments into a tuple
#            logger.info(self.figure.mapFromScene(pos))
            if self.figure.sceneBoundingRect().contains(pos):
                mousePoint = self.figure.getPlotItem().getViewBox().mapSceneToView(pos)
#                index = int(mousePoint.x())
##                if index > 0 and index < len(data1):
                self.label.setText("<span style='font-size: 12pt'>x=%0.1f,   <span style='color: red'>y1=%0.1f</span>" % (mousePoint.x(), mousePoint.y()))
                self.vLine.setPos(mousePoint.x())
                self.hLine.setPos(mousePoint.y())
                

        #def mpl_setup(self):
        #    def onselect(eclick, erelease):
        #        print "eclick: {}, erelease: {}".format(eclick,erelease)
        #       
        #    self.rs = RectangleSelector(self.axes, onselect,
        #                                drawtype='box',useblit=True)
if __name__ == '__main__':
    console = logging.StreamHandler()
    logger.addHandler(console)
    logger.setLevel(logging.DEBUG)
    t=Test()
    t.configure_traits()
