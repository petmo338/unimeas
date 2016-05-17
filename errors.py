class BaseError(Exception):

	def __init__(self, *value):
		self.text = ""
		for variable in value:
			self.text += str(variable)
			# self.text += str(sep)
		self.text2 = self.text

	def __str__(self):
		return str(self.text2) + "\n"


class Error(BaseError):
	def __repr__(self):
		return "Error: " + str(self.text2) + "\n"


class ArgumentError(BaseError):
	def __repr__(self):
		return "ArgumentError: " + str(self.text2) + "\n"


class NumberError(BaseError):
	def __repr__(self):
		return "NumberError: " + str(self.text2) + "\n"


class LenghtOverflowError(BaseError):
	def __repr__(self):
		return "LenghtOverflowError: " + str(self.text2) + "\n"


class UnresolvedReferenceError(BaseError):
	def __repr__(self):
		return "UnresolvedReferenceError: " + str(self.text2) + "\n"


class FatalError(BaseError):
	def __repr__(self):
		return "FatalError: " + str(self.text2) + "\n"


class Quit(BaseError):
	def __repr__(self):
		return "Quit: " + str(self.text2) + "\n"


class Warn(BaseError):
	def __repr__(self):
		return "Warn: " + str(self.text2) + "\n"


class IllegalError(BaseError):
	def __repr__(self):
		return "IllegalError: " + str(self.text2) + "\n"


class Info(BaseError):
	def __repr__(self):
		return "Info: " + str(self.text2) + "\n"


class ValueTest:
	max_value = 2147483647
	min_value = -2147483648

	def __init__(self, value, mode="", max_=9.999999e37, min_=-9.999999e37, float_allowed=True):
		if mode is "w":
			self.max_value = 999999999999999
			self.min_value = -999999999999999
			float_allowed = True
		elif mode is "b":
			self.max_value, self.min_value = 255, 0
			float_allowed = False
		elif mode is "f":
			self.max_value = 9.99999999999999e307
			self.min_value = -9.99999999999999e307
			float_allowed = True
		elif mode is "":
			self.max_value = max_
			self.min_value = min_
		elif mode is "p":
			self.max_value = 9.999999e37
			self.min_value = -9.999999e37
			float_allowed = True
		if value > self.max_value:
			raise NumberError("Too high number, max allowed value: ", self.max_value)
		elif value < self.min_value:
			raise NumberError("Too low number, min allowed value: ", self.min_value)
		if not float_allowed and type(value) == float:
			raise NumberError("Expected type int, not float")


class LenTest:
	max_len = 500

	def __init__(self, value, max_s=512, max_else=128):
		if type(value) is str:
			self.max_len = max_s
		else:
			self.max_len = max_else
		if len(value) > self.max_len:
			raise LenghtOverflowError(
				"Too long ", str(type(value))[8:-2], ", max allowed lenght: ", self.max_len,
				", lenght: ", str(len(value)))