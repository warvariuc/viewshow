__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import datetime
import os
import tempfile

from PyQt4 import QtCore, QtGui

from viewshow import utils


class Screenshot(QtGui.QPixmap):
    """Pixmap with creation date-time.
    """
    def __init__(self, *args, timestamp=None):
        self.timestamp = timestamp or datetime.datetime.now()
        self.path = None
        super().__init__(*args)

    @classmethod
    def make(cls, rect=None):
        """Make a screenshot of the desktop.
        """
        desktop_widget = QtGui.QApplication.desktop()
        if rect is None:
            rect = desktop_widget.geometry()
        image = cls.grabWindow(
            desktop_widget.winId(), rect.x(), rect.y(), rect.width(), rect.height())
        # http://stackoverflow.com/questions/30966200/casting-a-qobject-subclass-instance
        image = cls(image)
        image.save()
        return image

    def save(
            self, file_name_format='screenshot_{timestamp:%Y-%m-%d_%H-%M-%S}_{width}x{height}',
            directory='', image_format='png'):
        if not directory:
            directory = tempfile.gettempdir()
        file_name = file_name_format.format(
            timestamp=datetime.datetime.now(), width=self.width(), height=self.height()
        ) + '.' + image_format
        self.path = utils.auto_increment_file_name(os.path.join(directory, file_name))
        super().save(self.path, image_format)
