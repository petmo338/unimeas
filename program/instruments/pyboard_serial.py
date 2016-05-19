import logging
import serial
import struct
# from serial.tools.list_ports import comports
# import os
from traits.api import HasTraits, Instance, Bool, Dict, \
	List, Unicode, Str, Event, Button, Float, Int
from traitsui.api import View, Item, ButtonEditor, \
	EnumEditor, Label, HGroup, Handler
from time import time  # , sleep
from pyface.timer.api import Timer

# from . i_instrument import IInstrument
logger = logging.getLogger(__name__)


class PyboardHandler(Handler):
	def closed(self, info, is_ok):
		if info.object.serialport is not None:
			if info.object.serialport.isOpen():
				info.object.serialport.close()

# @provides(IInstrument)


class PyBoardSerial(HasTraits):
	"""Instrument for communication with PyBoard"""

	start_stop = Event
	refresh_list = Button

	button_label = Str('Start')

	output_unit = 0
	timebase = 0
	acquired_data = List(Dict)
	available_ports = List(Str)
	serialport = Instance(serial.Serial)
	portname = Str
	timer = Instance(Timer)
	name = Unicode('PyBoardSerial')
	measurement_info = Dict()
	x_units = Dict({0: 'SampleNumber', 1: 'Time'})
	y_units = Dict({0: 'NOx'})
	running = Bool(False)
	output_channels = Dict({0: 'chan0'})
	enabled_channels = List(Bool)
	acq_start_time = Float
	sample_nr = Int

	serial_out = Str

	traits_view = View(
		HGroup(
			Label('Device: '), Item(
				'portname', show_label=False, editor=EnumEditor(name='available_ports'),
				enabled_when='not running'
			),
			Item('refresh_list')
		),
		Item('start_stop', label='Start/stop acqusistion', editor=ButtonEditor(
			label_value='button_label')
		),
		Item('serial_out', label='Data out', style="readonly"),
		handler=PyboardHandler)

	def _enabled_channels_default(self):
		return [True]

	def _available_ports_default(self):
		import serial.tools.list_ports as lp
		ll = []
		for p in lp.grep('PyBoard'):
			ll.append(p.device)
		return ll

	def _refresh_list_fired(self):
		self.available_ports = self._available_ports_default()

	def _portname_changed(self):
		self.serialport = None

	def add_data(self):
		if not self.running:
			return
		# b = bytearray(2)
		self.sample_nr += 1
		measurement_time = time() - self.acq_start_time
		b = self.serialport.read_all()
		# print(len(b))
		if len(b) == struct.calcsize('hHH'):
			(nox_ppm, lambda_linear, oxygen_millivolt) = struct.unpack("hHH", b)
			self.serial_out = str(nox_ppm)
			dict_data = dict()
			for i, enabled in enumerate(self.enabled_channels):
				dict_data[
					self.output_channels[i]] = (
					dict(
						{self.x_units[0]: self.sample_nr, self.x_units[1]: measurement_time}),
						dict({self.y_units[0]: nox_ppm}))
				logger.info(dict_data)
			self.acquired_data.append(dict_data)
		self.timer = Timer.singleShot(
			max(0, ((float(self.sample_nr)) - measurement_time) * 1000), self.add_data)

	def start(self):
		self.running = True
		self.acq_start_time = time()
		self.sample_nr = 0
		if self.serialport is None:
			try:
				self.serialport = serial.Serial(self.portname, 115200, timeout=0.2)
			except Exception as e:
				logger.error(e)
				self.stop()
				return
		else:
			self.serialport.open()
		# self.serialport.write('a')
		self.timer = Timer.singleShot(900, self.add_data)

	def stop(self):
		logger.info('stop()')
		self.running = False
		if self.serialport is not None:
			# self.serialport.write('b')
			self.serialport.close()

	def _start_stop_fired(self):
		if self.portname == '':
			return
		if self.running:
			self.button_label = 'Start'
			self.stop()
		else:
			self.button_label = 'Stop'
			self.start()


if __name__ == '__main__':
	l = logging.getLogger()
	console = logging.StreamHandler()
	l.addHandler(console)
	l.setLevel(logging.DEBUG)
	l.info('test')
	n = PyBoardSerial()
	n.configure_traits()