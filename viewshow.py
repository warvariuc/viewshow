#!/usr/bin/env python3
__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import sys

PYTHON_REQUIRED_VERSION = '3.4'  # tested with this version
if sys.version < PYTHON_REQUIRED_VERSION:
    raise SystemExit('Bad Python version', 'Python %s or newer required (you are using %s).'
                     % (PYTHON_REQUIRED_VERSION, sys.version.split(' ')[0]))


import subprocess

from PyQt4 import QtGui, QtCore
import sip
# http://api.kde.org/4.x-api/kdelibs-apidocs/kdeui/html/classKStatusNotifierItem.html
from PyKDE4 import kdecore, kdeui

from viewshow import screenshot


QtCore.pyqtRemoveInputHook()
# http://stackoverflow.com/questions/23565702/pyqt4-crashed-on-exit
sip.setdestroyonexit(False)


def error(title, message):
    """Show error message dialog and exit.
    """
    print(title, '\n', message)
    subprocess.call("kdialog --title '%s' --sorry '%s'" % (title, message), shell=True)
    sys.exit(1)


def make_about_data():
    appName = "viewshow"
    catalog = ""
    programName = kdecore.ki18n("ViewShow")
    version = "0.5"
    description = kdecore.ki18n("A KDE screen recorder.")
    license = kdecore.KAboutData.License_GPL
    copyright = kdecore.ki18n("(c) 2015 Victor Varvaryuk")
    text = kdecore.ki18n("")
    homePage = "https://github.com/warvariuc/viewshow"
    bugEmail = ""

    global _about_data
    _about_data = kdecore.KAboutData(appName, catalog, programName, version, description,
                                     license, copyright, text, homePage, bugEmail)
    return _about_data


if __name__ == '__main__':

    kdecore.KCmdLineArgs.init(sys.argv, make_about_data())

    app = kdeui.KApplication()
    app.setOrganizationName("warvariuc")
    app.setApplicationName("viewshow")
    # app.setQuitOnLastWindowClosed(False)

    # make screenshot as ASAP to avoid latency because of loading the forms
    image = screenshot.Screenshot.make()

    from viewshow import selector
    screen_selector_dialog = selector.ScreenSelectorDialog(image=image)
    screen_selector_dialog.show()

    app.exec()
    # del screen_selector  # othewise the app crashes
