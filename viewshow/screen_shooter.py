__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import datetime
import os

from PyQt4 import QtCore, QtGui

from viewshow import utils


class ScreenShooter():

    DIRECTORY = '~/Desktop/'
    FILENAME = 'screenshot_{timestamp:%Y-%m-%d_%H-%M-%S}_{width}x{height}'
    IMAGE_FORMAT = 'png'

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
            timestamp=datetime.datetime.now(), width=image.width(), height=image.height()
        ) + '.' + self.IMAGE_FORMAT
        file_path = utils.find_available_path(os.path.join(self.DIRECTORY, file_name))
        image.save(file_path, self.IMAGE_FORMAT)
        return file_path
