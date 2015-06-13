__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import datetime
import os

from PyQt4 import QtCore, QtGui


class ScreenShooter():

    DIRECTORY = '~/Desktop/'
    FILENAME = 'screenshot_{timestamp:%Y-%m-%d_%H-%M-%S}_{width}x{height}'
    FORMAT = 'png'

    def __init__(self):
        pass

    @classmethod
    def check_preconditions(cls):
        pass

    def make_screenshot(self, rect):
        assert isinstance(rect, QtCore.QRect)
        screenshot = QtGui.QPixmap.grabWindow(
            QtGui.QApplication.desktop().winId(), rect.x(), rect.y(), rect.width(), rect.height())
        return screenshot

    def save_image(self, image):
        assert isinstance(image, QtGui.QPixmap)
        file_name = self.FILENAME.format(
            timestamp=datetime.datetime.now(), width=image.width(), height=image.height())
        file_path = os.path.join(os.path.expanduser(self.DIRECTORY), file_name)
        # detect file name
        _file_path = file_path
        i = 1
        while True:
            if not os.path.exists(_file_path):
                break
            i += 1
            _file_path = '%s(%d)' % (file_path, i)

        file_path = _file_path + '.' + self.FORMAT
        image.save(file_path, self.FORMAT)
        return file_path
