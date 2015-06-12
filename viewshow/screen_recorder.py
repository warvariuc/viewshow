__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import os
import datetime
import subprocess

from PyQt4 import QtCore

import pexpect


class ScreenRecorder(QtCore.QObject):

    CMD = ('avconv -f x11grab -r {frame_rate} -s {rect_width}x{rect_height} '
           '-i :0.0+{rect_left},{rect_top} -c:v libx264 -preset ultrafast -crf 0 '
           '{movie_file_path}')
    FRAME_RATE = 15
    MOVIE_FILENAME_TEMPLATE = '~/screen_{timestamp:%Y-%m-%d_%H-%M-%S}_{width}x{height}.mkv'

    recording_failed = QtCore.pyqtSignal(str)
    recording_started = QtCore.pyqtSignal(str)
    recording_finished = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)  # once per second
        self.timer.timeout.connect(self.check_recorder_status)
        self.movie_file_path = None  # where the video as saved to
        self.recorder = None

    @classmethod
    def check_preconditions(cls):
        """Verify that the host system has necessary programs to run this recorder.
        """
        try:
            output = subprocess.check_output('avconv -codecs', shell=True)
        except subprocess.CalledProcessError:
            return '`avconv` command not found. Please install `libav-tools` package.'

        if 'libx264' not in output.decode():
            return '`libx264` codec not supported. Please install `libavcodec-extra-*` package.'

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
            # print('The recorder is alive!')
            return True

    def stop_recording(self):
        if self.recorder:
            self.timer.stop()
            # print(self.recorder.read_nonblocking(1000, 0))
            self.recorder.terminate(force=True)
            self.recording_finished.emit(self.movie_file_path)
            self.movie_file_path = None
            self.recorder = None
