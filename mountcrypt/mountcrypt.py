import os
import sys
import pygtk
import gtk
import errno
import uuid
from subprocess import Popen, PIPE, STDOUT

errorCode = -1
errorMsg = ''

def setError(msg, code):
    global errorMsg
    global errorCode
    errorMsg = msg
    errorCode = code

def dialogPassword(text):
    message = gtk.MessageDialog(buttons=gtk.BUTTONS_OK_CANCEL)
    message.set_markup(text)

    #create entry
    entry = gtk.Entry()
    entry.set_visibility(False)
    entry.connect('activate', lambda ent, dlg, resp: dlg.response(resp), message, gtk.RESPONSE_OK)

    message.vbox.pack_end(entry, True, True, 0)
    message.vbox.show_all()

    #run dialog
    result = message.run()
    if result == gtk.RESPONSE_OK:
        text = entry.get_text()
    else:
        text = None

    #destroy dialog
    message.destroy()
    while gtk.events_pending():
        gtk.main_iteration()

    return text

def dialogError(errorMsg='', errorCode=-1):
    message = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
    message.set_markup(errorMsg)
    message.run()
    sys.exit(errorCode)

def luksUuid(filepath):
    cryptsetup = Popen(['cryptsetup', 'luksUuid', filepath], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout,stderr = cryptsetup.communicate()

    if (stderr):
        return str(uuid.uuid4())
    else:
        return str(stdout)

def luksIsOpened(alias):
    return os.path.isfile('/dev/mapper/' + alias)

def luksOpen(filepath, alias, password):
    #check if LUKS container already opened
    res = luksIsOpened(alias)
    if (res):
        setError('Error opening the LUKS container: Device "' + alias + '" already exists', 4)
        return False

    #open LUKS container
    cryptsetup = Popen(['cryptsetup', 'luksOpen', filepath, alias], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout,stderr = cryptsetup.communicate(input=password + '\n')
    password = None

    if (stderr):
        setError('Error opening the LUKS container: ' + stderr, 5)
        return False

    return True

def luksClose(alias):
    #check if LUKS device already opened
    res = luksIsOpened(alias)
    if (res):
        setError('Error closing the LUKS container: Device "' + alias + '" is not opened', 6)
        return False

    #close LUKS device
    cryptsetup = Popen(['cryptsetup', 'luksClose', alias], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout,stderr = cryptsetup.communicate()
    password = None

    if (stderr):
        setError('Error closing the LUKS device: ' + stderr, 7)
        return False

    return True

def luksMount(alias, dirpath):
    #create mount directory
    try:
        os.makedirs(dirpath)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(dirpath) and not os.path.ismount(dirpath):
            pass
        else:
            setError('Error mounting LUKS device: Couldn\'t create directory \"' + dirpath + '\"', 8)
            return False

    #mount LUKS device
    mount = Popen(['mount', '/dev/mapper/' + alias, dirpath], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout,stderr = mount.communicate()

    if (stderr):
        setError('Error mounting LUKS device: ' + stderr, 9)
        return False

    return True

#process arguments
if (len(sys.argv) != 2):
    sys.exit(1)

filepath = sys.argv[1]
alias = luksUuid(filepath)

#open password dialog
password = dialogPassword(text='Please enter the password for your LUKS encrypted container:')
if (password is None):
    sys.exit(2)

#open LUKS container
res = luksOpen(filepath, alias, password)
password = None
if (res is False):
    dialogError(errorMsg, errorCode)

#mount LUKS device
res = luksMount(alias, '/media/' + alias)
if (res is False):
    luksClose(alias)
    dialogError(errorMsg, errorCode)
