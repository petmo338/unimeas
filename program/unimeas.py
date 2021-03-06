# Standard library imports.
import logging

# Plugin imports.
from envisage.core_plugin import CorePlugin
from envisage.ui.tasks.tasks_plugin import TasksPlugin
from mainwindow_plugin import MainWindowPlugin
#from measurements_plugin import MeasurementsPlugin

# Local imports.
from unimeas_application import UniMeasApplication

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-2s %(name)-12s %(levelname)-8s %(message)s',
                    filename='unimeas.log')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.WARNING)
# set a format which is simpler for console use
formatter = logging.Formatter('%(asctime)-2s %(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.WARNING)
requests_log.propagate = True
app = None

def main(argv):
    """ Run the application.
    """
    logging.info('main starting')

    plugins = [ CorePlugin(), TasksPlugin(), MainWindowPlugin() ]
    app = UniMeasApplication(plugins=plugins)
#    pdb.set_trace()
    app.run()

    logging.shutdown()


if __name__ == '__main__':

#    import sys
    """ Run the application.
    """
    logging.info('main starting')

    plugins = [ CorePlugin(), TasksPlugin(), MainWindowPlugin() ]
    app = UniMeasApplication(plugins=plugins)
#    pdb.set_trace()
    app.run()

    logging.shutdown()
#    main(sys.argv)
