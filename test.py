#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui, QtCore
from PyKDE4.kdeui import KStatusNotifierItem

# http://api.kde.org/4.x-api/kdelibs-apidocs/kdeui/html/classKStatusNotifierItem.html
class Notifier(QtCore.QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.tray = KStatusNotifierItem("someId", self)
        self.tray.setCategory(KStatusNotifierItem.Communications)
        self.tray.setIconByName("/usr/share/icons/oxygen/16x16/categories/applications-internet.png")
        self.tray.setStatus(KStatusNotifierItem.NeedsAttention)
        self.tray.setToolTipIconByName("/usr/share/icons/oxygen/16x16/categories/applications-internet.png")
        self.tray.setToolTipTitle("Title")
        self.tray.setToolTipSubTitle("SubTitle")

if __name__ == '__main__':
    App = QtGui.QApplication(sys.argv)
    notifer = Notifier()
    App.exec()


# kdialog --title "Long process completed" --passivepopup "This popup will disappear in 5 seconds" 5