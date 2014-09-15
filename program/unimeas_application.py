# Enthought library imports.
from envisage.ui.tasks.api import TasksApplication
from pyface.tasks.api import TaskWindowLayout
from traits.api import Bool, Instance, List, Property

# Local imports.
from unimeas_preferences import UnimeasPreferences

class UniMeasApplication(TasksApplication):
    """ The Unimeas Tasks application.
    """

    #### 'IApplication' interface #############################################

    # The application's globally unique identifier.
    id = 'sensorscience.unimeas'

    # The application's user-visible name.
    name = 'UniMeas - Unified measurement system'

    #### 'TasksApplication' interface #########################################

    # The default window-level layout for the application.
    default_layout = List(TaskWindowLayout)

    # Whether to restore the previous application-level layout when the
    # applicaton is started.
    always_use_default_layout = Property(Bool)

    #### 'UnimeasApplication' interface ####################################

    preferences_helper = Instance(UnimeasPreferences)

    ###########################################################################
    # Private interface.
    ###########################################################################

    #### Trait initializers ###################################################

    def _default_layout_default(self):
        active_task = self.preferences_helper.default_task
        tasks = [ factory.id for factory in self.task_factories ]

        return [ TaskWindowLayout(*tasks,
                                  active_task = active_task,
                                  size = (1200, 600)) ]

    def _preferences_helper_default(self):
        return UnimeasPreferences(preferences = self.preferences)

    #### Trait property getter/setters ########################################

    def _get_always_use_default_layout(self):
        return self.preferences_helper.always_use_default_layout
