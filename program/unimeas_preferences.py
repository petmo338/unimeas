# Enthought library imports.
from envisage.ui.tasks.api import PreferencesPane
from apptools.preferences.api import PreferencesHelper, Preferences
from traits.api import Bool, Dict, Str, Unicode
from traitsui.api import EnumEditor, HGroup, VGroup, Item, Label, \
    View


class UnimeasPreferences(PreferencesHelper):
    """ The preferences helper for the Unimeas application.
    """

    #### 'PreferencesHelper' interface ########################################

    # The path to the preference node that contains the preferences.
    preferences_path = 'sensorscience.unimeas'

    #### Preferences ##########################################################

    # The task to activate on app startup if not restoring an old layout.
    default_task = Str

    # Whether to always apply the default application-level layout.
    # See TasksApplication for more information.
    always_use_default_layout = Bool

    preferences = Preferences(filename = 'settings.ini')

class UnimeasPreferencesPane(PreferencesPane):
    """ The preferences pane for the Unimeas application.
    """

    #### 'PreferencesPane' interface ##########################################

    # The factory to use for creating the preferences model object.
    model_factory = UnimeasPreferences

    #### 'AttractorsPreferencesPane' interface ################################

    task_map = Dict(Str, Unicode)

    view = View(
        VGroup(HGroup(Item('always_use_default_layout'),
                      Label('Always use the default active task on startup'),
                      show_labels = False),
               HGroup(Label('Default active task:'),
                      Item('default_task',
                           editor=EnumEditor(name='handler.task_map')),
                      enabled_when = 'always_use_default_layout',
                      show_labels = False),
               label='Application startup'),
        resizable=True)

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _task_map_default(self):
        return dict((factory.id, factory.name)
                    for factory in self.dialog.application.task_factories)
