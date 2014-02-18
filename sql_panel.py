from enthought.traits.api import HasTraits, Bool, Instance, Button, List, \
    Unicode, Str
from traitsui.api import EnumEditor, TextEditor, Item, View, HGroup, VGroup, spring
import csv
import time
import logging

class SQLWrapper():

    SERVER_HOST = 'pc15389.sensor.lab'
    USER = 'sensor'
    PASSWORD = 'sensor'
    table_name = ''
    TABLE_NAME_PREPEND = 'm'
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
        self.conn.commit()
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

        self.cursor = self.conn.cursor()
        return True

    def set_table(self, column_names, name, comment = ''):
        name = self.TABLE_NAME_PREPEND + name
        self.column_names = column_names
        self.DBAPI.paramstyle = "numeric"
        query = 'SELECT tablename FROM pg_tables where tablename like \'' + name + '\''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        if result == tuple():
            if not self._create_table(column_names, name):
                logging.getLogger('sql_wrapper').warning('Unable to create table. \
                                                        Saving data disabled')
                self.table_name = ''
                return False
        else:
            logging.getLogger('sql_wrapper').warning('Table: %s exists, appending', name)
        self.table_name = name
        query   = 'COMMENT on table ' + name + ' is \'' + comment + '\';'
        self.cursor.execute(query)
        return True

    def _create_table(self, column_names, name):
        logging.getLogger('sql_wrapper').info('column_names: %s, name %s', column_names, name)
        query = 'CREATE TABLE ' + name + ' (uid SERIAL, '
        query = query + ' REAL ,'.join(column_names) + ' REAL)'
#        logging.getLogger('sql_wrapper').info('query: %s', query)
# Fixa en try, catch
        self.cursor.execute(query)
        self.conn.commit()
        return True


    def insert_data(self, data):
        if self.table_name == '':
            logging.getLogger('sql_wrapper').info('No table_name set. Buffering...')
        else:
            string_data = []
            for i in xrange(len(self.column_names)):
                string_data.append('DEFAULT')
            query = 'INSERT INTO ' + str(self.table_name) + ' VALUES (DEFAULT '
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
                query = query + ' ,' + value
            query = query + ')'
            self.cursor.execute(query)
            self.conn.commit()
#            logging.getLogger('sql_wrapper').info('query: %s', query)


class SQLPanel(HasTraits):

    ############ Panel Interface ###########################3

    pane_name = Str('Save Configuration')
    pane_id = Str('sensorscience.unimeas.sql_pane')

    database_wrapper = Instance(SQLWrapper)
#    instrument = Instance(IInstrument)
    selected_user = Str
    refresh = Button
    measurement_name = Str
    measurement_description = Str
    save_in_database = Bool(False)
    prepend_timestamp = Bool(True)
    save_to_file = Bool
    running = Bool
    filename = Str('Z:\\Lab Users\\MY_NAME\\MEASUREMENT_NAME')
    available_users = List(Unicode)


    traits_view = View(VGroup(HGroup(Item('save_in_database', enabled_when = 'not running'),
                            Item('selected_user',
                            editor=EnumEditor(name='available_users'),
                            enabled_when = 'not running and save_in_database'), spring,
                        Item('refresh', show_label=False,  enabled_when = 'not running and save_in_database')),

                        Item('prepend_timestamp', enabled_when = 'not running and save_in_database'),
                        Item('measurement_name', enabled_when = 'not running and save_in_database'),
                        Item('measurement_description', enabled_when = 'not running and save_in_database', style = 'custom'),
                        Item('save_to_file', label = 'Save to file (.csv)', enabled_when = 'not running'),
                        Item('filename', enabled_when = 'not running and save_to_file')))

    def _available_users_default(self):
        return []

    def _measurement_name_default(self):
        localtime   = time.localtime()
        return time.strftime("%Y%m%d_%H%M%S_", localtime)

    def _prepend_timestamp_changed(self, old, new):
        if new == True:
            self.measurement_name = self._measurement_name_default() + self.measurement_name
        else:
            self.measurement_name = ''

    def _selected_user_changed(self, old, new):
        if new == '':
            self.save_in_database = False
        else:
            self.save_in_database = True
            if not self.database_wrapper.change_database(new):
                logging.getLogger('sql_panel').error('Unable to connect to database %s', new)

    def _save_in_database_changed(self, new):
        if new:
            self.database_wrapper = SQLWrapper()
            self.available_users = self.database_wrapper.initialize()
        else:
            del self.database_wrapper
            self.available_users = []

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
            self.database_wrapper.set_table(self.column_names, self.measurement_name,
                self.measurement_description)

        if running and self.save_to_file:
            try:
                filehandle = open(self.filename, "a", 1)
            except IOError:
                self.logger.error('Unable to open file %s', self.filename)
            self.csv_writer = csv.writer(filehandle, dialect=csv.excel_tab)
            self.csv_writer.writerow(self.column_names)
            self.column_names = self.column_names
        if not running and self.save_to_file:
            del self.csv_writer


if __name__ == '__main__':
    s = SQLPanel()
    s.configure_traits()
