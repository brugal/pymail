#!/usr/bin/python
from gtk import *
import sys
sys.path.insert (0, "..")
#import FileHandler
import FileSelection

def get_file (button, data=None):
	fget = FileSelection.Get ("/usr/tmp/testssss")
	fget.show_all ()
	filename = fget.run()
	print filename
	fget.destroy ()

win = GtkWindow ()
win.set_usize (200, 200)
win.connect ("destroy", mainquit)

button = GtkButton ("get file")
button.connect ("clicked", get_file)
win.add (button)

win.show_all ()
mainloop ()

