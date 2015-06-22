__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import os
import time

from PyQt4 import QtCore, QtGui
from PyKDE4 import kdecore, kdeui


from viewshow import utils
from viewshow import recorder
from viewshow import screenshot
from viewshow.screenshot_dialog import ScreenshotDialog


FormClass = utils.load_form('main.ui', QtGui.QDialog)

class ScreenSelectorDialog(FormClass):

    def __init__(self, *args, image=None):
        super().__init__(*args)
        self.setupUi()

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

        self.recorder = recorder.ScreenRecorder(self)
        self.recorder.recording_started.connect(self.on_recorder_started)
        self.recorder.recording_failed.connect(self.on_recorder_failed)
        self.recorder.recording_finished.connect(self.on_recorder_finished)

        self.set_state('selecting')
        self.drag_position = QtCore.QRect()
        self.drag_widget_name = ''

        if image is not None:
            self.make_screenshot(image)

    def setupUi(self):
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        super().setupUi(self)
        # center the window
        screen = QtGui.QApplication.desktop().screenGeometry()
        rect = screen.adjusted(screen.width() / 4, screen.height() / 4,
                               -screen.width() / 4, -screen.height() / 4)
        self.setGeometry(rect)

    @QtCore.pyqtSlot()
    def make_screenshot(self, image=None):
        self.hide()
        if image is None:
            time.sleep(0.5)  # wait for the desktop effects to finish
            image = screenshot.Screenshot.make(self.geometry())
        screenshot_dialog = ScreenshotDialog(image=image)
        screenshot_dialog.exec()
        self.show()

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
                rect = utils.adjust_rect(rect, 0, 0, 0, 0)
            elif self.drag_widget_name == 'topLeftGrip':
                rect = utils.adjust_rect(rect, delta.x(), delta.y(), 0, 0)
            elif self.drag_widget_name == 'topGrip':
                rect = utils.adjust_rect(rect, 0, delta.y(), 0, 0)
            elif self.drag_widget_name == 'topRightGrip':
                rect = utils.adjust_rect(rect, 0, delta.y(), delta.x(), 0)
            elif self.drag_widget_name == 'rightGrip':
                rect = utils.adjust_rect(rect, 0, 0, delta.x(), 0)
            elif self.drag_widget_name == 'bottomRightGrip':
                rect = utils.adjust_rect(rect, 0, 0, delta.x(), delta.y())
            elif self.drag_widget_name == 'bottomGrip':
                rect = utils.adjust_rect(rect, 0, 0, 0, delta.y())
            elif self.drag_widget_name == 'bottomLeftGrip':
                rect = utils.adjust_rect(rect, delta.x(), 0, 0, delta.y())
            elif self.drag_widget_name == 'leftGrip':
                rect = utils.adjust_rect(rect, delta.x(), 0, 0, 0)
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
                self.setGeometry(utils.adjust_rect(rect, 0, -1, 0, -1))
                return
            if key == QtCore.Qt.Key_Down:
                self.setGeometry(utils.adjust_rect(rect, 0, 1, 0, 1))
                return
            if key == QtCore.Qt.Key_Left:
                self.setGeometry(utils.adjust_rect(rect, -1, 0, -1, 0))
                return
            if key == QtCore.Qt.Key_Right:
                self.setGeometry(utils.adjust_rect(rect, 1, 0, 1, 0))
                return
            if key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
                self.makeScreenshotButton.animateClick()
                return
        elif q_key_event.modifiers() == QtCore.Qt.ShiftModifier:
            if key == QtCore.Qt.Key_Up:
                self.setGeometry(utils.adjust_rect(rect, 0, -1, 0, 0))
                return
            if key == QtCore.Qt.Key_Down:
                self.setGeometry(utils.adjust_rect(rect, 0, 0, 0, 1))
                return
            if key == QtCore.Qt.Key_Left:
                self.setGeometry(utils.adjust_rect(rect, -1, 0, 0, 0))
                return
            if key == QtCore.Qt.Key_Right:
                self.setGeometry(utils.adjust_rect(rect, 0, 0, 1, 0))
                return
            if key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
                self.startRecordingButton.animateClick()
                return
        return super().keyPressEvent(q_key_event)

    def resizeEvent(self, q_resize_event):
        # TODO: show new dimensions to user
        super().resizeEvent(q_resize_event)
        self.setGeometry(utils.adjust_rect(self.geometry(), 0, 0, 0, 0))

    def moveEvent(self, q_move_event):
        # TODO: show new position to user
        super().moveEvent(q_move_event)
        self.setGeometry(utils.adjust_rect(self.geometry(), 0, 0, 0, 0))
