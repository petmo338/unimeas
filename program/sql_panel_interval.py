from enthought.traits.api import HasTraits, Bool, Instance, Button, List, \
    Unicode, Str
from traitsui.api import EnumEditor, Item, View, HGroup, VGroup, spring, Handler
from traitsui.menu import OKButton, CancelButton
from generic_popup_message import GenericPopupMessage
import time
import logging
logger = logging.getLogger(__name__)

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
    TABLE_NAME_PREPEND = 'm'
    def _init(self):
        from pg8000 import DBAPI
        self.DBAPI = DBAPI
        try:
            self.conn =  self.DBAPI.connect(host=self.SERVER_HOST, \
                user=self.USER, password=self.PASSWORD, database='postgres')
        except:
            return False
        self.cursor = self.conn.cursor()
        return True

    def get_users(self):
        if not self._init():
            return []
        self.cursor.execute('SELECT datname FROM pg_database WHERE datistemplate = \
                            false AND datname != \'postgres\' ')
        self.conn.commit()
        result = self.cursor.fetchall()
        return [n[0] for n in result]

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

    def get_measurements(self):
        cursor = self.conn.cursor()
        query = 'select tablename from pg_catalog.pg_tables where tableowner = \'' \
            + self.USER + '\';'
        cursor.execute(query)
        self.conn.commit()
        result = cursor.fetchall()
        retval = list()
        for table in result:
            retval.append(table[0])
        return retval


    def set_table(self,name, comment = ''):
        if name[0].isdigit():
            name = self.TABLE_NAME_PREPEND + name
#        self.DBAPI.paramstyle = "numeric"
        query = 'SELECT tablename FROM pg_tables where tablename like \'' + name + '\''
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        if result == tuple():
            if not self._create_table(name):
                logger.warning('Unable to create table. Saving data disabled')
                self.table_name = ''
                return False
        else:
            logger.info('Table: %s exists, appending', name)
        self.table_name = name
        query   = 'COMMENT on table ' + name + ' is \'' + comment + '\';'
        self.cursor.execute(query)
        return True

    def _create_table(self, name):
        query = 'CREATE TABLE ' + name + ' (uid SERIAL)'
        self.cursor.execute(query)
        self.conn.commit()
        return True

    def add_columns(self, columns):
        for col in columns:
            query = 'ALTER TABLE ' + self.table_name +' ADD COLUMN ' + col + ' REAL DEFAULT NULL'
            try:
                self.cursor.execute(query)
            except Exception as e:
                logger.error('In add_columns, %s', e)

        self.current_columns = columns
        query =  'select column_name from information_schema.columns where table_name=\'' + self.table_name + '\';'
        self.cursor.execute(query)
        self.conn.commit()
        result = self.cursor.fetchall()
        self.column_names = [n[0] for n in result]
        logger.info('all column names %s', self.column_names)

    def insert_data(self, data):
        if self.table_name == '':
            logger.warning('No table_name set. NOT saving data!!!')
        else:
            logger.warning('%s %s %s', data, self.current_columns, self.column_names)
            string_data = []
            for i in xrange(len(self.column_names)):
                string_data.append('DEFAULT')
            query = 'INSERT INTO ' + str(self.table_name) + ' VALUES (DEFAULT '
            for channel in data.keys().lower():
                for column in self.current_columns:
                    column_index = self.column_names.index(column)
                    string_data.append[column_index] = str(data[channel][column_index%2].values()[0])

            for value in string_data:
                query = query + ' ,' + value
            query = query + ')'
            logger.info('query: %s', query)
            self.cursor.execute(query)
            self.conn.commit()

    def get_description(self, measurement_name):
        if measurement_name == '':
            return ''
        query = 'SELECT obj_description(\'public.' + measurement_name + '\'::regclass, \'pg_class\');'
        logger.info(query)
        logger.info('Paramstyyle : %s', self.DBAPI.paramstyle)
        self.DBAPI.paramstyle = 'format'
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except self.DBAPI.ProgrammingError as e:
            logger.warning(e)
            return ''
        result = self.cursor.fetchall()
#        logger.warning(e)

        logger.info('get_desc: %s', result)
        if result[0][0] == None:
            return ''
        else:
            return result[0][0]


class SQLPanel(HasTraits):

    ############ Panel Interface ###########################3

    pane_name = Str('Save Configuration')
    pane_id = Str('sensorscience.unimeas.sql_pane_interval')

    database_wrapper = Instance(SQLWrapper)
#    instrument = Instance(IInstrument)
    selected_user = Str
    new_measurement = Button
    measurement_name = Str
    measurement_description = Str
    save_in_database = Bool(False)


    running = Bool

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
                        Item('measurement_description', style = 'custom')))

    def _new_measurement_fired(self):
        popup = CreateMeasurementPopup()
        ui = popup.edit_traits()
        if ui.result is True:
            self.is_new = True
            self.available_measurements.append(popup.measurement_name)
            self.measurement_name = popup.measurement_name
            self.measurement_description = popup.measurement_description
            self.database_wrapper.set_table(self.measurement_name,
                    self.measurement_description)




    def _available_users_default(self):
        return []

    def _measurement_name_default(self):
        return ''

    def _measurement_name_changed(self, new):
        if hasattr(self, 'is_new'):
            if not self.is_new:
                self.measurement_description = self.database_wrapper.get_description(new)
            else:
                self.is_new = False
        else:
            self.measurement_description = self.database_wrapper.get_description(new)

        self.database_wrapper.set_table(new, self.measurement_description)

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
            self.available_users = self.database_wrapper.get_users()
        else:
            del self.database_wrapper
            self.available_users = []

#    @on_trait_change('instrument.sample_number')
    def add_data(self, data):
        if self.save_in_database:
            self.database_wrapper.insert_data(data)


    def start_stop(self, active_instrument):
        self.running = active_instrument.running
        if self.running and self.save_in_database:
            if len(self.measurement_name) == 0:
                GenericPopupMessage(message = 'No measurement selected').edit_traits()
                self.save_in_database = False
            else:
                if self.database_wrapper.get_description(self.measurement_name) is not self.measurement_description:
                            self.database_wrapper.set_table(self.measurement_name, self.measurement_description)
                self.database_wrapper.add_columns([active_instrument.x_units[0] +active_instrument.sweep_name,\
                                                    active_instrument.y_units[0] + active_instrument.sweep_name])



if __name__ == '__main__':
    l = logging.getLogger()
    console = logging.StreamHandler()
    l.addHandler(console)
    l.setLevel(logging.DEBUG)
    l.info('test')
    s = SQLPanel()
    s.configure_traits()
