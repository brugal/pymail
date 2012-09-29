#!/usr/bin/python
# NOTE:	crashes with gtk 1.2.1 
import sys
#FIXME remove gtk 1.2.1 and replace with new version, (1.2.1 crashes)
sys.path.insert (0, "/site/home/acano/own_src/news_reader/pygtk-new")

from gtk import *
import MessageCList, ComposeWindow, os 
import FileSelection
import FileLock
import StatusLabel
import string 
import stat
import StringIO
import mimetools
import time

#FIXME 	Include all references when replying (append last message to end
#	of references list. 9/4/00
#FIXME bug with delete_messages()/import() combination, it updates
#	the real_mbox correctly, but the clist will remove the wrong message.
#	7/11/00
#FIXME save read messages to ~/mbox
#FIXME a decent fixed-witdh font for message textbox
#FIXME save button- save message somewhere
#FIXME mime attachments
#FIXME save sent messages to a file, just in case the transfer fails
#FIXME chmod on tmp files

BUFFER_SIZE = 8192

class MessagePointer:
	# info for MessageCList
	def __init__ (self):
		self.from_ = None  # either a name, email, or "" if screwed up
		self.subject = None
		self.date = None

		self.read = None
		self.deleted = None
		self.marked = None

		self.seek_index = None

# global variables
debug = TRUE

messages = None				# [] of MessagePointer objects
tmp_mbox = None				# file object
real_mbox = None			# file object
real_mbox_in_use = None			# - a write/read lock used only within
					#   this program 
bytes_locked_in_real_mbox = None	# bytes locked in real_mbox
min_real_mbox_size = None		# - bytes locked plus any messages 
					#   added by sendmail (MTA). Used
					#   to detect if real_mbox has been
					#   altered by another program.
message_clist = None			# MessageCList.MessageCList()
current_message_num = None		# integer index into messages[]
current_message = None			# a mimetools.Message object
header_textbox = None			# - GtkText() showing header info
					#   of current message
message_textbox = None			# GtkText() showing the message
quote_color = None			# GdkColor to use for quoted messages
status_label = None			# - StatusLabel() for warnings and
					#   confirmations

need_to_delete_messages_in_real_mbox = FALSE


def dprint (text):
	if debug == TRUE:
		print "pym: %s" % text

def quit (widget=None, data=None):
	update_mbox ()
	remove_tmp_files ()
	remove_file_locks ()
	mainquit ()

def error_exit ():
	global tmp_mbox, tempdir
	remove_file_locks ()
	print "\
Error occured, a copy of your original mbox file can be found here: \n\
	%(copy_of_mbox)s \n\
Remeber to delete %(tempdir)s/ before running %(program_name)s again."  % \
		{	"copy_of_mbox"  : tmp_mbox.name,
			"tempdir"	: tempdir,
			"program_name"	: os.path.basename (sys.argv[0]) \
		}
	sys.exit (1)

def remove_tmp_files ():
	global tempdir
	tmp_files = os.listdir (tempdir)
	for file in tmp_files:
		os.remove (os.path.join (tempdir, file))
	os.rmdir (tempdir)

def remove_file_locks ():
	global real_mbox, tmp_mbox
	if real_mbox != None:
		FileLock.fcntl_remove_lock (real_mbox)
	if tmp_mbox != None:
		FileLock.fcntl_remove_lock (tmp_mbox)


def compose (widget=None, data=None, to="", cc="", from_="",subj="",
	     references=None, mesg=""):
	if from_ == ""  or  from_ == None:
		if os.environ.has_key("USER"):
			#FIXME config file with users alternate email
			#from_ = "%s@localhost" % os.environ["USER"]
			from_ = "acano@systec.com"
	
	#FIXME config file with option to automatically cc to one's self

	compose_win = ComposeWindow.ComposeWindow (to, cc, from_, subj, references, mesg)

def reply (widget=None, data=None):
	global current_message, messages
	if current_message == None:
		#FIXME status label for these type of warnings
		global status_label
		status_label.status_print ("no message selected to reply to")
		#print "no message selected to reply to"	
		return

	# To:
	while 1:
		to = current_message.getheader ("reply-to")
		if to != None:
			break
		to = current_message.getheader ("reply")
		if to != None:
			break
		(name, to) = current_message.getaddr ("from")
		if to != "":
			break			
		# if all else fails
		to = "????????"
		break	

	# CC:
	cc = current_message.getheader ("cc")
	if cc == None:
		cc = ""
	#FIXME if user wants to automatically CC to self, cc = cc + $user

	# from:  (from_)
	"""
	from_ = current_message.getheader ("to")
	if from_ == None:
		from_ = ""
	"""
	from_ = ""	# compse() handles correct 'from_'...
			#FIXME above is ugly

	# Subject:
	new_subject = current_message.getheader ("subject")	
	if new_subject == None:
		new_subject = ""
	new_subject = string.strip (new_subject)
	if string_begins_with (string.lower(new_subject), "re:"):
		pass
	else:
		new_subject = "Re: " + new_subject

	references = current_message.getheader ("message-id")
	print references
	# - quoted message.  example:
	#   > blah blah blah die balh
	#   > slkdj slksdlkdjf
	#FIXME fix width and readjust to 80 chars per line
	global message_textbox
	body = message_textbox.get_chars (0, -1)
	lines = string.split (body, "\n")

	new_message_body = ""
	for line in lines:
		new_message_body = new_message_body + "> " + line + "\n"

	quoted_message = "On %(date)s, %(author)s wrote:\n%(message)s" % \
		{ 	"date"	  :	current_message.getheader("date"),
			"author"  :	current_message.getheader("from"),
			"message" :	new_message_body	\
		}	
	"""
	print "reply_to(): "
	print "to == " + to
	print "cc == " + cc
	print "from == " + from_
	print "subject == " + new_subject
	print "message == \n" + quoted_message
	"""

	compose (widget=None, data=None, to=to, cc=cc, from_=from_, \
		subj=new_subject, references=references, mesg=quoted_message)

def message_selected (clist=None, row=None, column=None, data=None):
	global messages, message_clist

	msg_num = message_clist.get_text (row, MessageCList.NUMBER_COL)
	msg_num = string.atoi (msg_num)
	msg_num = msg_num - 1  # since the clist is indexed from '1' not '0'
	message = messages[msg_num]

	# read/unread toggled
	if column == MessageCList.STATUS_COL:
		if message.read == TRUE:
			message.read = FALSE
			message_clist.message_unread (row)
		else:
			message.read = TRUE
			message_clist.message_read (row)
		return

	# marked/unmarked toggled
	if column == MessageCList.MARKED_COL:
		if message.marked == TRUE:
			message.marked = FALSE
			message_clist.message_unmarked (row)
		else:
			message.marked = TRUE
			message_clist.message_marked (row)
		return
	
	global current_message_num
	#current_message_num = i
	current_message_num = msg_num

	global message_clist
	message_clist.message_read (row)

	message.read = TRUE
	global tmp_mbox
	tmp_mbox.seek (message.seek_index)
	body = ""
	# get header lines
	header_lines = []
	while 1:
		line = tmp_mbox.readline ()
		if line == "\n"  or  line == "":
			break
		header_lines.append (line)
	# get body
	body_lines = []
	while 1:
		line = tmp_mbox.readline ()
		if line[:len("From ")] == "From ":
			# - Delete the extra "\n" from the "\nFrom " mbox
			#   message separator.
			if len(body_lines) > 0:
				del body_lines[-1]	
			break
		if line == "":	# end of file
			break
		body_lines.append (line)

	msg_text = string.join (header_lines,"") + "\n" + \
			string.join (body_lines, "")	
	#print msg_text
	fp = StringIO.StringIO (msg_text)
	global current_message
	current_message = mimetools.Message (fp)
	global message_textbox, quote_color
	message_textbox.freeze ()

	# delete text in message_textbox
	i = message_textbox.get_chars (0, -1)
	message_textbox.set_point (len (i))
	message_textbox.backward_delete (len (i))

	style = message_textbox.get_style ()
	for line in body_lines:
		#FIXME 	Some people don't use ">".  I've seen "-" and ":" used.
		#	You could check for "some person wrote:" and see what
		#	quote char follows, but sometimes people don't include
		#	a "some person wrote:" string... oh well.
		if len(line) > 1  and  line[0] == ">":
			message_textbox.insert (style.font, quote_color,
					style.base[STATE_NORMAL], line)
		else:
			message_textbox.insert_defaults (line)
	message_textbox.thaw ()	

	global header_textbox
	header_textbox.freeze ()
	i = header_textbox.get_chars (0, -1)
	header_textbox.set_point (len (i))
	header_textbox.backward_delete (len (i))
	list_id = current_message.getheader("list-id")
	header_textbox.insert_defaults (\
			"From:\t\t%s\n" \
			"Subject:\t%s\n" \
			"Date:\t\t%s\n" \
			"List-Id:\t%s\n\n%s" % \
			(current_message.getheader("from"),
			current_message.getheader("subject"),
			current_message.getheader("date"),
		 	list_id,
		 	string.join (header_lines,"")))
	header_textbox.set_point (0)
	header_textbox.thaw ()

def import_mbox (widget=None, data=None):
	dprint ("import_mbox()")
	global messages, tmp_mbox
	update_mbox ()
	get_list_of_messages ()
	update_message_clist ()

def update_mbox ():
	dprint ("update_mbox()")
	global real_mbox, tmp_mbox

	global real_mbox_in_use
	# - lock so that touch_real_mbox() doesn't screw this up.  See
	#   def touch_real_mbox():  to see why it's needed.
	real_mbox_in_use = TRUE
	FileLock.lockf_lock_entire_file (real_mbox)

	global need_to_delete_messages_in_real_mbox
	if need_to_delete_messages_in_real_mbox == FALSE:
		# - just need to expand the file lock on real_mbox to include
		#   new messages
		dprint ("simply expanding real_mbox lock to include new msgs")
	else:
		new_messages_file = create_tmp_copy_of_new_messages ()
		remove_deleted_messages_from_real_mbox ()
		need_to_delete_messages_in_real_mbox = FALSE
		if new_messages_file != None:
			readd_new_messages_to_real_mbox (new_messages_file)
			new_messages_file.close ()

	copy_file (real_mbox, tmp_mbox)
	global bytes_locked_in_real_mbox
	bytes_locked_in_real_mbox = os.stat(real_mbox.name)[stat.ST_SIZE]
	global min_real_mbox_size
	min_real_mbox_size = bytes_locked_in_real_mbox
	FileLock.fcntl_lock_file_up_to_present_bytes (real_mbox)
	FileLock.lockf_remove_lock (real_mbox)
	real_mbox_in_use = FALSE

	# - I guess some xbiff-type programs use /var/spool/mail/mbox size to 
	#   indicate new messages.  This is a problem if you delete read
	#   messages and then add the new ones, mbox is shorter.  So here's
	#   a kludge.
	timeout_add (2000, touch_real_mbox)

def touch_real_mbox ():
	"I guess some xbiff-type programs use /var/spool/mail/mbox size to indicate new messages.  This is a problem if you delete read messages and then add the new ones, mbox is shorter.  So here's a kludge."
	dprint ("touch_real_mbox()")
	global real_mbox, real_mbox_in_use
	while real_mbox_in_use == TRUE:
		# wait for the mbox to be free'd
		while events_pending():
			mainiteration () 
	real_mbox.read (1)
	dprint ("real_mbox touched")
	return FALSE


def create_tmp_copy_of_new_messages ():
	"Returns the fileObject that contains the new messages, 'None' if no new messages."
	dprint ("copying new messages to a tmp file")
	global bytes_locked_in_real_mbox
	old_size = bytes_locked_in_real_mbox
	global real_mbox
	new_size = os.stat(real_mbox.name)[stat.ST_SIZE]

	if old_size == new_size:
		# no new messages
		return None

	global tempdir
	new_messages_file = open (os.path.join(tempdir, "new-messages"), "w+")
	real_mbox.seek (old_size)
	global BUFFER_SIZE
	while 1:
		data = real_mbox.read (BUFFER_SIZE)
		if data == "":
			break
		new_messages_file.write (data)
		#print data
	return new_messages_file

def remove_deleted_messages_from_real_mbox ():
	dprint ("deleting messages from real_mbox")
	# - skip until you find the first message to delete, that way
	#   you don't have to write the first few undeleted messages in
	#   real_mbox since they are already there.
	#print "len(messages) == %d" % len(messages)
	found_deleted_message = FALSE
	global messages
	for i in range (len(messages)):
		#print i, messages[i].subject, messages[i].deleted
		if messages[i].deleted == TRUE:
			found_deleted_message = TRUE
			break
	index_of_first_deleted_message = i

	#FIXME some debug code
	if found_deleted_message == FALSE:
		print 	"*** warning *** this shouldn't happen! Trying to " + \
			"find a deleted message and reached end of mbox. FIXME"
		return
	if len(messages) == 0:
		print	"*** warning *** this shouldn't happen! There are " + \
			"0 messages in message list, therefore global " + \
			"need_to_delete_messages_in_real_mbox should have " + \
			"been set to FALSE and this function should not " + \
			"have been called.  FIXME"
		return

	
	first_deleted_message = messages[index_of_first_deleted_message]
	global real_mbox, tmp_mbox
	real_mbox.seek (first_deleted_message.seek_index)
	tmp_mbox.seek (first_deleted_message.seek_index)
	bytes_written = first_deleted_message.seek_index
	for i in range (index_of_first_deleted_message, len(messages)):
		if messages[i].deleted == FALSE:
			# write it
			tmp_mbox.seek (messages[i].seek_index)
			if i == len(messages) - 1:
				text = tmp_mbox.read ()
			else:
				size = messages[i + 1].seek_index - \
					messages[i].seek_index
				text = tmp_mbox.read (size)
			real_mbox.write (text)
			bytes_written = bytes_written + len(text)

	real_mbox.truncate (bytes_written)	


def readd_new_messages_to_real_mbox (new_messages_file):
	dprint ("readding new messages to real_mbox")
	global real_mbox, BUFFER_SIZE
	# seek to end of real_mbox
	real_mbox.seek (os.stat(real_mbox.name)[stat.ST_SIZE])
	new_messages_file.seek (0)
	#print new_messages_file.name
	while 1:
		data = new_messages_file.read (BUFFER_SIZE)
		if data == "":
			break
		real_mbox.write (data)
		#print data


def string_begins_with (string_=None, substring=None):
	string_to_check = string_[:len(substring)]
	if string_to_check == substring:
		return TRUE
	else:
		return FALSE

def get_list_of_messages ():
	dprint ("get_list_of_messages()")
	global tmp_mbox, messages
	if os.stat(tmp_mbox.name)[stat.ST_SIZE] == 0:
		messages = []
		return
	tmp_mbox.seek (0)
	messages = []
	line = tmp_mbox.readline()
	#if line[:len("From ")] != "From ":
	if not string_begins_with (line, "From "):
		print "invalid mbox begins with:\n" + line
		error_exit ()
	tmp_mbox.seek (0)

	while 1:	# break when all lines of text in tmp_mbox are read
		line = None
		header_lines = []
		seek_index = tmp_mbox.tell ()
		while 1:	# break when "\n\n" or EOF found
			line = tmp_mbox.readline ()
			if line == "":
				break
			if line == "\n":
				# - header found advance to next message 
				#   and break
				while 1:  # break when "From " or EOF found
					tmp_seek = tmp_mbox.tell ()
					line = tmp_mbox.readline()
					if line == "":
						break
					if line[:len("From ")] == "From ":
						# - Start of new message found. 
						#   Rewind so that "From " ...
						#   is part of new message.
						#   Helps when writing to mbox
						#   later.
						tmp_mbox.seek (tmp_seek)
						break
				break
			else:
				header_lines.append (line)
		if len(header_lines) == 0:
			# no header, end of file 
			break
		header = string.join (header_lines, "")
	
		msg = MessagePointer ()
		msg.read = FALSE
		msg.deleted = FALSE
		msg.marked = FALSE
		msg.seek_index = seek_index

		fp = StringIO.StringIO (header)
		msg.fp = fp
		m = mimetools.Message (fp)
		msg.subject = m.getheader ("subject")
		if msg.subject == None:
			msg.subject = ""
		(name, email) = m.getaddr ("from")
		if name != "":
			msg.from_ = name
		else:
			if email == "":
				#FIXME
				print "msg.from_ FIXME, email == ''"
			msg.from_ = email
		msg.date = m.getheader ("date")
		if msg.date == None:
			msg.date = "None"
		messages.append (msg)
		
				
def update_message_clist ():
	dprint ("update_message_clist()")
	global messages, message_clist
	message_clist.freeze ()
	message_clist.clear ()
	for i in range (len (messages)):
		msg = messages[i]
		message_clist.append ((`i+1`, 
				" ",	# marked/unmarked, 'x' or ' '
				":", 	# read/unread,     ' ' or ':'
				msg.from_, msg.subject, msg.date))
		if msg.read == TRUE:
			message_clist.message_read (i)
	message_clist.thaw ()	

def delete_read_messages (widget=None, data=None):
	dprint ("delete_read_messages()")
	global messages, message_clist
	messages_deleted = 0
	for i in range (len(messages)-1, -1, -1):
		if messages[i].read == TRUE:
			messages[i].deleted = TRUE
			message_clist.remove (i)
			messages_deleted = messages_deleted + 1

	if messages_deleted == 0:
		return
	else:
		global need_to_delete_messages_in_real_mbox
		need_to_delete_messages_in_real_mbox = TRUE

def check_if_real_mbox_has_been_altered_by_another_program ():
	global real_mbox, min_real_mbox_size
	new_size = os.stat(real_mbox.name)[stat.ST_SIZE]

	if new_size > min_real_mbox_size:
		# messages have been appended, take into account
		min_real_mbox_size = os.stat(real_mbox.name)[stat.ST_SIZE]
	if new_size < min_real_mbox_size:
		print "error: %s has been edited by some other program" % \
			real_mbox.name
		error_exit ()
	return TRUE

# - Need to do this by hand since shutil.copy() opens the src file and
#   removes any file locks on it.
def copy_file (src, dest):
	"Both arguments (src and dest) should be fileObjects."
	global BUFFER_SIZE
	dest.truncate (0)
	dest.seek (0)
	src.seek (0)

	while 1:
		data = src.read (BUFFER_SIZE)
		if data == "":
			break
		dest.write (data)
	dest.flush ()

def save_message (widget=None, data=None):
	global current_message_num, messages, tmp_mbox
	if current_message_num == None:
		status_print ("no message selected")
		return
	msg = messages[current_message_num]
	tmp_mbox.seek (msg.seek_index)

	if current_message_num == len(messages) - 1:  # it's the last message
		text = tmp_mbox.read ()
	else:
		next_msg = messages[current_message_num + 1]
		size = next_msg.seek_index - msg.seek_index
		text = tmp_mbox.read (size)

	#filename = time.strftime ("%2m-%2d-%4Y %I:%M:%S", 
	#		time.localtime (time.time()))
	sio = StringIO.StringIO (text)
	m = mimetools.Message (StringIO.StringIO(text))
	filename = "%s %s" % (m.getheader("date"), msg.subject)
	# get rid of '/' 
	filename = string.replace (filename, "/", "-")
	fs = FileSelection.Get (filename)
	fs.show ()
	filename = fs.run ()
	fs.destroy ()
	if filename == None:
		return

	f = open (filename, "w")
	f.write (text)
	f.close ()
	status_print ("message saved")
		
def status_print (text):
	global status_label
	status_label.status_print (text)

######################
#####	main	######
######################
#FIXME ~/.pym-gtkrc ?
rc_parse ("/site/home/acano/own_src/mail/pym-gtkrc")
win = GtkWindow ()
quote_color = win.get_colormap().alloc (0xffff, 0x0000, 0x0000)
win.set_usize (670, 720)
win.set_title ("%s:" % os.path.basename (sys.argv[0]))
win.connect ("destroy", quit)
win.set_policy (TRUE, TRUE, FALSE) # allow_shrink, allow_grow, auto_shrink

main_vbox = GtkVBox ()
win.add (main_vbox)

#FIXME menu

button_hbox = GtkHBox ()
main_vbox.pack_start (button_hbox, FALSE, FALSE)

buttons = {}
def make_button (name, function, data=None):
	global buttons, button_hbox	
	buttons[name] = GtkButton (name)
	buttons[name].connect ("clicked", function, data)
	button_hbox.pack_start (buttons[name], FALSE, FALSE)

make_button ("quit", quit)
make_button ("compose", compose)
make_button ("reply", reply)
make_button ("delete read", delete_read_messages)
make_button ("import mbox", import_mbox)
make_button ("save message", save_message)

vpane = GtkVPaned ()
vpane.set_position (200)
main_vbox.pack_start (vpane)

sw = GtkScrolledWindow ()
vpane.add1 (sw)

message_clist = MessageCList.MessageCList ()
message_clist.connect ("select-row", message_selected)
sw.add (message_clist)

vpane2 = GtkVPaned ()
vpane2.set_position (70)
vpane.add2 (vpane2)

sw = GtkScrolledWindow ()
sw.set_policy (POLICY_AUTOMATIC, POLICY_AUTOMATIC)
vpane2.add1 (sw)

header_textbox = GtkText ()
header_textbox.set_name ("header_textbox")
sw.add (header_textbox)

sw = GtkScrolledWindow ()
vpane2.add2 (sw)

message_textbox = GtkText ()
message_textbox.set_word_wrap (TRUE)
message_textbox.set_name ("message_textbox")
sw.add (message_textbox)

hbox_used_as_padding = GtkHBox ()
main_vbox.pack_start (hbox_used_as_padding, FALSE, FALSE, 0)
status_label = StatusLabel.StatusLabel ()
hbox_used_as_padding.pack_start (status_label, FALSE, FALSE, 0)

messages = []

# get tempdir
if os.environ.has_key ("TMPDIR"):
	tempdir = os.environ["TMPDIR"]
elif os.path.exists ("/tmp"):
	tempdir = "/tmp"
else:
	tempdir = os.getcwd ()

if os.environ.has_key ("USER"):
	tempdir = os.path.join (tempdir, os.environ["USER"] + "-pymail")
else:
	tempdir = os.path.join (tempdir, "pymail-tmpdir")

if os.path.exists (tempdir):
	print "\
error:  %(tempdir)s already exists.  \n\
Another copy of %(program_name)s might already be running, or the previous \n\
copy might have exited with an error." % \
		{ 	"tempdir" 	: tempdir,
			"program_name" 	: os.path.basename (sys.argv[0]) \
		}
	remove_file_locks ()
	sys.exit (1)
#FIXME 	remember to remove try/except statements, they are just put in while
#	I write the program so I don't have to keep deleteing 'tempdir'
try:
	os.mkdir (tempdir, 0700)	# drwx------ 
except:
	print "remember to take this try/except out."
	pass

real_mbox_in_use = FALSE
# make sure real_mbox is opened for writing so that file-locks can work
real_mbox = open (os.environ["MAIL"], "r+") 
FileLock.fcntl_lock_file_up_to_present_bytes (real_mbox)

# these are used to check if another program messes with /var/spool/mail/mbox
bytes_locked_in_real_mbox = os.stat (real_mbox.name)[stat.ST_SIZE]
min_real_mbox_size = bytes_locked_in_real_mbox

# - Create a work copy (tmp_mbox) of the mbox, in case other programs screw
#   with the actual mbox (real_mbox).
tmp_mbox_filename = os.path.join (tempdir, "mbox")
tmp_mbox = open (tmp_mbox_filename, "w+")
FileLock.lockf_lock_entire_file (tmp_mbox)
copy_file (real_mbox, tmp_mbox)

#timeout_add (1000, check_mbox_size)
timeout_add (1000, check_if_real_mbox_has_been_altered_by_another_program)
get_list_of_messages ()
update_message_clist ()

#FIXME huh?
FileLock.lockf_remove_lock (real_mbox)
win.show_all ()
mainloop ()
