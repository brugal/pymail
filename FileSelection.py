from gtk import *
import _gtk
import os, shutil, time

#FIXME 	catch IOError when you
#	do something like this in the entry box:
#	/home/evil_person/pix/picture.jpg
#
#	when 'pix' doesn't exist


class ConfirmDialog (GtkDialog):
	def __init__ (self, message="confirm", ok_button_label="ok", 
			cancel_button_label="cancel"):
		GtkDialog.__init__ (self)
		self.confirmed = None
		label = GtkLabel (message)
		self.vbox.pack_start (label)
		label.show ()

		ok_button = GtkButton (ok_button_label)
		ok_button.connect ("clicked", self.ok_selected)
		self.action_area.pack_start (ok_button, FALSE, FALSE)
		ok_button.show ()

		cancel_button = GtkButton (cancel_button_label)
		cancel_button.connect ("clicked", self.cancel_selected)
		self.action_area.pack_start (cancel_button, FALSE, FALSE)
		cancel_button.show ()

	def ok_selected (self, button, data=None):
		self.confirmed = TRUE

	def cancel_selected (self, button, data=None):
		self.confirmed = FALSE
		
	def run (self):
		while self.confirmed == None:
			while events_pending():
				mainiteration()
			time.sleep (0.1)
		return self.confirmed
		
class Get(GtkFileSelection):
	current_path = None
	
	def __init__ (self, filename=""):
		if Get.current_path == None:
			Get.current_path = os.getcwd ()

		self.selected_filename = None
		self.got_filename = FALSE
		self.confirmation = TRUE

		self.file_basename = os.path.basename (filename)

		if os.path.basename(filename) == filename: # relative pathname
			filename = os.path.join (Get.current_path, filename)
		
		GtkFileSelection.__init__ (self, filename)
		grab_add (self)
		self.set_filename (filename)
		self.hide_fileop_buttons ()

		self.connect ("destroy", self.close_file_selection)
		self.cancel_button.connect ("clicked", self.destroy)
		self.ok_button.children()[0].set_text ("Save")
		self.ok_button.connect ("clicked", self.select_filename)
		self.dir_list.connect ("select_row", self.dir_changed)

	def dir_changed (self, clist=None, row=None, column=None, data=None):
		self.selection_entry.set_text (self.file_basename)

	def set_confirmation (self, boolean):
		self.confirmation = boolean

	def run (self):
		while self.got_filename == FALSE:
			while events_pending():
				mainiteration ()
			time.sleep (0.1)
		return self.selected_filename

	def _abspath (self, filename):
		if os.path.isabs (filename):
			return filename
		return os.path.normpath (os.path.join (os.getcwd(), filename))

	def close_file_selection (self, widget, event=None):
		new_filename = self.get_filename ()
		new_filename = self._abspath (new_filename)
		(head, tail) = os.path.split (new_filename)
		Get.current_path = head
		self.selected_filename = None
		self.got_filename = TRUE

	def select_filename (self, button):
		self.selected_filename = self.get_filename ()
		if self.confirmation:
			if os.path.exists (self.selected_filename):
				c = ConfirmDialog ("File Exists, continue?")
				grab_add (c)
				c.show ()
				ret = c.run ()
				c.destroy ()
				if ret == FALSE:
					self.got_filename = FALSE
					return
		self.got_filename = TRUE
