from Lib_ssd1306 import SSD1306, display


class Display:
    pinout = {'sda': 'X10', 'scl': 'X9'}
    height = 64
    external_vcc = False

    def __init__(self):
        self.oled = SSD1306(self.pinout, self.height, self.external_vcc)
        self.oled.poweron()
        self.oled.init_display()

    def rectangle(self, x, y, x2, y2, c, update=False, step=1):
        for y0 in range(y, y2 + 1, step):
            for x0 in range(x, x2 + 1, step):
                self.pixel(x0, y0, c)
        if update:
            self.show()

    def pixel(self, x, y, c, update=False):
        try:
            display.set_pixel(127 - x, y, c)
        except IndexError:
            pass
        if update:
            self.show()

    def fill(self, c):
        self.rectangle(0, 0, 127, 63, c)
        self.show()

    @staticmethod
    def show():
        display.display()

    @staticmethod
    def clear():
        display.clear()

    def frame(self, x, y, x2, y2, c):
        self.rectangle(x, y, x2, y, c)
        self.rectangle(x, y, x, y2, c)
        self.rectangle(x, y2, x2, y2, c)
        self.rectangle(x2, y, x2, y2, c)

    def grid(self, x, y, sx, sy, cx, cy, c):
        x1 = x
        y1 = y
        for y_times in range(cy):
            for x_times in range(cx):
                self.frame(
                    x1, y1,
                    x1 + sx,
                    y1 + sy,
                    c)
                x1 += sx
            x1 = x
            y1 += sy

    @staticmethod
    def off():
        display.poweroff()

    @staticmethod
    def on():
        display.poweron()
        display.init_display()