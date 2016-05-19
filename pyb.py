"""
pyb — functions related to the pyboard
The pyb module contains specific functions related to the pyboard.
"""

# Time related functions
"""from __builtin__ import object"""


def delay(ms):  # Delay for the given number of milliseconds.
	"""
	:rtype : object
	"""
	pass


def udelay(us):  # Delay for the given number of microseconds.
	pass


def millis():  # Returns the number of milliseconds since the board was last reset.
	pass

	"""
	The result is always a micropython smallint (31-bit signed number), so after 2^30 milliseconds
	(about 12.4 days)
	this will start to return negative numbers.
	"""


def micros():  # Returns the number of microseconds since the board was last reset.
	pass

	"""
	The result is always a micropython smallint (31-bit signed number), so after 2^30 microseconds
	(about 17.8 minutes) this will start to return negative numbers.
	"""


def elapsed_millis(start):  # Returns the number of milliseconds which have elapsed since start.
	pass

	"""
	This function takes care of counter wrap, and always returns a positive number. This means it
	can be used
	to measure periods upto about 12.4 days.

	Example:

	start = def millis()
	while pyb.elapsed_millis(start) < 1000:
		# Perform some operation
	"""


def elapsed_micros(start):  # Returns the number of microseconds which have elapsed since start.
	pass

	"""
	This function takes care of counter wrap, and always returns a positive number.
	This means it can be used to measure periods upto about 17.8 minutes.

	Example:

	start = pyb.micros()
	while pyb.elapsed_micros(start) < 1000:
		# Perform some operation
		pass
	Reset related functions
	def hard_reset()
	Resets the pyboard in a manner similar to pushing the external RESET button.
	"""


def bootloader():  # Activate the bootloader without BOOT* pins.
	pass


# Interrupt related functions

def disable_irq():
	""" Disable interrupt requests. Returns the previous IRQ state: False/True for disabled/enabled
	IRQs respectively. This return value can be passed to enable_irq to restore the IRQ to its
	original state."""
	pass


def enable_irq(state=True):
	"""
	Enable interrupt requests. If state is True (the default value) then IRQs are enabled.
	If state is False then IRQs are disabled. The most common use of this function is to pass
	it the value
	returned by disable_irq to exit a critical section."""
	pass


# Power related functions

def freq(sysclk, hclk, pclk1, pclk2):
	"""
	If given no arguments, returns a tuple of clock frequencies: (sysclk, hclk, pclk1, pclk2).
	These correspond to:

	sysclk: frequency of the CPU
	hclk: frequency of the AHB bus, core memory and DMA
	pclk1: frequency of the APB1 bus
	pclk2: frequency of the APB2 bus
	If given any arguments then the function sets the frequency of the CPU, and the busses if
	additional arguments
	are given. Frequencies are given in Hz. Eg freq(120000000) sets sysclk (the CPU frequency) to
	120MHz.
	Note that not all values are supported and the largest supported frequency not greater than the
	given value will
	be selected.
	Supported sysclk frequencies are (in MHz):
	8, 16, 24, 30, 32, 36, 40, 42, 48, 54, 56, 60, 64, 72, 84, 96, 108, 120, 144, 168.

	The maximum frequency of hclk is 168MHz, of pclk1 is 42MHz, and of pclk2 is 84MHz.
	Be sure not to set frequencies above these values.

	The hclk, pclk1 and pclk2 frequencies are derived from the sysclk frequency using a prescaler
	(divider).
	Supported prescalers for hclk are: 1, 2, 4, 8, 16, 64, 128, 256, 512. Supported prescalers for
	pclk1 and pclk2 are:
	1, 2, 4, 8. A prescaler will be chosen to best match the requested frequency.

	A sysclk frequency of 8MHz uses the HSE (external crystal) directly and 16MHz uses the HSI
	(internal oscillator)
	directly. The higher frequencies use the HSE to drive the PLL (phase locked loop), and then use
	the output of the PLL.

	Note that if you change the frequency while the USB is enabled then the USB may become unreliable.
	It is best to
	change the frequency in boot.py, before the USB peripheral is started. Also note that sysclk
	frequencies below
	36MHz do not allow the USB to function correctly.
	"""
	pass


def wfi():
	""" Wait for an interrupt. This executies a wfi instruction which reduces power consumption of
	the MCU
	until an interrupt occurs, at which point execution continues."""
	pass


def standby():
	pass


def stop():
	pass


# Miscellaneous functions

def have_cdc():  # Return True if USB is connected as a serial device, False otherwise.
	"""
	Note

	This function is deprecated. Use def USB_VCP().isconnected() instead.
	"""
	pass


def main(*args, **kwargs):
	pass


class USB_HID:

	def send(self, b):
		pass


def hid(buttons, x=0, y=0, z=0):
	"""Takes a 4-tuple (or list) and sends it to the USB host (the PC) to signal a HID mouse-motion
	event.
	Note

	This function is deprecated. Use def USB_HID().send(...) instead.
	"""
	pass


def info(dump_alloc_table):  # Print out lots of information about the board.
	pass


def mount(device, mountpoint, *, readonly=False, mkfs=False):
	""" Mount a block device and make it available as part of the filesystem.
	device must be an object that provides the block protocol: """
	pass


def readblocks(self, blocknum, buf):
	pass


def writeblocks(self, blocknum, buf):  # (optional)
	pass


def count(self):
	pass


'''def sync(self):  # (optional)
	"""
	readblocks and writeblocks should copy data between buf and the block device, starting from
	block number blocknum
	on the device. buf will be a bytearray with length a multiple of 512. If writeblocks is not
	defined then the device
	is mounted read-only. The return value of these two functions is ignored.
	count should return the number of blocks available on the device. sync, if implemented,
	should sync the data on the device.
	The parameter mountpoint is the location in the root of the filesystem to mount the device.
	It must begin with a forward-slash.
	If readonly is True, then the device is mounted read-only, otherwise it is mounted read-write.
	If mkfs is True, then a new filesystem is created if one does not already exist.
	To unmount a device, pass None as the device and the mount location as mountpoint.
	"""
	pass'''


def repl_uart(uart):  # Get or set the UART object that the REPL is repeated on.
	pass


def rng():  # Return a 30-bit hardware generated random number.
	pass


def sync():  # Sync all file systems.
	pass


def unique_id():  # Returns a string of 12 bytes (96 bits), which is the unique ID for the MCU.
	pass


def usb_mode(*arguments, **keyword_arguments):
	pass

# Classes


class Accel:  # - accelerometer control

	def x(self, *args, **kwargs):
		pass

	def y(self, *args, **kwargs):
		pass

	def z(self, *args, **kwargs):
		pass

	def tilt(self, *args, **kwargs):
		pass

	def filtered_xyz(self, *args, **kwargs):
		pass

	def read(self, *args, **kwargs):
		pass

	def write(self, *args, **kwargs):
		pass


class ADC:  # - analog to digital conversion: read analog values on a pin
	pass


class CAN:  # - controller area network communication bus
	NORMAL = None
	MASK32 = None

	def __init__(self, *args, **kwargs):
		pass

	def init(self, *args, **kwargs):
		pass

	def setfilter(self, *args, **kwargs):
		pass

	def any(self, *args, **kwargs):
		pass

	def send(self, *args, **kwargs):
		pass

	def recv(self, *args, **kwargs):
		pass


class DAC:  # - digital to analog conversion
	pass


class ExtInt:  # - configure I/O pins to interrupt on external events
	IRQ_RAISING = IRQ_FALLING = IRQ_RISING_FALLING = 0

	def __init__(self, pin, mode, pull, callback):
		"""
		:param pin:
		:param mode: #["IRQ_RAISING", "IRQ_FALLING", "IRQ_RISING_FALLING"]
		:param pull: #["PULL_NONE", "PULL_UP", "PULL_DOWN"]
		:param callback:
		:return:
		"""

	def regs(self):
		pass

	def disable(self):
		pass

	def enable(self):
		pass

	def line(self):
		pass

	def swint(self):
		pass


class I2C:  # ---- a two-wire serial protocol
	MASTER = SLAVE = 0

	def __init__(self, side, mode, baudrate):
		self.MASTER = 1
		self.SLAVE = 0

	def deinit(self):
		pass

	def init(self, mode, *, addr, baudrate, gencall):
		pass

	def is_ready(self, addr):
		pass

	def mem_read(self, data, addr, memadddr, timeout, addr_size):
		pass

	def mem_write(self, data, addr, memadddr, timeout, addr_size):
		pass

	def recv(self, recv, addr, timeout):
		pass

	def scan(self):
		pass

	def send(self, data, addr, timeout):
		pass


class LCD:  # --- LCD control for the LCD touch-sensor pyskin

	def __init__(self, skin_position):
		print("LCD init", skin_position)

	def command(self, instr_data, buf):
		pass

	def contrast(self, value):
		pass

	def fill(self, colour):
		pass

	def get(self, x, y):
		return 1

	def light(self, value):
		pass

	def pixel(self, x, y, colour):
		pass

	def show(self):
		pass

	def text(self, str, x, y, colour):
		pass

	def write(self, str):
		print(str)


class LED:  # - LED object
	def __init__(self, id):
		print("LED init", id)

	def off(self):
		pass

	def on(self):
		pass

	def toggle(self):
		pass

	def intensity(self, value):
		pass


class Pin:  # - control I/O pins
	PULL_NONE = PULL_UP = PULL_DOWN = 1
	OUT_PP = None

	def __init__(self, id, mode, pul=None, af=None):
		pass

	def init(self, mode, pull, af):
		pass

	def dict(self, dictorary):
		pass

	def debug(self, state):
		pass

	def af_list(self):
		pass

	def mapper(self, fun):
		pass

	def value(self, v=None):
		pass

	def low(self, *args, **kwargs):
		pass

	def high(self, *args, **kwargs):
		pass

	def IN(self, *args, **kwargs):
		pass

	def board(self, *args, **kwargs):
		pass


class PinAF:  # - Pin Alternate Functions
	pass


class RTC:  # - real time clock

	def datetime(self, time=None):
		pass


class Servo:  # - 3-wire hobby servo driver
	pass


class SPI:  # - a master-driven serial protocol
	MASTER = None

	def __init__(self, a1, a2, baudrate):
		pass

	def send(self, *args, **kwargs):
		pass


class Switch:  # - switch object

	def __init__(self):
		pass

	@staticmethod
	def switch():
		return True

	def callback(self, *args, **kwargs):
		pass


class Timer:  # - control internal timers

	def __init__(self, c, freq=None, percentage=100):
		pass

	def init(self, *args, **kwargs):
		pass

	def deinit(self, *args, **kwargs):
		pass

	def channel(self, *args, **kwargs):
		pass

	def counter(self, *args, **kwargs):
		pass

	def source_freq(self, *args, **kwargs):
		pass

	def freq(self, *args, **kwargs):
		pass

	def prescaler(self, *args, **kwargs):
		pass

	def period(self, *args, **kwargs):
		pass

	def callback(self, *args, **kwargs):
		pass


class TimerChannel:  # - setup a channel for a timer
	pass


class UART:  # - duplex serial communication bus

	def __init__(self, bus, baudrate, bits, parity, stop, *, timeout, timeout_char, read_buf_len):
		pass

	def init(
		self, baudrate, bits=8, parity=None, stop=1, *, timeout=1000, timeout_char=0,
		read_buf_len=64):
		pass

	def deinit(self):
		pass

	def read(self, nrbytes):
		pass

	def readall(self):
		return 17

	def readchar(self):
		return 17

	def readinto(self, buf, nrbytes):
		return 17

	def readln(self):
		return 17

	def write(self, buf):
		return 5

	def writechar(self, char):
		pass

	def sendbreak(self):
		pass


class USB_VCP:  # - USB virtual comm port

	def write(self, *a, **k):
		pass