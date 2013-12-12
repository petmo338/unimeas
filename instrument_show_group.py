""" A Group for toggling the visibility of a task's dock panes. """


# Enthought library imports.
from pyface.action.api import Action, ActionItem, Group
from pyface.tasks.api import Task
from traits.api import cached_property, Instance, List, on_trait_change, \
    Property, Unicode

# Local imports.
from instruments.i_instrument import IInstrument


class InstrumentShowAction(Action):
    """ An Action to show selected instrument.
    """

    #### 'DockPaneToggleAction' interface #####################################

    instrument = Instance(IInstrument)
    task = Instance(Task)
    
    #### 'Action' interface ###################################################

    name = Property(Unicode, depends_on='instrument.name')
    style = 'toggle'
    tooltip = Property(Unicode, depends_on='name')

    ###########################################################################
    # 'Action' interface.
    ###########################################################################

    def destroy(self):
        super(InstrumentShowAction, self).destroy()

        # Make sure that we are not listening to changes to the pane anymore.
        # In traits style, we will set the basic object to None and have the
        # listener check that if it is still there.
        self.instrument = None

    def perform(self, event=None):
        if self.instrument:
            self.task.active_instrument = self.instrument
#            self.dock_pane.visible = not self.dock_pane.visible

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _get_name(self):
        if self.instrument is None:
            return 'UNDEFINED'
        return self.instrument.name

    def _get_tooltip(self):
        return u'Toggles the visibility of the %s pane.' % self.name

    @on_trait_change('task.active_instrument')
    def _update_checked(self):
        if self.instrument == self.task.active_instrument:
            self.checked = True
        else:
            self.checked = False
#
#    @on_trait_change('dock_pane.closable')
#    def _update_visible(self):
#        if self.dock_pane:
#            self.visible = self.dock_pane.closable

class InstrumentShowGroup(Group):
    """ A Group for toggling the visibility of a task's dock panes.
    """

    #### 'Group' interface ####################################################

    id = 'InstrumentShowGroup'

    items = List

    #### 'DockPaneToggleGroup' interface ######################################

    task = Property(depends_on='parent.controller')

    @cached_property
    def _get_task(self):
        manager = self.get_manager()

        if manager is None or manager.controller is None:
            return None

        return manager.controller.task

    instruments = Property(depends_on='task.instruments')

    @cached_property
    def _get_instruments(self):
        if self.task is None or self.task.window is None:
            return []

#        task_state = self.task.window._get_state(self.task)
        return self.task.instruments

    def get_manager(self):
        # FIXME: Is there no better way to get a reference to the menu manager?
        manager = self
        while isinstance(manager, Group):
            manager = manager.parent
        return manager

    #### Private interface ####################################################

    @on_trait_change('instruments[]')
    def _instruments_updated(self):
        """Recreate the group items when dock panes have been added/removed.
        """

        # Remove the previous group items.
        self.destroy()

        items = []
        for instrument in self.instruments:
            action = InstrumentShowAction(instrument=instrument, task=self.task)
            items.append(ActionItem(action=action))

        items.sort(key=lambda item: item.action.name)
        self.items = items

        # Inform the parent menu manager.
        manager = self.get_manager()
        manager.changed = True