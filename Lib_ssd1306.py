# The MIT License (MIT)
#
# Copyright (c) 2014 Kenneth Henderick
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# pyb

# Constants
DISPLAYOFF          = 0xAE
SETCONTRAST         = 0x81
DISPLAYALLON_RESUME = 0xA4
DISPLAYALLON        = 0xA5
NORMALDISPLAY       = 0xA6
INVERTDISPLAY       = 0xA7
DISPLAYON           = 0xAF
SETDISPLAYOFFSET    = 0xD3
SETCOMPINS          = 0xDA
SETVCOMDETECT       = 0xDB
SETDISPLAYCLOCKDIV  = 0xD5
SETPRECHARGE        = 0xD9
SETMULTIPLEX        = 0xA8
SETLOWCOLUMN        = 0x00
SETHIGHCOLUMN       = 0x10
SETSTARTLINE        = 0x40
MEMORYMODE          = 0x20
COLUMNADDR          = 0x21
PAGEADDR            = 0x22
COMSCANINC          = 0xC0
COMSCANDEC          = 0xC8
SEGREMAP            = 0xA0
CHARGEPUMP          = 0x8D
EXTERNALVCC         = 0x10
SWITCHCAPVCC        = 0x20
SETPAGEADDR         = 0xB0
SETCOLADDR_LOW      = 0x00
SETCOLADDR_HIGH     = 0x10
ACTIVATE_SCROLL                      = 0x2F
DEACTIVATE_SCROLL                    = 0x2E
SET_VERTICAL_SCROLL_AREA             = 0xA3
RIGHT_HORIZONTAL_SCROLL              = 0x26
LEFT_HORIZONTAL_SCROLL               = 0x27
VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL = 0x29
VERTICAL_AND_LEFT_HORIZONTAL_SCROLL  = 0x2A

# I2C devices are accessed through a Device ID. This is a 7-bit
# value but is sometimes expressed left-shifted by 1 as an 8-bit value.
# A pin on SSD1306 allows it to respond to ID 0x3C or 0x3D. The board
# I bought from ebay used a 0-ohm resistor to select between "0x78"
# (0x3c << 1) or "0x7a" (0x3d << 1). The default was set to "0x78"
DEVID = 0x3c

# I2C communication here is either <DEVID> <CTL_CMD> <command byte>
# or <DEVID> <CTL_DAT> <display buffer bytes> <> <> <> <>...
# These two values encode the Co (Continuation) bit as b7 and the
# D/C# (Data/Command Selection) bit as b6.
CTL_CMD = 0x80
CTL_DAT = 0x40


def init():
	d = SSD1306(pinout={'sda': 'X10', 'scl': 'X9'}, height=64, external_vcc=False)
	d.poweron()
	d.init_display()
	return d


class SSD1306(object):

	def __init__(
		self, pinout, height=32, external_vcc=True,
		i2c_devid=DEVID
	):
		self.external_vcc = external_vcc
		self.height       = 32 if height == 32 else 64
		self.pages        = int(self.height / 8)
		self.columns      = 128

		# Infer interface type from entries in pinout{}
		if 'dc' in pinout:
			# SPI
			rate = 16 * 1024 * 1024
			self.spi = pyb.SPI(2, pyb.SPI.MASTER, baudrate=rate, polarity=1, phase=0)  # SCK: Y6: MOSI: Y8
			self.dc  = pyb.Pin(pinout['dc'], pyb.Pin.OUT_PP, pyb.Pin.PULL_DOWN)
			self.res = pyb.Pin(pinout['res'], pyb.Pin.OUT_PP, pyb.Pin.PULL_DOWN)
			self.offset = 0
		else:
			# Infer bus number from pin
			if pinout['sda'] == 'X10':         # FB: Orig bug: was X9
				self.i2c = pyb.I2C(1)
			else:
				self.i2c = pyb.I2C(2)
			self.i2c.init(pyb.I2C.MASTER, baudrate=400000)  # 400kHz
			self.devid = i2c_devid
			# used to reserve an extra byte in the image buffer AND as a way to infer the interface type
			self.offset = 1
			# I2C command buffer
			self.cbuffer = bytearray(2)
			self.cbuffer[0] = CTL_CMD
		self.buffer       = bytearray(self.offset + self.pages * self.columns)

	def clear(self):
		# self.buffer = bytearray(self.offset + self.pages * self.columns)
		if self.offset == 1:
			self.buffer[0] = CTL_DAT

	def write_command(self, command_byte):
		if self.offset == 1:
			self.cbuffer[1] = command_byte
			self.i2c.send(self.cbuffer, addr=self.devid, timeout=5000)
		else:
			self.dc.low()
			self.spi.send(command_byte)

	def invert_display(self, invert):
		self.write_command(INVERTDISPLAY if invert else NORMALDISPLAY)

	def display(self):
		self.write_command(COLUMNADDR)
		self.write_command(0)
		self.write_command(self.columns - 1)
		self.write_command(PAGEADDR)
		self.write_command(0)
		self.write_command(self.pages - 1)
		if self.offset == 1:
			self.i2c.send(self.buffer, addr=self.devid, timeout=5000)
		else:
			self.dc.high()
			self.spi.send(self.buffer)

	def set_pixel(self, x, y, state):
		index = x + (int(y / 8) * self.columns)
		if state:
			self.buffer[self.offset + index] |= (1 << (y & 7))
		else:
			self.buffer[self.offset + index] &= ~(1 << (y & 7))

	def init_display(self):
		chargepump = 0x10 if self.external_vcc else 0x14
		precharge  = 0x22 if self.external_vcc else 0xf1
		multiplex  = 0x1f if self.height == 32 else 0x3f
		compins    = 0x02 if self.height == 32 else 0x12
		contrast   = 0xff   # 0x8f if self.height == 32 else (0x9f if self.external_vcc else 0x9f)
		data = [
			DISPLAYOFF,
			SETDISPLAYCLOCKDIV, 0x80,
			SETMULTIPLEX, multiplex,
			SETDISPLAYOFFSET, 0x00,
			SETSTARTLINE | 0x00,
			CHARGEPUMP, chargepump,
			MEMORYMODE, 0x00,
			SEGREMAP | 0x10,
			COMSCANDEC,
			SETCOMPINS, compins,
			SETCONTRAST, contrast,
			SETPRECHARGE, precharge,
			SETVCOMDETECT, 0x40,
			DISPLAYALLON_RESUME,
			NORMALDISPLAY,
			DISPLAYON
		]
		for item in data:
			self.write_command(item)
		self.clear()
		self.display()

	def poweron(self):
		if self.offset == 1:
			pyb.delay(10)
		else:
			self.res.high()
			pyb.delay(1)
			self.res.low()
			pyb.delay(10)
			self.res.high()
			pyb.delay(10)

	def poweroff(self):
		self.write_command(DISPLAYOFF)

	def contrast(self, contrast):
		self.write_command(SETCONTRAST)
		self.write_command(contrast)

	def set_start_end_cols(self, start_col=0, end_col=None):
		if end_col is None:
			end_col = self.columns - 1
		if start_col < 0 or start_col > self.columns - 1:
			raise ValueError('Start column must be between 0 and %d.' % (self.columns - 1,))
		if end_col < start_col or end_col > self.columns - 1:
			raise ValueError(
				'End column must be between the start column (%d) and %d.' % (
					start_col, self.columns - 1))

		self.write_command(COLUMNADDR)
		self.write_command(start_col)  # Start column
		self.write_command(end_col)  # End column

	def set_start_end_pages(self, start_page=0, end_page=None):
		if end_page is None:
			end_page = self.pages - 1
		if start_page < 0 or start_page > self.pages - 1:
			raise ValueError('Start page must be between 0 and %d.' % (self.pages - 1,))
		if end_page < start_page or end_page > self.pages - 1:
			raise ValueError(
				'End page must be between the start page (%d) and %d.' % (
					start_page, self.pages - 1
				)
			)

		self.write_command(PAGEADDR)
		self.write_command(start_page)  # Page start address. (0 = reset)
		self.write_command(end_page)    # Page end address.


display = SSD1306(pinout={'sda': 'X10', 'scl': 'X9'}, height=64, external_vcc=False)
'''
# I2C connected to Y9, Y10 (I2C bus 2)
display = SSD1306(pinout={'sda': 'Y10',
						'scl': 'Y9'},
				height=64'''

display.poweron()
display.init_display()


if __name__  == '__main__':
	import pyb
	# from Lib_ssd1306 import SSD1306

	'''# SPI
	display  =  SSD1306(pinout={'dc': 'Y3',
								'res': 'Y4'},
						height=64,
						external_vcc=False)'''

	# I2C connected to X9, X10 (I2C bus 1)
	display = SSD1306(pinout={'sda': 'X10', 'scl': 'X9'}, height=64, external_vcc=False)
	'''
	# I2C connected to Y9, Y10 (I2C bus 2)
	display = SSD1306(pinout={'sda': 'Y10',
	'scl': 'Y9'},
	height=64,
	external_vcc=False)'''

	led_red = pyb.LED(1)
	led_red.off()

	try:
		display.poweron()
		display.init_display()

		x = 0
		y = 0
		direction_x = True
		direction_y = True

		while True:
			# Clear the previous lines
			prev_x = x
			prev_y = y

			# Move bars
			x += (1 if direction_x else -1)
			y += (1 if direction_y else -1)

			# Bounce back, if required
			if x == 128:
				direction_x = False
				x = 126
			elif x == -1:
				direction_x = True
				x = 1
			if y == 64:
				direction_y = False
				y = 63
			elif y == -1:
				direction_y = True
				y = 1

			# Draw new lines
			for i in range(64):
				display.set_pixel(prev_x, i, False)
				display.set_pixel(x, i, True)
			for i in range(128):
				display.set_pixel(i, prev_y, False)
				display.set_pixel(i, y, True)

			# Make sure the corners are active
			display.set_pixel(0, 0, True)
			display.set_pixel(127, 0, True)
			display.set_pixel(0, 63, True)
			display.set_pixel(127, 63, True)

			# Write display buffer
			display.display()

	except Exception as ex:
		led_red.on()
		print('Unexpected error: {0}'.format(ex))
		display.poweroff()
		i2c = pyb.I2C(1, pyb.I2C.MASTER)