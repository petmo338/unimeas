import font
from pyb import CAN, Timer, delay, USB_VCP
from ustruct import unpack, pack

timer_ticks = 0
time_to_heat_up = True
time_to_display = True

display = font.Display()
display.fill(0)
text = font.Chars()

usb_serial = USB_VCP()


def tick(timer):
	global timer_ticks, time_to_heat_up, time_to_display
	time_to_display = True
	timer_ticks -= 1
	if timer_ticks <= 0:
		time_to_heat_up = True
		timer_ticks = 60


def decode_nox_message(received_data):
	def var(value, value2):
		return True if value & value2 else False

	(nox_ppm, lambda_linear, oxygen_millivolt) = unpack("hHH", bytearray(received_data[:48]))

	sensor_temp   = var(received_data[6], 0b00000011)
	lambda_signal = var(received_data[6], 0b00001100)
	nox_signal    = var(received_data[6], 0b00110000)
	sensor_supply = var(received_data[6], 0b11000000)
	nox_open_wire = var(received_data[7], 0b00000011)
	nox_valid     = var(received_data[7], 0b00001100)
	nox_short     = var(received_data[7], 0b00110000)

	return (
		nox_ppm, lambda_linear, oxygen_millivolt,
		sensor_temp, lambda_signal, nox_signal, sensor_supply,
		nox_open_wire, nox_valid, nox_short
	)


def write_on_display(waiting):
	if waiting:
		text.write("Waiting...", row=1, colour=1, size=2)
	else:
		text.write("NOx ppm: ", row=1, colour=1)
		text.row_fill(1, colour=0, left=text.x, size=2)
		text.write(nox_ppm, row=1, colour=1, x_pos=text.x, size=2)

		text.write("NOx valid: ", row=5, colour=1)
		text.row_fill(3, colour=0, left=text.x, size=2)
		text.write(
			nox_valid, row=3, colour=1, x_pos=text.x,
			size=2
		)


NOX_OUT = 0x0CFF1752
NOX_START = 0x0CFF1400

can = CAN(1, CAN.NORMAL)

can.init(can.NORMAL, extframe=True, prescaler=21, sjw=1, bs1=5, bs2=2)

can.setfilter(0, CAN.MASK32, 0, (0x0, 0x0))

can_bus_up = False
# print("Waiting for CAN bus messages: ", end="")
while not can.any(0):
	# print(end="!")
	write_on_display(1)
	delay(1000)

display.fill(0)

can_bus_up = True

time_to_heat_up = True
timer_ticks = 0

timer_object = Timer(4, freq=1)
timer_object.callback(tick)

while "not break":
	if time_to_heat_up:
		can.send(128, NOX_START)
		time_to_heat_up = False

	message = ""
	if can.any(0):
		message = can.recv(0, timeout=1000)
		can_id = message[0]
		data = message[3]

		if can_id == NOX_OUT:
			(
				nox_ppm, lambda_linear, oxygen_millivolt,
				sensor_temp, lambda_signal, nox_signal, sensor_supply,
				nox_open_wire, nox_valid, nox_short
			) = decode_nox_message(data)

			hardware_error = nox_open_wire | nox_short
			sensor_ok = sensor_temp & lambda_signal & nox_signal & sensor_supply, nox_valid


			if time_to_display:
				serial_data = pack('hHH', nox_ppm, lambda_linear, oxygen_millivolt)
				usb_serial.write(serial_data)
				write_on_display(0)

				# print(
				# 	"\nID {0:} = {0:08X}:  Data: {1:02X} {2:02X} {3:02X} {4:02X}  {5:02X} {6:02X}  "
				# 	"{7:02X} {8:02X} ".format(can_id, *data), end="")
				# print(
				# 	sensor_temp, lambda_signal, nox_signal, sensor_supply,
				# 	nox_open_wire, nox_valid, nox_short,
				# 	nox_ppm, lambda_linear, oxygen_millivolt, end="")

				# print(" Sensors OK: {}".format(sensor_ok), end="")

				time_to_display = False