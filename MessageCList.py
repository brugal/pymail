from gtk import *

# clist columns
NUMBER_COL 	= 0
MARKED_COL	= 1
STATUS_COL	= 2
FROM_COL	= 3
SUBJECT_COL	= 4
DATE_COL	= 5

class MessageCList (GtkCList):
	def __init__ (self):
		GtkCList.__init__ (self, 6, ("#", "x", "-", "From", "Subject",
				"Date"))
		# not useful since sendmail changes dates to when it puts them
		# in your mbox
		self.set_column_visibility (DATE_COL, FALSE)
		#FIXME adjust width as needed.  Example: start out of width
		# 	enough to hold '1' to '9' messages, then expand to two
		# 	spaces when '10', '100', '1000', etc. messages are in.
		self.set_column_width (NUMBER_COL, 25)
		self.set_column_width (MARKED_COL, 0)
		self.set_column_width (STATUS_COL, 0)
		self.set_column_width (FROM_COL, 130)
		self.set_column_width (SUBJECT_COL, 280)
		#self.set_column_width (DATE_COL, 40)	

		self.read_color = self.get_colormap().alloc (0x7000, \
					0x8000, 0x9000)
		self.unread_color = self.get_colormap().alloc (0xffff, \
					0xffff, 0xffff)
	
	def message_read (self, row):
		self.set_background (row, self.read_color)
		self.set_text (row, STATUS_COL, " ")

	def message_unread (self, row):
		self.set_background (row, self.unread_color)
		self.set_text (row, STATUS_COL, ":")

	def message_marked (self, row):
		self.set_text (row, MARKED_COL, "x")
	def message_unmarked (self, row):
		self.set_text (row, MARKED_COL, " ")

