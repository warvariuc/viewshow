import datetime
import os
import tempfile

from PyQt4 import QtCore, QtGui, uic


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def icon_path(icon_file_name):
    return os.path.join(BASE_DIR, 'ui/icons', icon_file_name)


def load_form(file_name, expected_base_class):
    form_class, base_class = uic.loadUiType(os.path.join(BASE_DIR, 'ui', file_name))
    assert base_class is expected_base_class

    class FormClass(base_class, form_class):
        def setupUi(self, *args, **kwargs):
            # change directory so that relative paths to icons would work
            cwd = os.getcwd()
            os.chdir(os.path.join(BASE_DIR, 'ui'))
            super().setupUi(*args, **kwargs)
            os.chdir(cwd)  # change to the previous directory

    return FormClass


def normalize_path(path):
    return os.path.expanduser(os.path.expandvars(path))


def get_config_path():
    config_dir = os.environ.get('XDG_CONFIG_HOME', '$HOME/.config')
    config_file_path = os.path.join(config_dir, 'viewshow')
    return config_file_path


def auto_increment_file_name(path):
    path, ext = os.path.splitext(normalize_path(path))
    i = 0
    while True:
        _path = path + ('(%s)' % i if i else '') + ext
        if not os.path.exists(_path):
            break
        i += 1
    return _path


def make_screenshot(rect):
    assert isinstance(rect, QtCore.QRect)
    image = QtGui.QPixmap.grabWindow(
        QtGui.QApplication.desktop().winId(), rect.x(), rect.y(), rect.width(), rect.height())
    return image


def save_image(
        image, file_name_format='screenshot_{timestamp:%Y-%m-%d_%H-%M-%S}_{width}x{height}',
        directory='', image_format='png'):
    assert isinstance(image, QtGui.QPixmap)
    if not directory:
        directory = tempfile.gettempdir()
    file_name = file_name_format.format(
        timestamp=datetime.datetime.now(), width=image.width(), height=image.height()
    ) + '.' + image_format
    file_path = auto_increment_file_name(os.path.join(directory, file_name))
    image.save(file_path, image_format)
    return file_path
