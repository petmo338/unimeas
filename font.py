"""
This program prints characters on the OLED display SSD1306. 128x64.
"""

from Display_graphic import Display
try:
    from pyb import delay
except NameError:
    pass
# from bytearray import bytearray
# from errors import Warn, ValueTest, ArgumentError

oled = Display()


class Chars:
    X_MAX           = 128 							# Display's number of pixels in x-direction
    Y_MAX           = 64 							# Display's number of pixels in y-direction
    X_DISPLAY_MAX   = X_MAX - 1
    Y_DISPLAY_MAX   = Y_MAX - 1
    CHAR_MAX_HEIGHT = 6
    CHAR_MIN_HEIGHT = -1
    Y_CHAR_MIN      = 1  									# 2 pixels margin to the below
    Y_CHAR_MAX      = Y_DISPLAY_MAX - CHAR_MAX_HEIGHT - 2   # 2 pixels margin above char
    CENTER          = 63
    X_CHAR_MIN      = 2  									# 2 pixels margin to the left
    X_CHAR_MAX      = X_MAX - 4 							# 2 pixels margin to the right
    X_PRINT_MAX     = X_CHAR_MAX - 2
    ROW_SPACE       = 9 				# Height in pixels of a char line (incl space between lines)
    ROWS            = Y_DISPLAY_MAX // ROW_SPACE 	# Max number of char lines that fits on display

    x = 0  		# Start x-position for active area
    y = 0  		# Start y-position for active area
    x_pos = 0
    y_pos = 0
    width = 6  		# Start width of char
    row = 1  	# Current row number (one row uses 8 pixles + 1 px space)
    test = False
    chrs = 0
    text = ""  	# Text out
    colour = 0  # Char colour
    fg = 0
    write_chrs = 0
    chars_size = 1
    bg = 0
    char_pixels = bytearray(())  # Font list char pattern: columns
    characthers = {
        "A": [bytearray([0b01111000, 0b00010110, 0b00010001, 0b00010110, 0b01111000]), 6],
        "B": [bytearray([0b01111111, 0b01001001, 0b01001001, 0b00110110]), 5],
        "C": [bytearray([0b00111110, 0b01000001, 0b01000001, 0b01000001]), 5],
        "D": [bytearray([0b01111111, 0b01000001, 0b01000001, 0b00111110]), 5],
        "E": [bytearray([0b01111111, 0b01001001, 0b01001001, 0b01000001]), 5],
        "F": [bytearray([0b01111111, 0b00001001, 0b00001001, 0b00000001]), 5],
        "G": [bytearray([0b00111110, 0b01000001, 0b01001001, 0b01001001, 0b01111001]), 6],
        "H": [bytearray([0b01111111, 0b00001000, 0b00001000, 0b01111111]), 5],
        "I": [bytearray([0b01000001, 0b01111111, 0b01000001]), 4],
        "J": [bytearray([0b00100000, 0b01000000, 0b01000000, 0b00111111]), 5],
        "K": [bytearray([0b01111111, 0b00001000, 0b00010100, 0b00100010, 0b01000001]), 6],
        "L": [bytearray([0b01111111, 0b01000000, 0b01000000, 0b01000000]), 5],
        "M": [bytearray([0b01111111, 0b00000010, 0b00001100, 0b00000010, 0b01111111]), 6],
        "N": [bytearray([0b01111111, 0b00000100, 0b00001000, 0b00010000, 0b01111111]), 6],
        "O": [bytearray([0b00111110, 0b01000001, 0b01000001, 0b01000001, 0b00111110]), 6],
        "P": [bytearray([0b01111111, 0b00001001, 0b00001001, 0b00000110]), 5],
        "Q": [bytearray([0b00111110, 0b01000001, 0b01010001, 0b00100001, 0b01011110]), 6],
        "R": [bytearray([0b01111111, 0b00001001, 0b00011001, 0b01100110]), 5],
        "S": [bytearray([0b01000110, 0b01001001, 0b01001001, 0b00110001]), 5],
        "T": [bytearray([0b00000001, 0b00000001, 0b01111111, 0b00000001, 0b00000001]), 6],
        "U": [bytearray([0b00111111, 0b01000000, 0b01000000, 0b01000000, 0b00111111]), 6],
        "V": [bytearray([0b00001111, 0b00110000, 0b01000000, 0b00110000, 0b00001111]), 6],
        "W": [bytearray([0b00111111, 0b01000000, 0b00111100, 0b01000000, 0b00111111]), 6],
        "X": [bytearray([0b01100011, 0b00010100, 0b00001000, 0b00010100, 0b01100011]), 6],
        "Y": [bytearray([0b00000011, 0b00000100, 0b01111000, 0b00000100, 0b00000011]), 6],
        "Z": [bytearray([0b01100001, 0b01010001, 0b01001001, 0b01000101, 0b01000011]), 6],
        "1": [bytearray([0b00000010, 0b01111111]), 3],
        "2": [bytearray([0b01100010, 0b01010001, 0b01001001, 0b01000110]), 5],
        "3": [bytearray([0b01000001, 0b01001001, 0b01001001, 0b00110110]), 5],
        "4": [bytearray([0b00001111, 0b00001000, 0b00001000, 0b01111111]), 5],
        "5": [bytearray([0b01001111, 0b01001001, 0b01001001, 0b00111001]), 5],
        "6": [bytearray([0b00111110, 0b01001001, 0b01001001, 0b00110001]), 5],
        "7": [bytearray([0b01000001, 0b00110001, 0b00001101, 0b00000011]), 5],
        "8": [bytearray([0b00110110, 0b01001001, 0b01001001, 0b00110110]), 5],
        "9": [bytearray([0b00100110, 0b01001001, 0b01001001, 0b00111110]), 5],
        "0": [bytearray([0b00111110, 0b01000001, 0b01000001, 0b00111110]), 5],
        "a": [bytearray([0b00111000, 0b01000100, 0b00100100, 0b01111100]), 5],
        "b": [bytearray([0b01111111, 0b01000100, 0b01000100, 0b00111000]), 5],
        "c": [bytearray([0b00111000, 0b01000100, 0b01000100, 0b01000100]), 5],
        "d": [bytearray([0b00111000, 0b01000100, 0b01000100, 0b01111111]), 5],
        "e": [bytearray([0b00111000, 0b01010100, 0b01010100, 0b01011000]), 5],
        "f": [bytearray([0b00000100, 0b01111110, 0b00000101]), 4],
        "g": [bytearray([0b10011000, 0b10100100, 0b10100100, 0b01111100]), 5],
        "h": [bytearray([0b01111111, 0b00000100, 0b00000100, 0b01111000]), 5],
        "i": [bytearray([0b01111101]), 2],
        "j": [bytearray([0b10000000, 0b10000000, 0b01111101]), 4],
        "k": [bytearray([0b01111111, 0b00010000, 0b00101000, 0b01000100]), 5],
        "l": [bytearray([0b01111111]), 2],
        "m": [bytearray([0b01111100, 0b00000100, 0b01111000, 0b00000100, 0b01111000]), 6],
        "n": [bytearray([0b01111100, 0b00001000, 0b00000100, 0b01111000]), 5],
        "o": [bytearray([0b00111000, 0b01000100, 0b01000100, 0b00111000]), 5],
        "p": [bytearray([0b11111100, 0b00100100, 0b00100100, 0b00011000]), 5],
        "q": [bytearray([0b00011000, 0b00100100, 0b00100100, 0b11111100]), 5],
        "r": [bytearray([0b01111100, 0b00001000, 0b00000100, 0b00000100]), 5],
        "s": [bytearray([0b01001000, 0b01010100, 0b01010100, 0b00100100]), 5],
        "t": [bytearray([0b00000100, 0b00111111, 0b01000100]), 4],
        "u": [bytearray([0b00111100, 0b01000000, 0b01000000, 0b01111100]), 5],
        "v": [bytearray([0b00001100, 0b00110000, 0b01000000, 0b00110000, 0b00001100]), 6],
        "w": [bytearray([0b00111100, 0b01000000, 0b00111000, 0b01000000, 0b00111100]), 6],
        "x": [bytearray([0b01000100, 0b00101000, 0b00010000, 0b00101000, 0b01000100]), 6],
        "y": [bytearray([0b10001100, 0b01010000, 0b00100000, 0b00010000, 0b00001100]), 6],
        "z": [bytearray([0b01000100, 0b01100100, 0b01010100, 0b01001100, 0b01000100]), 6],
        ".": [bytearray([0b01100000, 0b01100000]), 3],
        ":": [bytearray([0b01100110, 0b01100110]), 3],
        ",": [bytearray([0b10110000, 0b01110000]), 3],
        "!": [bytearray([0b01011111]), 3],
        "?": [bytearray([0b00000010, 0b00000001, 0b01011001, 0b00000101, 0b00000010]), 6],
        "#": [bytearray([0b00010100, 0b01111111, 0b00010100, 0b01111111, 0b00010100]), 6],
        "$": [bytearray([0b00100100, 0b00101010, 0b01111111, 0b00101010, 0b00010010]), 6],
        "%": [bytearray([0b01000011, 0b00110011, 0b00001000, 0b01100110, 0b01100001]), 6],
        "&": [bytearray([0b00110000, 0b01001110, 0b01011101, 0b00100010, 0b01010000]), 6],
        "'": [bytearray([0b00000111]), 3],
        '"': [bytearray([0b00000111, 0b00000000, 0b00000111]), 5],
        "(": [bytearray([0b00011100, 0b00100010, 0b01000001]), 4],
        ")": [bytearray([0b01000001, 0b00100010, 0b00011100]), 4],
        "*": [bytearray([0b00101010, 0b00011100, 0b00111110, 0b00011100, 0b00101010]), 6],
        "+": [bytearray([0b00001000, 0b00001000, 0b00111110, 0b00001000, 0b00001000]), 6],
        "-": [bytearray([0b00001000, 0b00001000, 0b00001000]), 4],
        "/": [bytearray([0b01000000, 0b00110000, 0b00001000, 0b00000110, 0b00000001]), 6],
        ";": [bytearray([0b10110110, 0b01110110]), 3],
        "<": [bytearray([0b00001000, 0b00010100, 0b00010100, 0b00100010]), 5],
        ">": [bytearray([0b00100010, 0b00010100, 0b00010100, 0b00001000]), 5],
        "=": [bytearray([0b00010100, 0b00010100, 0b00010100, 0b00010100, 0b00010100]), 6],
        "@": [
            bytearray([
                0b00011100, 0b00100010, 0b01001001, 0b01010101, 0b00111101, 0b10000010,
                0b01111100]), 8],
        "[": [bytearray([0b01111111, 0b01000001, 0b01000001]), 4],
        "\\": [bytearray([0b00000001, 0b00000110, 0b00001000, 0b00110000, 0b01000000]), 6],
        "]": [bytearray([0b01000001, 0b01000001, 0b01111111]), 4],
        "_": [bytearray([0b01000000, 0b01000000, 0b01000000, 0b01000000, 0b01000000]), 6],
        "{": [bytearray([0b00001000, 0b01110111, 0b01000001]), 4],
        "|": [bytearray([0b00000000, 0b11111111]), 4],
        "}": [bytearray([0b01000001, 0b01110111, 0b00001000]), 4],
        "`": [bytearray([0b00000001, 0b00000010]), 3],
        "~": [bytearray([0b00001000, 0b00000100, 0b00001000, 0b00010000, 0b00001000]), 6],
        "^": [bytearray([0b00000100, 0b00000010, 0b00000001, 0b00000010, 0b00000100]), 6],
        "Å": [bytearray([0b01110000, 0b00101010, 0b00100101, 0b00101010, 0b01110000]), 6],
        "Ä": [bytearray([0b01110000, 0b00101001, 0b00100100, 0b00101001, 0b01110000]), 6],
        "Ö": [bytearray([0b00111101, 0b01000010, 0b01000010, 0b01000010, 0b00111101]), 6],
        "å": [bytearray([0b00110000, 0b01001011, 0b00101011, 0b01111000]), 5],
        "ä": [bytearray([0b00111001, 0b01000100, 0b00100100, 0b01111101]), 5],
        "ö": [bytearray([0b00111001, 0b01000100, 0b01000100, 0b00111001]), 5],
        "É": [bytearray([0b01111100, 0b01010110, 0b01010101, 0b01000100]), 5],
        "é": [bytearray([0b00111000, 0b01010110, 0b01010101, 0b01011000]), 5],
        "–": [bytearray([0b00001000, 0b00001000, 0b00001000, 0b00001000, 0b00001000]), 6],
        "°": [bytearray([0b00000110, 0b00001001, 0b00001001, 0b00000110]), 5],
        "•": [bytearray([0b00011000, 0b00111100, 0b00111100, 0b00011000]), 5],
        " ": [bytearray([]), 5],
        "\t": [bytearray([]), 20 - (x - x_pos) % 20],
        "\x00": [bytearray([
            0b01111110, 255 - 0b00000100, 255 - 0b00000010, 255 - 0b01010010,
            255 - 0b00001010, 255 - 0b00000100, 0b01111110]), 8]}

    # Implemented chars
    lista = "!#$%&'\"()*+,-./ 0123456789:;<=>?@\nABCDEFGHIJKLMNOPQRSTUVWXYZ\t\[\
            \]_abcdefghijklmnopqrstuvwxyzÅÄÖåäöÉé{|}`~^°•"

    def _row(self, newline=False):
        """
        This method controlles newlines.

        :param newline: Do a newline
        """
        if (self.x > self.X_CHAR_MAX - self.width) or newline:
            if self.ROWS >= self.row > 0:
                self.row += self.optisize(1)
            else:
                if self.y <= self.Y_CHAR_MAX:
                    self.y_pos += self.optisize(self.ROW_SPACE)
                    self.write_chrs += 1
                else:
                    self.y_pos = self.Y_DISPLAY_MAX + 14
            self.x = self.x_pos
            # log("typsnitt", INFO, "Newline")
        if self.ROWS >= self.row > 0:  # Line
            self.y = self.Y_DISPLAY_MAX - (self.Y_CHAR_MAX - (self.row - 1) * self.ROW_SPACE)
        else:
            self.y -= 2 * (self.chars_size - 1)

    def optisize(self, value):
        return value * self.chars_size

    @micropython.native
    def _char_out(self, pixels, width):  # This method prints out the char
        """
        This method prints out the text you have entered on the display.

        :param pixels: Pixels to draw
        :param width: Character's width
        """
        self.width = width
        self.char_pixels = pixels
        self._row()
        self.chrs += 1
        x = self.x 	 # Create a local copy of self.x and self.y
        y = self.y + 1
        bits = bytearray([128, 64, 32, 16, 8, 4, 2, 1])  # Make 8 bits (one byte)
        for columns in self.char_pixels:
            for bit in bits:  		# Test if bit is 0 or 1
                if columns - bit >= 0:  # if bit is 1: draw a pixel on the x and y *cordinates*
                    columns -= bit
                    if not self.test:
                        if self.chars_size == 1:
                            oled.pixel(x, y, self.colour)    # Draw the pixel
                        else:
                            oled.rectangle(
                                x, y, x + (self.chars_size - 1),
                                y + (self.chars_size - 1), self.colour)
                y -= self.optisize(1)    		# Go up one pixel
            y = self.y + 1  # If the byte is completed, reset x
            x += self.optisize(1)  		# Go one pixel right
        self.x += self.optisize(self.width)  	# Y += char's width
        self.width = 0
        self.char_pixels = bytearray([])

    def _char_in(self, char=None):  # This method says how the char look
        """
        This method tells how the characters look and their width.

        :param char: Char that will be printed
        """

        if char in self.characthers.keys():
            self._char_out(*self.characthers.get(char))

        elif char is "\n":  # newline
            self._row(newline=True)

        else:  # Non-implemented chars are shown as a filled rectangle
            self._char_out(*self.characthers.get("\x00"))

    def write(
        self, *args, row=0, colour=1, x_pos=X_CHAR_MIN,
        y_pos=Y_DISPLAY_MAX - (Y_CHAR_MAX - (1 - 1) * ROW_SPACE), sep="", test=False, size=1
    ):
        """
        This method writes text on the display.
        :param args: Text to print on the display
        :param row: Row that the text will be printed on (there are LINES rows)
        :param colour: Text colour
        :param x_pos: X-position to print the text on
        :param y_pos: Y-position to print the text on
        :param test: If test
        :return: Text that has been printed on the display
        """
        if y_pos == self.Y_DISPLAY_MAX - (self.Y_CHAR_MAX - (1 - 1) * self.ROW_SPACE) and row == 0:
            row = 1
        self.x = x_pos
        self.y = y_pos
        self.write_chrs = 0
        self.chars_size = size
        self.y_pos = y_pos
        self.x_pos = x_pos
        self.row = self.optisize(row)
        self._row()
        self.colour = colour
        self.test = test
        for variable in range(len(args)):
            self.text += str(args[variable])
            if variable < len(args) - 1:
                self.text += str(sep)

        for c in self.text:
            self._char_in(c)

        text = self.text
        self.text = ""
        if self.test:
            self.test = False
            return self.row, self.x - self.X_CHAR_MIN, text, self.write_chrs
        self.test = False
        oled.show()
        return text

    def row_fill(self, row, colour=0, left=X_CHAR_MIN, right=X_PRINT_MAX, size=1):
        """
        This method fills a row woth a colour.
        :param row: Row that will be filled
        :param colour: Colour to fill the row with
        :param left: Left border
        :param right: Right border
        """
        # Fill a row with a colour
        self.chars_size = size
        oled.rectangle(
            left,
            self.optisize(
                row * self.ROW_SPACE - self.CHAR_MAX_HEIGHT - 1 - (self.chars_size - 1)),
            right,
            self.optisize(row * self.ROW_SPACE - self.CHAR_MIN_HEIGHT - 1), colour)
        oled.show()
        # log(
        # 	"typsnitt", INFO,
        # 	'Filled row ' + str(row) + " from " + str(left) + " to " + str(right))

    def scroll_bar(self, page, pages, foreground=1, background=0):
        """
        This method draws a scroll bar.
        :param page: Which page you are on
        :param pages: Pages you have
        :param foreground: Foreground colour
        :param background: Background colour
        """
        self.fg, self.bg = foreground, background
        oled.rectangle(self.X_DISPLAY_MAX - 1, 0, self.X_DISPLAY_MAX, self.Y_DISPLAY_MAX, self.bg)
        if pages <= self.Y_MAX:
            oled.rectangle(
                self.X_DISPLAY_MAX - 1, round((self.Y_MAX / pages) * (page - 1)),
                self.X_DISPLAY_MAX, round((self.Y_MAX / pages) * page) - 1, self.fg)
        else:
            if round((self.Y_MAX / pages) * page - 1) < 0:
                oled.rectangle(self.X_DISPLAY_MAX - 1, 0, self.X_DISPLAY_MAX, 0, self.fg)
            elif round((self.Y_MAX / pages) * page - 1) > self.Y_DISPLAY_MAX:
                oled.rectangle(
                    self.X_DISPLAY_MAX - 1, self.Y_DISPLAY_MAX,
                    self.Y_DISPLAY_MAX, self.X_DISPLAY_MAX, self.fg)
            else:
                oled.rectangle(
                    self.X_DISPLAY_MAX - 1, round((self.Y_MAX / pages) * page - 1),
                    self.X_DISPLAY_MAX, round((self.Y_MAX / pages) * page - 1), self.fg)
        oled.show()
        # log("typsnitt", INFO, "Page " + str(page) + " / " + str(pages))

# chars = Chars(-1)
# write = chars.write


def text_orientation(*text, sep="", orientation, pos, size=1):
    """
    This function center or right the text.
    :param text: Text to orientate.
    :param sep: Separetors.
    :param orientation: "c" if center, "r" if right, "l" if left.
    :param pos: X-position.
    :return: X-position.
    """
    _chars = Chars()
    txt = ""
    for variable in range(len(text)):
        txt += str(text[variable])
        if variable < len(txt) - 1:
            txt += str(sep)
    if _chars.write(txt, row=1, test=True, size=size)[0] > _chars.chars_size:
        raise SyntaxError('row too long!')
    if orientation == "c":
        x = pos - round(_chars.write(txt, row=1, test=True, size=size)[1] / 2)
        """ValueTest(x, "", _chars.X_CHAR_MAX, _chars.X_CHAR_MIN, False)
        ValueTest(
            _chars.write(
                txt, row=1, test=True, size=size)[1],
            "", _chars.X_CHAR_MAX, _chars.X_CHAR_MIN, False)"""
    elif orientation == "r":
        x = pos - _chars.write(txt, row=1, test=True, size=size)[1]
        """ValueTest(x, "", _chars.X_CHAR_MAX, _chars.X_CHAR_MIN, False)
        ValueTest(
            _chars.write(
                txt, row=1, test=True,
                size=size)[1], "", _chars.X_CHAR_MAX, _chars.X_CHAR_MIN, False)"""
    elif orientation == "l":
        x = pos
        SyntaxError(x, "", _chars.X_CHAR_MAX, _chars.X_CHAR_MIN, False)
    else:
        raise SyntaxError('expected "c", "v" or "r" as orientation, not ', repr(orientation))
    return x


if __name__  == '__main__':
    chars = Chars()
    chars.write("Hello world!\n" * 7)
    chars.scroll_bar(5, 8)
    delay(2000)
    chars.row_fill(3, 0)
    delay(5000)
    oled.fill(0)
    chars.write("Big text!\n" * 3, size=2)
    chars.scroll_bar(5, 8)
    delay(2000)
    chars.row_fill(2, 0, size=2)