def delay(ms):  # Delay for the given number of milliseconds.
    """
    :rtype : object
    """
    pass


def udelay(us):  # Delay for the given number of microseconds.
    pass


def millis():  # Returns the number of milliseconds since the board was last reset.
    pass


def micros():  # Returns the number of microseconds since the board was last reset.
    pass


def elapsed_millis(start):  # Returns the number of milliseconds which have elapsed since start.
    pass


def elapsed_micros(start):  # Returns the number of microseconds which have elapsed since start.
    pass


def bootloader():  # Activate the bootloader without BOOT* pins.
    pass


# Interrupt related functions

def disable_irq():
    pass


def enable_irq(state=True):
    pass


# Power related functions

def freq(sysclk, hclk, pclk1, pclk2):
    pass


def wfi():
    pass


def standby():
    pass


def stop():
    pass


# Miscellaneous functions

def have_cdc():  # Return True if USB is connected as a serial device, False otherwise.
    pass


def main(*args, **kwargs):
    pass


class USB_HID:

    def send(self, b):
        pass


def hid(buttons, x=0, y=0, z=0):
    pass


def info(dump_alloc_table):  # Print out lots of information about the board.
    pass


def mount(device, mountpoint, *, readonly=False, mkfs=False):
    pass


def readblocks(self, blocknum, buf):
    pass


def writeblocks(self, blocknum, buf):  # (optional)
    pass


def count(self):
    pass


def repl_uart(uart):
    pass


def rng():
    pass


def sync():
    pass


def unique_id():
    pass


def usb_mode(*arguments, **keyword_arguments):
    pass

# Classes


class ADC:
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
        pass

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