import pyb
from errors import IllegalError
# from buttons import *

INFO = "Info"
ERROR = "ERROR"
FATAL_ERROR = "### FATAL ERROR ###"
WARNING = "WARNING"
yy = 0
# b4 = back()
# del b4
locked = True
PyBoard = False


def init():
    global locked, PyBoard
    locked = False
    try:
        raise PermissionError("LOCKED!!")
    except NameError:
        PyBoard = True
    except PermissionError:
        pass


def _lock():
    pass
    """global locked
    if locked:
        try:
            raise PermissionError("LOCKED!!")
        except NameError:
            raise MemoryError("LOCKED!!")"""


def log(log_file, category, info):
    # _lock()
    with open("Log_files/" + str(log_file) + ".log", "a") as file:
        if category is not None:
            file.write("[" + str(category) + "]: ")
            file.write(" " * (24 - len(category)))
            file.write(info)
        file.write("\n")


def random_int(min_number, max_number):
    # _lock()
    r_int = int(min_number + ((max_number + 1 - min_number) * (pyb.rng() / 1073741823)))
    return r_int


def prt(*text, sep="", end="\n", flush=False):
    # _lock()
    text_string = ""
    for variable in range(len(text)):
        text_string += str(text[variable])
        if variable < len(text) - 1:
            text_string += str(sep)
    text_string2 = text_string
    print(text_string2, end=end, flush=flush)
    return text_string2


def pos(x, y, o=0):
    # _lock()
    if o == 1:
        return x, y
    elif o == 2:
        return y, 160 - 1 - x
    if o == 3:
        return 128 - 1 - y, 160 - 1 - x
    else:
        return 128 - 1 - y, x


def toggle(var):
    # _lock()
    return not bool(var)


def rectangle(file, mode, value, x1, y1, x2, y2, width=160, height=128):
    global yy
    # _lock()
    with open(str(file), str(mode)) as f:
        for x in range(x1, x2 + 1):
            for yy in range(y1, y2 + 1):
                if x >= height:
                    break
                else:
                    f.write(str(value))
            f.seek(yy * width + x1)


def delay(time, unit="ms"):
    # _lock()
    if unit == "s":
        pyb.udelay(round(time * 1000000) - 43)
    elif unit == "ms":
        pyb.udelay(round(time * 1000) - 43)
    elif unit == "us" or "µs":
        pyb.udelay(round(time) - 43)
    else:
        raise IllegalError('invalid option for "unit"')


def fix_20_digit_8_dec_number(value):
    # _lock()
    value *= 1000
    value = round(value)
    value *= 100000
    return value


def rgb(red, green, blue):                     # Renamed from "rbg24_16" to "rgb"
    """ Convert R, G, B values to packed 16 bits integer """
    # _lock()
    red &= 0xF8                               # Keep 5 MS bits
    green &= 0xFC                               # Keep 6 MS bits
    blue &= 0xF8                               # Keep 5 MS bits
    return red << 8 | green << 3 | blue >> 3         # Packed 16 bits


def rgb_16_24(colour):
    # _lock()
    red = colour & 0b1111100000000000
    green = colour & 0b0000011111100000
    blue = colour & 0b0000000000011111
    # print("r, g, b: ", r, g, b)
    return red >> 8, green >> 3, blue << 3


def out_of_bounds(value, minimum, maximum):
    # _lock()
    if value < minimum:
        return minimum
    elif value > maximum:
        return maximum
    else:
        return value


def hex_rgb(colour):
    # _lock()
    """ Convert R, G, B values to packed 16 bits integer """
    r = colour >> 16
    g = (colour >> 8) - (r << 8)
    b = colour - (g << 8) - (r << 16)
    r &= 0xF8                               # Keep 5 MS bits
    g &= 0xFC                               # Keep 6 MS bits
    b &= 0xF8                               # Keep 5 MS bits
    return r << 8 | g << 3 | b >> 3         # Packed 16 bits


def mean_value(*values):
    # _lock()
    total = 0
    for value in values:
        total += value
    total /= len(values)
    return total