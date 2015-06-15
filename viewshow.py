#!/usr/bin/env python3
__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import sys

PYTHON_REQUIRED_VERSION = '3.4'  # tested with this version
if sys.version < PYTHON_REQUIRED_VERSION:
    raise SystemExit('Bad Python version', 'Python %s or newer required (you are using %s).'
                     % (PYTHON_REQUIRED_VERSION, sys.version.split(' ')[0]))


import os
import subprocess
import time

from PyQt4 import QtGui, QtCore
import sip
# http://api.kde.org/4.x-api/kdelibs-apidocs/kdeui/html/classKStatusNotifierItem.html
from PyKDE4 import kdecore, kdeui

from viewshow.screen_recorder import ScreenRecorder
from viewshow.screen_shooter import ScreenshotDialog
from viewshow.dropbox_client import DropboxClient
from viewshow import utils


QtCore.pyqtRemoveInputHook()
# http://stackoverflow.com/questions/23565702/pyqt4-crashed-on-exit
sip.setdestroyonexit(False)


def adjust_rect(rect, dx1, dy1, dx2, dy2):
    """Return an adjusted rect within screen bounds
    """
    assert isinstance(rect, QtCore.QRect)
    rect = rect.adjusted(dx1, dy1, dx2, dy2)
    screen = QtGui.QApplication.desktop().screenGeometry()
    if rect.top() < screen.top():
        rect.moveTop(screen.top())
    if rect.right() > screen.right():
        rect.moveRight(screen.right())
    if rect.bottom() > screen.bottom():
        rect.moveBottom(screen.bottom())
    if rect.left() < screen.left():
        rect.moveLeft(screen.left())
    return rect


FormClass = utils.load_form('main.ui', QtGui.QDialog)


class ScreenSelector(FormClass):

    def __init__(self):
        super().__init__()
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)

        self.setupUi(self)
        self.startRecordingButton.clicked.connect(self.start_recording)
        self.makeScreenshotButton.clicked.connect(self.make_screenshot)

        self.tray = kdeui.KStatusNotifierItem("ViewShow", self)
        self.tray.setCategory(kdeui.KStatusNotifierItem.ApplicationStatus)
        self.tray.setStatus(kdeui.KStatusNotifierItem.Active)
        self.tray.setToolTipTitle("ViewShow - a screen recorder")
        self.tray.activateRequested.connect(self.on_tray_activate_requested)
        self.minimizeButton.clicked.connect(lambda: self.showMinimized())
        self.quitButton.clicked.connect(self.reject)

        self.tray.contextMenu().addAction(kdeui.KStandardAction.aboutApp(
            kdeui.KAboutApplicationDialog(None, self).show,
            self.tray.actionCollection()
        ))

        # center the window
        screen = QtGui.QApplication.desktop().screenGeometry()
        rect = screen.adjusted(screen.width() / 4, screen.height() / 4,
                               -screen.width() / 4, -screen.height() / 4)
        self.setGeometry(rect)

        self.recorder = ScreenRecorder(self)
        self.recorder.recording_started.connect(self.on_recorder_started)
        self.recorder.recording_failed.connect(self.on_recorder_failed)
        self.recorder.recording_finished.connect(self.on_recorder_finished)

        self.set_state('selecting')
        self.drag_position = QtCore.QRect()
        self.drag_widget_name = ''

    def set_state(self, state, text=''):
        if state == 'hidden':
            # the selection window is hidden
            self.tray.setIconByName(utils.icon_path('monitor.png'))
            self.tray.setToolTipIconByName(utils.icon_path('monitor.png'))
            self.tray.setToolTipSubTitle('Click to show')
            self.hide()
        elif state == 'selecting':
            # the selection window is shown
            self.tray.setIconByName(utils.icon_path('monitor.png'))
            self.tray.setToolTipIconByName(utils.icon_path('monitor.png'))
            self.tray.setToolTipSubTitle('Click to hide')
            self.show()
        elif state == 'recording':
            # the screen is being recorded, the selection window is hidden
            self.tray.setIconByName(utils.icon_path('film.png'))
            self.tray.setToolTipIconByName(utils.icon_path('film.png'))
            self.tray.setToolTipSubTitle(
                'A Screen recording is in process (%s). Left click to stop.' % text)
            self.hide()
        else:
            raise AssertionError('Unknown state')

    def on_tray_activate_requested(self, active):
        if self.recorder.is_active():
            self.recorder.stop_recording()
        elif active:
            self.set_state('selecting')
        else:
            self.set_state('hidden')

    def start_recording(self):
        self.recorder.start_recording(
            self.geometry(), QtGui.QApplication.desktop().screenGeometry())

    def stop_recording(self):
        self.recorder.stop_recording()

    def on_recorder_started(self, file_name):
        self.set_state('recording', file_name)
        # KNotification.event(KNotification.Notification, 'ShowView',
        #                     'Screen recording started:\n%s' % file_name)

    def on_recorder_finished(self, movie_path):
        self.set_state('selecting')
        self.tray.showMessage(
            'Recording finished',
            'The recorded movie: <a href="%s">%s</a>' % (movie_path, os.path.basename(movie_path)),
            utils.icon_path('film.png')
        )

    def on_recorder_failed(self, text):
        print(text)
        self.set_state('hidden')
        self.tray.showMessage(
            'Recording failed',
            'The recorder process has unexpectedly stopped. The movie file might be unredable.',
            utils.icon_path('exclamation.png')
        )

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
            if self.drag_widget_name == 'centerGrip':
                rect.moveTo(self.pos() + delta)
                rect = adjust_rect(rect, 0, 0, 0, 0)
            elif self.drag_widget_name == 'topLeftGrip':
                rect = adjust_rect(rect, delta.x(), delta.y(), 0, 0)
            elif self.drag_widget_name == 'topGrip':
                rect = adjust_rect(rect, 0, delta.y(), 0, 0)
            elif self.drag_widget_name == 'topRightGrip':
                rect = adjust_rect(rect, 0, delta.y(), delta.x(), 0)
            elif self.drag_widget_name == 'rightGrip':
                rect = adjust_rect(rect, 0, 0, delta.x(), 0)
            elif self.drag_widget_name == 'bottomRightGrip':
                rect = adjust_rect(rect, 0, 0, delta.x(), delta.y())
            elif self.drag_widget_name == 'bottomGrip':
                rect = adjust_rect(rect, 0, 0, 0, delta.y())
            elif self.drag_widget_name == 'bottomLeftGrip':
                rect = adjust_rect(rect, delta.x(), 0, 0, delta.y())
            elif self.drag_widget_name == 'leftGrip':
                rect = adjust_rect(rect, delta.x(), 0, 0, 0)
            self.setGeometry(rect)
            self.drag_position = event.globalPos()

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            event.accept()
            self.setWindowState(self.windowState() ^ QtCore.Qt.WindowFullScreen)

    def done(self, status):
        super().done(status)
        self.close()

    def closeEvent(self, q_close_event):
        self.stop_recording()
        super().closeEvent(q_close_event)

    def keyPressEvent(self, q_key_event):
        key = q_key_event.key()
        rect = self.geometry()
        if q_key_event.modifiers() in (QtCore.Qt.NoModifier, QtCore.Qt.KeypadModifier):
            if key == QtCore.Qt.Key_Up:
                self.setGeometry(adjust_rect(rect, 0, -1, 0, -1))
                return
            if key == QtCore.Qt.Key_Down:
                self.setGeometry(adjust_rect(rect, 0, 1, 0, 1))
                return
            if key == QtCore.Qt.Key_Left:
                self.setGeometry(adjust_rect(rect, -1, 0, -1, 0))
                return
            if key == QtCore.Qt.Key_Right:
                self.setGeometry(adjust_rect(rect, 1, 0, 1, 0))
                return
            if key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
                self.makeScreenshotButton.animateClick()
                return
        elif q_key_event.modifiers() == QtCore.Qt.ShiftModifier:
            if key == QtCore.Qt.Key_Up:
                self.setGeometry(adjust_rect(rect, 0, -1, 0, 0))
                return
            if key == QtCore.Qt.Key_Down:
                self.setGeometry(adjust_rect(rect, 0, 0, 0, 1))
                return
            if key == QtCore.Qt.Key_Left:
                self.setGeometry(adjust_rect(rect, -1, 0, 0, 0))
                return
            if key == QtCore.Qt.Key_Right:
                self.setGeometry(adjust_rect(rect, 0, 0, 1, 0))
                return
            if key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
                self.startRecordingButton.animateClick()
                return
        return super().keyPressEvent(q_key_event)

    def resizeEvent(self, q_resize_event):
        # TODO: show new dimensions to user
        super().resizeEvent(q_resize_event)
        self.setGeometry(adjust_rect(self.geometry(), 0, 0, 0, 0))

    def moveEvent(self, q_move_event):
        # TODO: show new position to user
        super().moveEvent(q_move_event)
        self.setGeometry(adjust_rect(self.geometry(), 0, 0, 0, 0))

    def make_screenshot(self):
        self.hide()
        time.sleep(0.5)  # wait for the desktop effects to finish
        image = utils.make_screenshot(self.geometry())
        image_path = utils.save_image(image)
        screen_shooter = ScreenshotDialog(self, image_path)
        screen_shooter.exec()

        # file_path = screenshooter.save_image(image)
        #
        # try:
        #     image_url = DropboxClient().upload_image(file_path)
        # except Exception as exc:
        #     QtGui.QMessageBox.critical(
        #         self, 'Error', 'There was an error while trying to upload the image:\n%s', exc)
        # else:
        #     clipboard = QtGui.QApplication.clipboard()
        #     clipboard.setText(image_url)
        #     msg_box = QtGui.QMessageBox(
        #         QtGui.QMessageBox.Information, 'The image was successfully uploaded',
        #         'Find the uploaded image here: <a href="%s">%s</a>\n'
        #         'The URL was also copied to the clipboard' % (image_url, image_url),
        #         QtGui.QMessageBox.Open | QtGui.QMessageBox.Close, self)
        #     msg_box.setTextFormat(QtCore.Qt.RichText)
        #     result = msg_box.exec()
        #     if result == QtGui.QMessageBox.Open:
        #         import webbrowser
        #         webbrowser.open(image_url)

        self.show()


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

    preconditions_error = ScreenRecorder.check_preconditions()
    if preconditions_error:
        error('Preconditions are not satisfied', preconditions_error)

    kdecore.KCmdLineArgs.init(sys.argv, make_about_data())

    app = kdeui.KApplication()
    app.setOrganizationName("warvariuc")
    app.setApplicationName("viewshow")
    # app.setQuitOnLastWindowClosed(False)

    screen_selector = ScreenSelector()
    screen_selector.show()

    app.exec()
    # del screen_selector  # othewise the app crashes
