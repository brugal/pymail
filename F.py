import struct, fcntl, FCNTL, os, stat, time

#FIXME this is broken!  tested it on red-hat 6.0  (kernel 2.0.36??)
#   and it seemd to work fine.  with debian 2.2 (kernel 2.2.17) releasing
#   the fnctl lock doesn't seem to work

# python 1.5.2 doesn't seem to have these in my distro (debian potato 2.2)
#   I don't know why?  h2py should have generated these automatically
#   from fcntl.h.  Debian bug?
FCNTL.SEEK_SET = 0
FCNTL.SEEK_CUR = 1
FCNTL.SEEK_END = 2

TRUE = 1
FALSE = 0

# fcntl type locks 
def fcntl_lock_file_up_to_present_bytes (fileObject):
    """fcntl() locks the entire file, but other programs still have the 
    ability to append to the end of the file."""
    size = os.stat(fileObject.name)[stat.ST_SIZE]
    _fcntl_lock (fileObject, size)

def fcntl_lock_entire_file (fileObject):
    """fcntl() locks the entire file so that other programs can't even
    append to the file."""
    _fcntl_lock (fileObject, 0)

def fcntl_remove_lock (fileObject):
    lockdata = struct.pack ('hhllhh',
                            FCNTL.F_WRLCK,
                            0,
                            FCNTL.SEEK_SET,
                            0,
                            0,
                            0)
    ret = fcntl.fcntl (fileObject.fileno(), FCNTL.F_UNLCK, lockdata)

# lockf type lock
def lockf_lock_entire_file (fileObject):
    """For use in addition to fcntl type locks for interaction with BSD 
    style programs."""
    fcntl.lockf (fileObject.fileno(), FCNTL.LOCK_EX)
    
def lockf_remove_lock (fileObject):
    """For use in addition to fcntl type locks for interaction with BSD 
    style programs."""
    fcntl.lockf (fileObject.fileno(), FCNTL.LOCK_UN)


#######        PRIVATE FUNCTIONS (preceded by a '_' laf)       ######

def _fcntl_lock (fileObject, length):
    lockdata = struct.pack ( \
                'hhllhh',
                FCNTL.F_WRLCK,  # type
                0,              # offset relative to whence
                FCNTL.SEEK_SET, # whence: SEEK_SET, SEEK_CUR, SEEK_END
                length,         # len,  0 == entire file
                0,              # ???
                0)              # ???
    # first check if fileObject is already locked.
    print_warning = TRUE
    while 1:
        ret = fcntl.fcntl (fileObject.fileno(), FCNTL.F_GETLK, lockdata)
        # FCNTL.F_UNLCK == 2, but fcntl.fcntl returns byte-string,
        # i.e., we should've been able to do:
        # if ret[0] == FCNTL.F_UNLCK:
        # but have to do the following instead: 
        #FIXME I screwed up.  whether lockdata is an int or a string
        # affects the type of the return value... that's
        # stupid.  doing this crap in C is easier.
        if ret[0] == '\002':  # '\002' represents FCNTL.F_UNLCK
            break
        if print_warning == TRUE:
            print "%s is locked. Waiting..." % fileObject.name
            print_warning = FALSE   # just print warning once
            time.sleep (1)
    fcntl.fcntl (fileObject.fileno(), FCNTL.F_SETLK, lockdata)
    print "got a fcntl lock on %s" % fileObject.name
