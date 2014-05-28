from enthought.traits.api import HasTraits, Bool, Int, List, Float, Instance, \
    Str
from traitsui.api import Item, View, Group,Handler, \
    TableEditor
from traitsui.table_column import NumericColumn
import logging
from pyface.timer.api import Timer
import numpy as np
logger = logging.getLogger(__name__)

class TableEntry(HasTraits):

    time = Int
    start_temp = Int
    end_temp = Int
    remaining = Int
    
    def _on_time_changed(self, new):
        self.remaining = new

table_editor = TableEditor(
    columns = [ NumericColumn( name = 'time', label = 'Seconds', horizontal_alignment = 'right'),
                NumericColumn( name = 'start_temp', label = 'Start temp'),
                NumericColumn( name = 'end_temp', label = 'End temp'),
                NumericColumn( name = 'remaining', editable = False, label = 'Left', width = 70, read_only_cell_color = 0xF4F3EE)],
    deletable   = True,
    sort_model  = False,
    auto_size   = True,
    orientation = 'vertical',
    show_toolbar = False,
    sortable = False,
    row_factory = TableEntry )

class TemperatureControlHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
        info.object.start_stop(False)
        return

class TemperatureControlPanel(HasTraits):
    UPDATE_INTERVAL = 500.0
    pane_name = Str('Temperature control ')
    pane_id = Str('sensorscience.unimeas.temperatur_control_pane')
    enable = Bool(False)
    timer = Instance(Timer)

    table_entries = List(TableEntry)
    current_row = Int(0)
    current_temp = Int(0)
    current_time = Float
    row_start_time = Float
    running = False

    temperature_table = List(Int)

    traits_view = View(Item('enable'),
        Group(
            Item( 'table_entries',
                  show_label  = False,
                  editor      = table_editor,
                  enabled_when = 'not running'
            ),
            show_border = True,
        ),
        resizable = True,
        kind      = 'live',
        handler = TemperatureControlHandler
    )

    def _onTimer(self):
        self.current_time += (self.UPDATE_INTERVAL / 1000)
        index = int(np.floor(self.current_time))
        if index > len(self.temperature_table):
            self.start_stop(False)
        if self.temperature_table[index] is not self.current_temp:
            self.current_temp = self.temperature_table[index]

    def _table_entries_default(self):
        return [TableEntry(time = 10, start_temp = 50, end_temp = 50, remaining = -1),
                TableEntry(time = 5, start_temp = 50, end_temp = 150, remaining = -1),
                TableEntry(time = 10, start_temp = 150, end_temp = 150, remaining = -1),
                TableEntry(time = 20, start_temp = 150, end_temp = 100, remaining = -1),]

    def start_stop(self, running):
        if not self.enable:
            return
        self.running = running
        if running:
            self.calculate_temperature_table()
            self.timer = Timer(self.UPDATE_INTERVAL, self._onTimer)
            self.timer.start()
            self.current_row = 0
            self.row_changed(0)
            self.current_time = 0
            self.current_temp = self.temperature_table[0]
            
        else:
            if self.timer is not None:
                self.timer.Stop()

    def add_data(self, data):
        pass

    def calculate_temperature_table(self):
        self.temperature_table = []
        for row in self.table_entries:
            slope = (row.end_temp - row.start_temp) / float(row.time - 1)
            #logger.info('Slope of row %s is %f', row, slope)
            for i in range(row.time):
                self.temperature_table.append(int(i * slope + row.start_temp))

    def row_changed(self, remainder):
        self.row_start_time = self.current_time
        if self.current_row >= len(self.table_entries):
            return


    def _current_temp_changed(self, new):
        logger.info('Send %s to temp controller', new)   


if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    g=TemperatureControlPanel()
    g.configure_traits()
