from traits.api import HasTraits, Bool, Int, List, Float, Instance, \
    Str
from traitsui.api import Item, View, Group, Handler, \
    TableEditor
from traitsui.table_column import NumericColumn
from time import time
import logging
from program.instruments.i_instrument import IInstrument
logger = logging.getLogger(__name__)

class TableEntry(HasTraits):

    time = Int
    enabled = Bool
    remaining = Int

table_editor = TableEditor(
    columns = [ NumericColumn( name = 'time'),
                NumericColumn( name = 'enabled'),
                NumericColumn( name = 'remaining')],
    deletable   = True,
    sort_model  = False,
    auto_size   = True,
    orientation = 'vertical',
    edit_view   = None,
#    auto_add = True,
    show_toolbar = True,
    sortable = False,
    row_factory = TableEntry )

class GPIOHandler(Handler):

    def closed(self, info, is_ok):
        """ Handles a dialog-based user interface being closed by the user.
        Overridden here to stop the timer once the window is destroyed.
        """
#        info.object.timer.Stop()
        return

class GPIOPanel(HasTraits):
    pane_name = Str('GPIO control')
    pane_id = Str('sensorscience.unimeas.gpio_pane')
    enable = Bool(False)

    table_entries = List(TableEntry)
    current_row = Int(0)
    row_start_time = Float
    running = False
    active_instrument = Instance(IInstrument)

    traits_view = View(Item('enable'), #Label('Rightclick to edit'),
        Group(
            Item( 'table_entries',
                  show_label  = False,
#                  label       = 'right-click to edit',
                  editor      = table_editor,
                  enabled_when = 'not running'
            ),
            show_border = True,
        ),
        resizable = True,
        kind      = 'live'
    )

    def _table_entries_default(self):
        return [TableEntry(time = 0, enabled = True, remaining = 0),
                TableEntry(time = 10, enabled = False, remaining = 0)]

    def start_stop(self, running):
        if not self.enable:
            return
        self.running = running
        if running:
            self.current_row = 0
            self.row_changed(0)

    def add_data(self, data):
        if not self.enable:
            return
        if self.current_row < len(self.table_entries):
            row_time = time() - self.row_start_time
            self.table_entries[self.current_row].remaining = int(self.table_entries[self.current_row].time - row_time)
#            logging.getLogger(__name__).info('row_time %f, rem-time %d, tot_time %d', \
#                row_time, self.table_entries[self.current_row].remaining, self.table_entries[self.current_row].time)
            if self.table_entries[self.current_row].remaining < 1:
                self.current_row += 1
                self.row_changed(self.table_entries[self.current_row - 1].time - row_time)

    def row_changed(self, remainder):
        self.row_start_time = time() + remainder
#        logging.getLogger(__name__).info('self.row_start_time: %f', self.row_start_time)
        if self.current_row >= len(self.table_entries):
            return
        msg = 'digio.writebit(1, %d)' % self.table_entries[self.current_row].enabled
#        logging.getLogger(__name__).info('Row changed. Set to %s, msg: %s', \
#            self.table_entries[self.current_row].enabled, msg)

        if self.active_instrument.name == 'Keithley SourceMeter':
            if self.table_entries[self.current_row].enabled:
                msg = 'digio.writeport(16383)'
            else:
                msg = 'digio.writeport(0)'
#            msg = 'digio.writebit(1, %d)' % self.table_entries[self.current_row].enabled
            self.active_instrument.instrument.write(msg)

    #def _enable_changed(self):
    #    self.request_redraw = True

if __name__ == '__main__':
    g=GPIOPanel()
    g.configure_traits()
