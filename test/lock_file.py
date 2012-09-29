#!/usr/bin/env python
import sys
sys.path.insert (0, "..")

from FileLock import *
import time

f = open ("/var/spool/mail/acano", "a+")
fcntl_lock_file_up_to_present_bytes (f)

while 1:
	time.sleep (1)

