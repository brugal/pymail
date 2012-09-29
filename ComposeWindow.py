from gtk import *
import smtplib, os
import string
import sys
import time

def sanitize_filename (filename):
	filename = string.replace (filename, '/', '-')
	return filename

class ComposeWindow:
	win = None		# GtkWindow
	entry_dict = None	# {}
	status_label = None	# GtkLabel
#	quote_color = None	# GdkColor for quoted reply
# 'quote_color' doesn't work... when you go in to type in your part it comes
# out with the 'quote_color'

	def __init__ (self, to="", cc="", from_="", subj="", references=None,
	mesg=None):
		self.win = GtkWindow ()
		#self.win.set_usize (520, 600)
		#self.set_name ("compose_textbox")
		self.win.set_usize (670, 700)
		#self.quote_color = self.win.get_colormap().alloc (\
		#				0xffff, 0x0000, 0x0000)
		vbox = GtkVBox ()
		self.win.add (vbox)

		button_hbox = GtkHBox ()
		vbox.pack_start (button_hbox, FALSE, FALSE)
		
		button = GtkButton ("Send")
		button.connect ("clicked", self.send)
		button_hbox.pack_start (button)

		button = GtkButton ("Cancel")
		button.connect ("clicked", self.win.destroy)
		button_hbox.pack_start (button)

		hbox = GtkHBox ()
		vbox.pack_start (hbox, FALSE, FALSE)
		label_vbox = GtkVBox ()
		hbox.pack_start (label_vbox)
		entry_vbox = GtkVBox ()
		hbox.pack_start (entry_vbox)
		
		entries = ["to", "cc", "from", "subject"]
		self.entry_dict = {}
		for entry in entries:
			if entry == "cc":
				label = GtkLabel ("cc (coma seperated list):")
			else:
				label = GtkLabel (entry + ":")
			label_vbox.pack_start (label)

			self.entry_dict[entry] = GtkEntry ()
			entry_vbox.pack_start (self.entry_dict[entry])

		self.entry_dict["to"].set_text (to)
		self.entry_dict["cc"].set_text (cc)
		self.entry_dict["from"].set_text (from_)
		self.entry_dict["subject"].set_text (subj)

		self.references = references
		sw = GtkScrolledWindow ()
		vbox.pack_start (sw)
	
		self.textbox = GtkText ()
		self.textbox.set_name ("compose_textbox")
		self.textbox.set_word_wrap (TRUE)
		self.textbox.set_editable (TRUE)
		if mesg != None:	# it's a reply
			#style = self.textbox.get_style ()
			#self.textbox.insert (style.font, self.quote_color,
			#		style.base[STATE_NORMAL], mesg)
			self.textbox.insert_defaults (mesg)
			self.win.set_title ("%s (reply): %s" % ( \
					os.path.basename(sys.argv[0]), subj))
		else:
			self.win.set_title ("%s (compose): %s" % ( \
					os.path.basename(sys.argv[0]), subj))
		sw.add (self.textbox)

		self.status_label = GtkLabel ("  ")
		self.status_label.set_justify (JUSTIFY_LEFT)		
		vbox.pack_start (self.status_label, FALSE, FALSE)
		
		self.win.show_all ()

	def send (self, widget=None):
		to 	= self.entry_dict["to"].get_text()
		from_ 	= self.entry_dict["from"].get_text()
		subject	= self.entry_dict["subject"].get_text()
		cc	= self.entry_dict["cc"].get_text()

		#FIXME no...   sucks
		parameters_needed = {	"to"		: 	to, 
					"from"		:	from_  \
					#"subject"	:	subject \
				    }
		for parameter in parameters_needed.keys():
			val = parameters_needed[parameter]
			if val == None  or  val == "":
				self.status_label.set_text (\
					"*** need %s entry ***" % parameter)
				return
	
		if cc != None  and  cc != "":
			#FIXME what if 'cc' is a 'space' seperated list instead
			#	of a 'coma' seperated list?
			recipients = to + "," + cc	
			recipients = string.split (recipients, ",")
			#FIXME chop whitespace from the begging and end of
			#	each recepient in list
		else:
			recipients = [to]

		text	= self.textbox.get_chars(0,-1)

		header = ""
		if cc != None  and cc != "":
			header = "To: %s\nSubject: %s\nCc: %s" % (to,
				subject, cc)
		else:
			header = "To: %s\nSubject: %s" % (to, subject)

		if self.references != None  and  self.references != "":
			header = "%s\nReferences: %s" % (header, 
				self.references)

		if text != ''  and  text[-1] != '\n':
			text = text + '\n'

		text = "%s\n\n%s" % (header, text)


		# save a copy
		for recipient in recipients:
			recp = string.strip (recipient)
			save_dir = os.path.join (os.environ["HOME"], 
						"PYMAIL", "sent", recp)
			if not os.path.exists (save_dir):
				os.mkdir (save_dir)
			message_id = time.strftime ("%2m%2d%4Y %I:%M:%S", 
						time.localtime(time.time()))
			filename = "%s -%s" % (message_id, subject)
			filename = sanitize_filename (filename)
			i = 1
			while os.path.exists (os.path.join(save_dir, filename)):
				filename = "%s %d-%s" % (message_id, i, subject)
				i = i + 1
			f = open (os.path.join (save_dir, filename), "w")
			f.write ("From: %s\nDate: %s\n" % (from_,
				time.asctime (time.localtime (time.time()))))
			f.write ("CC:")
			for r in recipients:
				if r != to:
					f.write (" %s" % r)
			f.write ("\n")
			f.write (text)
			f.close ()
			
		#FIXME add option to have someting other that 'localhost'?
		smtp = smtplib.SMTP ("localhost")
		smtp.sendmail (from_, recipients, text)
		smtp.quit ()
		self.win.destroy ()	
		
