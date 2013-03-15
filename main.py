#!/usr/bin/env python3
__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import sys

python_required_version = '3.2'  # tested with this version
if sys.version < python_required_version:
    raise SystemExit('Bad Python version', 'Python %s or newer required (you are using %s).'
                     % (python_required_version, sys.version.split(' ')[0]))


import os

from PyQt4 import QtGui, QtCore, uic
from PyKDE4.kdeui import KApplication, KStatusNotifierItem, KNotification
from PyKDE4.kdecore import ki18n, KAboutData, KCmdLineArgs

import pexpect


QtCore.pyqtRemoveInputHook()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

FormClass, BaseClass = uic.loadUiType('main.ui')
assert BaseClass is QtGui.QDialog


def keep_rect_within_screen_bounds(rect):
    assert isinstance(rect, QtCore.QRect)
    screen = QtGui.QApplication.desktop().screenGeometry()
    if rect.top() < screen.top():
        rect.moveTop(screen.top())
    if rect.right() > screen.right():
        rect.moveRight(screen.right())
    if rect.bottom() > screen.bottom():
        rect.moveBottom(screen.bottom())
    if rect.left() < screen.left():
        rect.moveLeft(screen.left())


class Window(QtGui.QDialog, FormClass):

    def __init__(self):
        super().__init__()
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)

        self.setupUi(self)

        # http://api.kde.org/4.x-api/kdelibs-apidocs/kdeui/html/classKStatusNotifierItem.html
        self.tray = KStatusNotifierItem("someId", self)
        self.tray.setCategory(KStatusNotifierItem.ApplicationStatus)
        self.tray.setIconByName(os.path.join(BASE_DIR, "monitor.png"))
        self.tray.setStatus(KStatusNotifierItem.Active)
        self.tray.setToolTipIconByName(os.path.join(BASE_DIR, "monitor.png"))
        self.tray.setToolTipTitle("ViewShow - a screen recorder")
        self.tray.setToolTipSubTitle("Click to start recording")

        screen = QtGui.QApplication.desktop().screenGeometry()
        rect = screen.adjusted(screen.width() / 4, screen.height() / 4,
                               -screen.width() / 4, -screen.height() / 4)
        self.setGeometry(rect)

        self.recorder = None
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)  # once per second
        self.timer.timeout.connect(self.check_recording_status)

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            event.accept()
            self.drag_position = event.globalPos()
            self.drag_widget_name = QtGui.QApplication.widgetAt(event.globalPos()).objectName()

    def mouseMoveEvent(self, event):
        # is called only when a mouse button is pressed
        if event.buttons() == QtCore.Qt.LeftButton:
            event.accept()
            rect = self.geometry()
            delta = event.globalPos() - self.drag_position
            if self.drag_widget_name == 'centerLabel':
                rect.moveTo(self.pos() + delta)
            elif self.drag_widget_name == 'topLeftGrip':
                rect.adjust(delta.x(), delta.y(), 0, 0)
            elif self.drag_widget_name == 'topGrip':
                rect.adjust(0, delta.y(), 0, 0)
            elif self.drag_widget_name == 'topRightGrip':
                rect.adjust(0, delta.y(), delta.x(), 0)
            elif self.drag_widget_name == 'rightGrip':
                rect.adjust(0, 0, delta.x(), 0)
            elif self.drag_widget_name == 'bottomRightGrip':
                rect.adjust(0, 0, delta.x(), delta.y())
            elif self.drag_widget_name == 'bottomGrip':
                rect.adjust(0, 0, 0, delta.y())
            elif self.drag_widget_name == 'bottomLeftGrip':
                rect.adjust(delta.x(), 0, 0, delta.y())
            elif self.drag_widget_name == 'leftGrip':
                rect.adjust(delta.x(), 0, 0, 0)
            keep_rect_within_screen_bounds(rect)
            self.setGeometry(rect)
            self.drag_position = event.globalPos()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            event.accept()
            widget_name = QtGui.QApplication.widgetAt(event.globalPos()).objectName()
            if widget_name == 'centerLabel':
#                self.showMinimized()  # minimize the window
                self.hide()
                self.start_recording()
            else:
                self.setWindowState(self.windowState() ^ QtCore.Qt.WindowFullScreen)

    def done(self, status):
        super().done(status)
        self.close()

    def start_recording(self):
        rect = self.geometry()
        screen = QtGui.QApplication.desktop().screenGeometry()
        rect = rect.intersected(screen)
        if rect.width() % 2:
            # make the width divisible by 2
            rect.setWidth(rect.width() + 1)
            if rect.right() > screen.right():
                rect.moveRight(screen.right())
        if rect.height() % 2:
            # make the height divisible by 2
            rect.setHeight(rect.height() + 1)
            if rect.bottom() > screen.bottom():
                rect.moveBottom(screen.bottom())
        filename_template = 'test%d.mkv'
        i = 1
        while True:
            filename = filename_template % i
            if not os.path.exists(filename):
                break
            i += 1
        cmd = ('avconv -f x11grab -r 15 -s %dx%d -i :0.0+%d,%d -c:v libx264 -preset ultrafast '
               '-crf 0 %s') % (rect.width(), rect.height(), rect.left(), rect.top(), filename)
        self.recorder = pexpect.spawn(cmd)
        self.timer.start()
        KNotification.event(KNotification.Notification, 'ShowView', 'Screen recording started')

    def check_recording_status(self):
        if not self.recorder.isalive():
            print('The recorder is dead!')
            print(self.recorder.read())
        else:
            print('The recorder is alive!')

    def stop_recording(self):
        if self.recorder:
            self.timer.stop()
#            print(self.recorder.read_nonblocking(1000, 0))
            self.recorder.terminate(force=True)
            KNotification.event(KNotification.Notification, self.recorder.read())

    def closeEvent(self, qCloseEvent):
        print('close event')
        self.stop_recording()

    def resizeEvent(self, qResizeEvent):
        # TODO: show new dimensions to user
        print('Resize event')
        super().resizeEvent(qResizeEvent)

    def moveEvent(self, qResizeEvent):
        # show new position to user
        print('Move event')
        super().moveEvent(qResizeEvent)


if __name__ == '__main__':

    appName = "viewshow"
    catalog = ""
    programName = ki18n("ViewShow")
    version = "0.1"
    description = ki18n("KDE screen recorder")
    license = KAboutData.License_GPL
    copyright = ki18n("(c) 2013 Victor Varvariuc")
    text = ki18n("none")
    homePage = "https://github.com/warvariuc/viewshow"
    bugEmail = "victor.varvariuc@gmail.com"

    aboutData = KAboutData(appName, catalog, programName, version, description,
                           license, copyright, text, homePage, bugEmail)

    KCmdLineArgs.init(sys.argv, aboutData)

    app = KApplication()

    window = Window()
    window.show()

    sys.exit(app.exec())
