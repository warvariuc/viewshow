#!/usr/bin/env python3
__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import sys

python_required_version = '3.2'  # tested with this version
if sys.version < python_required_version:
    raise SystemExit('Bad Python version', 'Python %s or newer required (you are using %s).'
                     % (python_required_version, sys.version.split(' ')[0]))


import os
import datetime

from PyQt4 import QtGui, QtCore, uic
# http://api.kde.org/4.x-api/kdelibs-apidocs/kdeui/html/classKStatusNotifierItem.html
from PyKDE4 import kdecore, kdeui
from PyKDE4.kdecore import ki18n

import pexpect


QtCore.pyqtRemoveInputHook()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

FormClass, BaseClass = uic.loadUiType('main.ui')
assert BaseClass is QtGui.QDialog


def icon_path(icon_file_name):
    return os.path.join(BASE_DIR, icon_file_name)


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



class Window(QtGui.QDialog, FormClass):

    def __init__(self):
        super().__init__()
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)

        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon(icon_path('monitor.png')))
        # workaround - aligment via designer is not working for me
        self.centerGrip.layout().setAlignment(self.quitButton, QtCore.Qt.AlignHCenter)
        self.startButton.setIcon(QtGui.QIcon(icon_path('film.png')))
        self.startButton.clicked.connect(self.start_recording)

        self.tray = kdeui.KStatusNotifierItem("ViewShow", self)
        self.tray.setCategory(kdeui.KStatusNotifierItem.ApplicationStatus)
        self.tray.setStatus(kdeui.KStatusNotifierItem.Active)
        self.tray.setToolTipTitle("ViewShow - a screen recorder")
        self.tray.activateRequested.connect(self.on_tray_activate_requested)

        self.tray.contextMenu().addAction(kdeui.KStandardAction.aboutApp(
            kdeui.KAboutApplicationDialog(None, self).show,
            self.tray.actionCollection()
        ))

        # center the window
        screen = QtGui.QApplication.desktop().screenGeometry()
        rect = screen.adjusted(screen.width() / 4, screen.height() / 4,
                               - screen.width() / 4, -screen.height() / 4)
        self.setGeometry(rect)

        self.recorder = ScreenRecorder(self)
        self.recorder.recording_started.connect(self.on_recorder_started)
        self.recorder.recording_failed.connect(self.on_recorder_failed)
        self.recorder.recording_finished.connect(self.on_recorder_finished)

        self.set_state('selecting')

    def set_state(self, state, text=''):
        if state == 'hidden':
            # the selection window is hidden
            self.tray.setIconByName(icon_path('monitor.png'))
            self.tray.setToolTipIconByName(icon_path('monitor.png'))
            self.tray.setToolTipSubTitle('Click to show')
            self.hide()
        elif state == 'selecting':
            # the selection window is shown
            self.tray.setIconByName(icon_path('monitor.png'))
            self.tray.setToolTipIconByName(icon_path('monitor.png'))
            self.tray.setToolTipSubTitle('Click to hide')
            self.show()
        elif state == 'recording':
            # the screen is being recorded, the selection window is hidden
            self.tray.setIconByName(icon_path('film.png'))
            self.tray.setToolTipIconByName(icon_path('film.png'))
            self.tray.setToolTipSubTitle('A Screen recording is in process (%s). '
                                         'Left click to stop.' % text)
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
        self.recorder.start_recording(self.geometry(),
                                      QtGui.QApplication.desktop().screenGeometry())

    def stop_recording(self):
        self.recorder.stop_recording()

    def on_recorder_started(self, file_name):
            self.set_state('recording', file_name)
#        KNotification.event(KNotification.Notification, 'ShowView', 'Screen recording started:\n%s'
#                                                                    % file_name)

    def on_recorder_finished(self, movie_path):
        self.set_state('selecting')
        self.tray.showMessage(
            'Recording finished',
            'The recorded movie: <a href="%s">%s</a>' % (movie_path, os.path.basename(movie_path)),
            icon_path('film.png')
        )

    def on_recorder_failed(self, text):
        print(text)
        self.set_state('hidden')
        self.tray.showMessage(
            'Recording failed',
            'The recorder process has unexpectedly stopped. The movie file might be unredable.',
            icon_path('exclamation.png')
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
            widget_name = QtGui.QApplication.widgetAt(event.globalPos()).objectName()
            if widget_name == 'centerGrip':
                self.start_recording()
            else:
                self.setWindowState(self.windowState() ^ QtCore.Qt.WindowFullScreen)

    def done(self, status):
        super().done(status)
        self.close()

    def closeEvent(self, qCloseEvent):
        self.stop_recording()

    def keyPressEvent(self, qKeyEvent):
        key = qKeyEvent.key()
        rect = self.geometry()
        if qKeyEvent.modifiers() in (QtCore.Qt.NoModifier, QtCore.Qt.KeypadModifier):
            if key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
                self.startButton.animateClick()
                return
            elif key == QtCore.Qt.Key_Up:
                self.setGeometry(adjust_rect(rect, 0, -1, 0, -1))
                return
            elif key == QtCore.Qt.Key_Down:
                self.setGeometry(adjust_rect(rect, 0, 1, 0, 1))
                return
            elif key == QtCore.Qt.Key_Left:
                self.setGeometry(adjust_rect(rect, -1, 0, -1, 0))
                return
            elif key == QtCore.Qt.Key_Right:
                self.setGeometry(adjust_rect(rect, 1, 0, 1, 0))
                return
        elif qKeyEvent.modifiers() == QtCore.Qt.ShiftModifier:
            if key == QtCore.Qt.Key_Up:
                self.setGeometry(adjust_rect(rect, 0, -1, 0, 0))
                return
            elif key == QtCore.Qt.Key_Down:
                self.setGeometry(adjust_rect(rect, 0, 0, 0, 1))
                return
            elif key == QtCore.Qt.Key_Left:
                self.setGeometry(adjust_rect(rect, -1, 0, 0, 0))
                return
            elif key == QtCore.Qt.Key_Right:
                self.setGeometry(adjust_rect(rect, 0, 0, 1, 0))
                return
        return super().keyPressEvent(qKeyEvent)

    def resizeEvent(self, qResizeEvent):
        # TODO: show new dimensions to user
        super().resizeEvent(qResizeEvent)
        self.setGeometry(adjust_rect(self.geometry(), 0, 0, 0, 0))

    def moveEvent(self, qResizeEvent):
        # TODO: show new position to user
        super().moveEvent(qResizeEvent)
        self.setGeometry(adjust_rect(self.geometry(), 0, 0, 0, 0))


class ScreenRecorder(QtCore.QObject):

    recording_failed = QtCore.pyqtSignal(str)
    recording_started = QtCore.pyqtSignal(str)
    recording_finished = QtCore.pyqtSignal(str)

    CMD = ('avconv -f x11grab -r {frame_rate} -s {rect_width}x{rect_height} '
           '-i :0.0+{rect_left},{rect_top} -c:v libx264 -preset ultrafast -crf 0 '
           '{movie_file_path}')
    FRAME_RATE = 15
    MOVIE_FILENAME_TEMPLATE = '~/screen_{timestamp:%Y-%m-%d_%H-%M-%S}_{width}x{height}.mkv'

    def __init__(self, parent):
        super().__init__(parent)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)  # once per second
        self.timer.timeout.connect(self.check_recorder_status)
        self.movie_file_path = None  # where the video as saved to
        self.recorder = None

    def check_preconditions(self):
        """Verify that the host system has necessary programs to run this recorder.
        """
        raise NotImplementedError

    def is_active(self):
        """Whether the recording process is going on
        """
        return self.recorder is not None

    def normalize_selection(self, rect, screen_rect):
        """Ensure that the recorded region is inside the screen, otherwise avconv will fail.
        """
        assert isinstance(rect, QtCore.QRect)
        assert isinstance(screen_rect, QtCore.QRect)

        rect = rect.intersected(screen_rect)
        # make sure that the recorded region width/height is divisible by 2
        if rect.width() % 2:
            # make the width divisible by 2
            rect.setWidth(rect.width() + 1)
            if rect.right() > screen_rect.right():
                rect.moveRight(screen_rect.right())
        if rect.height() % 2:
            # make the height divisible by 2
            rect.setHeight(rect.height() + 1)
            if rect.bottom() > screen_rect.bottom():
                rect.moveBottom(screen_rect.bottom())

        return rect

    def start_recording(self, rect, screen_rect, frame_rate=0, filename_template=''):
        """Start the recording process.
        """
        rect = self.normalize_selection(rect, screen_rect)
        frame_rate = frame_rate or self.FRAME_RATE
        filename_template = filename_template or self.MOVIE_FILENAME_TEMPLATE
        movie_path = filename_template.format(timestamp=datetime.datetime.now(),
                                              width=rect.width(), height=rect.height())
        movie_path = os.path.expanduser(movie_path)
        # detect file name
        _movie_path = movie_path
        i = 1
        while True:
            if not os.path.exists(_movie_path):
                movie_path = _movie_path
                break
            i += 1
            _movie_path = '%s(%d)' % (movie_path, i)
        self.movie_file_path = movie_path
        # make the command
        cmd = self.CMD.format(
            movie_file_path=self.movie_file_path,
            frame_rate=frame_rate,
            rect_left=rect.left(),
            rect_top=rect.top(),
            rect_width=rect.width(),
            rect_height=rect.height(),
        )
        # spawn avconv recording process
        self.recorder = pexpect.spawn(cmd)
        # start recorder status verifier timed
        self.timer.start()
        self.recording_started.emit(self.movie_file_path)

    def check_recorder_status(self):
        if self.recorder is None:
            return None
        if not self.recorder.isalive():
            self.timer.stop()
            self.recording_failed.emit(self.recorder.read())
            self.movie_file_path = None
            self.recorder = None
            return False
        else:
        #            print('The recorder is alive!')
            return True

    def stop_recording(self):
        if self.recorder:
            self.timer.stop()
            #            print(self.recorder.read_nonblocking(1000, 0))
            self.recorder.terminate(force=True)
            self.recording_finished.emit(self.movie_file_path)
            self.movie_file_path = None
            self.recorder = None


if __name__ == '__main__':

    appName = "viewshow"
    catalog = ""
    programName = ki18n("ViewShow")
    version = "0.3"
    description = ki18n("""\
A KDE screen recorder.
This application uses <a href="http://p.yusukekamiyamane.com/">Fugue Icons</a>.
""")
    license = kdecore.KAboutData.License_GPL
    copyright = ki18n("(c) 2013 Victor Varvariuc")
    text = ki18n("")
    homePage = "https://github.com/warvariuc/viewshow"
    bugEmail = "victor.varvariuc@gmail.com"

    aboutData = kdecore.KAboutData(appName, catalog, programName, version, description,
                                   license, copyright, text, homePage, bugEmail)

    kdecore.KCmdLineArgs.init(sys.argv, aboutData)

    app = kdeui.KApplication()
    app.setQuitOnLastWindowClosed(False)

    window = Window()
    window.show()

    sys.exit(app.exec())
