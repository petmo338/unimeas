from enthought.traits.api import HasTraits, Bool, Instance, Button, List, \
    Unicode, Str, File
from traitsui.api import EnumEditor, Item, View, HGroup, VGroup, spring, Handler, FileEditor
from traitsui.menu import OKButton, CancelButton
from generic_popup_message import GenericPopupMessage
import csv
import time
import logging
logger = logging.getLogger(__name__)

TABLE_NAME_PREPEND = 'm'

class CreateMeasurementPopup(Handler):
    measurement_name = Str
    measurement_description = Str
    prepend_timestamp = Bool(True)

    traits_view = View(Item('measurement_name'),
                       Item('prepend_timestamp'),
                       Item('measurement_description', style = 'custom'),
                       buttons = [OKButton, CancelButton], kind = 'modal')

    def _measurement_name_default(self):
        localtime   = time.localtime()
        return time.strftime("%Y%m%d_%H%M%S_", localtime)

    def _prepend_timestamp_changed(self, old, new):
        if new == True:
            self.measurement_name = self._measurement_name_default() + self.measurement_name
        else:
            self.measurement_name = ''


class SQLWrapper():

    SERVER_HOST = 'pc15389.sensor.lab'
#    SERVER_HOST = 'localhost'
    USER = 'sensor'
    PASSWORD = 'sensor'
    table_name = ''

    def initialize(self):
        from pg8000 import DBAPI
        self.DBAPI = DBAPI
        try:
            self.conn =  self.DBAPI.connect(host=self.SERVER_HOST, \
                user=self.USER, password=self.PASSWORD, database='postgres')
        except:
            return list()

        self.cursor = self.conn.cursor()
        self.cursor.execute('SELECT datname FROM pg_database WHERE datistemplate = \
                            false AND datname != \'postgres\' ')
#        self.conn.commit()
        result = self.cursor.fetchall()
        retval = list()
        for user in result:
            retval.append(user[0])
        return retval

    def change_database(self, db):
        self.cursor.close()
        self.conn.close()
        try:
            self.conn =  self.DBAPI.connect(host=self.SERVER_HOST, user=self.USER, \
                password=self.PASSWORD, database=str(db))
        except:
            return False
        self.DBAPI.paramstyle = 'numeric'
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()
        return True

    def get_measurements(self):

        query = 'select tablename from pg_catalog.pg_tables where tableowner = \'' \
            + self.USER + '\';'
        self.cursor.execute(query)
        self.conn.commit()
        result = self.cursor.fetchall()
        retval = list()
        for table in result:
            retval.append(table[0])
        return retval


    def set_measurement(self, column_names, name, comment = '-'):
        if name[0].isdigit():
            name = TABLE_NAME_PREPEND + name
        self.column_names = column_names
        result = tuple()
        query = "SELECT tablename FROM pg_tables where tablename like '" + name + "'"

        try:
            self.cursor.execute(query)
#            self.cursor.execute("SELECT tablename FROM pg_tables where tablename like :1", (name,))
            self.conn.commit()
        except Exception as e:
            logger.error('Trying tablename like %s', e)
        else:
            result = self.cursor.fetchall()
        if result == tuple():
            if not self._create_table(column_names, name):
                logger.warning('Unable to create table. Saving of data disabled')
                self.table_name = ''
                return False
        else:
            logger.info('Table: %s exists, appending', name)
        self.table_name = name
        query   = "COMMENT on table " + name + " is '" + comment + "'"
  #      self.cursor.execute(query)
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            logger.error('Trying Comment: %s', e)
        return True

    def _create_table(self, column_names, name):
#        logger.warning('column_names: %s, name %s', column_names, name)
        query = "CREATE TABLE " + name + " (uid SERIAL, "
        query = query + " REAL ,".join(column_names) + " REAL)"
        try:
            #self.cursor.execute("CREATE TABLE \'%s\'  (uid SERIAL, %s REAL)", (name, ' REAL, '.join(column_names),))
            self.cursor.execute(query)
            self.conn.commit()
        except Exception as e:
            logger.warning('Problems with query %s. Error %s', query, e)
            return False
        return True


    def insert_data(self, data):
        if self.table_name == '':
            logger.info('No table_name set. Buffering...')
        else:
            string_data = []
            for i in xrange(len(self.column_names)):
                string_data.append('DEFAULT')
            query = "INSERT INTO " + str(self.table_name) + " VALUES (DEFAULT "
            #query = ''
            for channel in data.keys():
                candidates = [n for n in self.column_names if n.startswith(channel)]

                for column in candidates:
                    column_index = self.column_names.index(column)
                    try:
                        string_data[column_index] = str(data[channel][0][column[len(channel):]])
                    except KeyError:
                        if data[channel][1] == dict():
                            break
                        string_data[column_index] = str(data[channel][1][column[len(channel):]])

            for value in string_data:
                query = query + " ," + value
            query = query + ")"
            try:
                self.cursor.execute(query)
                self.conn.commit()
            except Exception as e:
                logger.error('SQL error %s', e)
#            logger.info('query: %s', query)


class SQLPanel(HasTraits):

    ############ Panel Interface ###########################3

    pane_name = Str('Save Configuration')
    pane_id = Str('sensorscience.unimeas.sql_pane')

    database_wrapper = Instance(SQLWrapper)
#    instrument = Instance(IInstrument)
    selected_user = Str
    new_measurement = Button
    measurement_name = Unicode
    measurement_description = Str
    save_in_database = Bool(False)

    save_to_file = Bool
    running = Bool
#    filename = Str('Z:\\Lab Users\\MY_NAME\\MEASUREMENT_NAME')
    filename = File
    available_users = List(Unicode)
    available_measurements = List(Unicode)


    traits_view = View(VGroup(HGroup(Item('save_in_database', enabled_when = 'not running'),
                            Item('selected_user',
                            editor=EnumEditor(name='available_users'),
                            enabled_when = 'not running and save_in_database'), spring,
                        Item('new_measurement', show_label=False,  enabled_when = 'not running and save_in_database')),
                        Item('measurement_name',
                            editor=EnumEditor(name='available_measurements'),
                            enabled_when = 'not running and save_in_database'),
                        Item('measurement_description', enabled_when = 'False', style = 'custom'),
                        Item('save_to_file', label = 'Save to file (.csv)', enabled_when = 'not running'),
                        #Item('filename', enabled_when = 'not running and save_to_file'),
                        Item('filename',  style='simple', editor = FileEditor(dialog_style = 'save', filter = ['*.csv']))))

    def _new_measurement_fired(self):
        popup = CreateMeasurementPopup()
        ui = popup.edit_traits()
        if ui.result is True:
            result = popup.measurement_name
            if result[0].isdigit():
                result = TABLE_NAME_PREPEND + result
            result = result.replace(' ','_')
            self.available_measurements.append(result)
            self.measurement_name = self.available_measurements[-1]
            self.measurement_description = popup.measurement_description

    def _available_users_default(self):
        return []

    def _measurement_name_default(self):
        return ''


    def _selected_user_changed(self, old, new):
        if new == '':
            self.save_in_database = False
        else:
            self.save_in_database = True
            if not self.database_wrapper.change_database(new):
                logger.error('Unable to connect to database %s', new)
                self.save_in_database = False
                self.available_measurements = []
                return
            self.available_measurements = self.database_wrapper.get_measurements()
            self.available_measurements.insert(0, '')


    def _save_in_database_changed(self, new):
        if new:
            self.database_wrapper = SQLWrapper()
            self.available_users = self.database_wrapper.initialize()
        else:
            del self.database_wrapper
            self.available_users = []

    def set_column_names(self, column_names):
        self.column_names = column_names

    def write_to_file(self, data):
        string_data = []
        for i in xrange(len(self.column_names)):
                string_data.append('0')
        for channel in data.keys():
                candidates = [n for n in self.column_names if n.startswith(channel)]
                for column in candidates:
                    column_index = self.column_names.index(column)
                    try:
                        string_data[column_index] = str(data[channel][0][column[len(channel):]])
                    except KeyError:
                        if data[channel][1] == dict():
                            break
                        string_data[column_index] = str(data[channel][1][column[len(channel):]])

        if hasattr(self, 'csv_writer'):
            self.csv_writer.writerow(string_data)


#    @on_trait_change('instrument.sample_number')
    def add_data(self, data):
        if self.save_in_database:
            self.database_wrapper.insert_data(data)
        if self.save_to_file:
            self.write_to_file(data)

    def start_stop(self, running):
        self.running = running
        if running and self.save_in_database:
            if len(self.measurement_name) == 0:
                GenericPopupMessage(message = 'No measurement selected').edit_traits()
                self.save_in_database = False
            else:
                self.database_wrapper.set_measurement(self.column_names, self.measurement_name,
                    self.measurement_description)

        if running and self.save_to_file:
            try:
                filehandle = open(self.filename, "a", 1)
            except IOError:
                logger.error('Unable to open file %s', self.filename)
            else:
                self.csv_writer = csv.writer(filehandle, dialect=csv.excel_tab)
                self.csv_writer.writerow(self.column_names)
            self.column_names = self.column_names
#        if not running and self.save_to_file:
#            del self.csv_writer


if __name__ == '__main__':
    s = SQLPanel()
    s.configure_traits()
