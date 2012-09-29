from gtk import *
import time

class StatusLabel(GtkLabel):
	def __init__ (self, msg=""):
		GtkLabel.__init__ (self, msg)
		
		self.messages = {}
		self.lock = None
		
		timeout_add (3000, self._erase_some_messages)

	def status_print (self, msg):
		msg_number = time.time ()
		self.messages[msg_number] = msg

		self.lock = TRUE
		old_text = self.get ()
		self.set_text ("%s %s" % (old_text, msg))
		self.lock = FALSE

	def _erase_some_messages (self):
		if len(self.messages) == 0:
			return TRUE

		while self.lock == TRUE:
			while events_pending():
				mainiteration ()

		# get rid of stale messages
		current_time = time.time ()
		for time_ in self.messages.keys ():
			if time_ < current_time - 3:
				del self.messages[time_]

		message_numbers = self.messages.keys ()
		message_numbers.sort ()
		new_text = ""
		for number in message_numbers:
			new_text = new_text + " " + self.messages[number]
		self.set_text (new_text)
		return TRUE

