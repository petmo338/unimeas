# Standard library imports.
import os.path

# Enthought library imports.
from envisage.api import Plugin
from envisage.ui.tasks.api import TaskFactory
from traits.api import List


class MainWindowPlugin(Plugin):
    """ The main window plugin.
    """

    # Extension point IDs.
    PREFERENCES       = 'envisage.preferences'
    PREFERENCES_PANES = 'envisage.ui.tasks.preferences_panes'
    TASKS             = 'envisage.ui.tasks.tasks'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'sensorscience.unimeas.mainwindow'

    # The plugin's name (suitable for displaying to the user).
    name = 'MainWindow'

    #### Contributions to extension points made by this plugin ################

    preferences = List(contributes_to=PREFERENCES)
    preferences_panes = List(contributes_to=PREFERENCES_PANES)
    tasks = List(contributes_to=TASKS)

    ###########################################################################
    # Protected interface.
    ###########################################################################

    def _preferences_default(self):
        filename = os.path.join(os.getcwd(), 'preferences.ini')
        return [ 'file://' + filename ]

    def _preferences_panes_default(self):
        from unimeas_preferences import UnimeasPreferencesPane
        return [ UnimeasPreferencesPane ]

    def _tasks_default(self):
        from measure_over_time_task import MeasureOverTimeTask
        from measure_interval_task import MeasureIntervalTask
        return [ TaskFactory(id = 'sensorscience.unimeas.measureinterval',
                             name = 'Measure interval/ramp',
                             factory = MeasureIntervalTask),
                  TaskFactory(id = 'sensorscience.unimeas.measureovertime',
                             name = 'Measurement over time',
                             factory = MeasureOverTimeTask)]
