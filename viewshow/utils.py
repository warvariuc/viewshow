import os

from PyQt4 import uic


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def icon_path(icon_file_name):
    return os.path.join(BASE_DIR, 'ui/icons', icon_file_name)


def load_form(file_name):
    FormClass, BaseClass = uic.loadUiType(os.path.join(BASE_DIR, 'ui', file_name))

    class FormClass(FormClass):
        def setupUi(self, *args, **kwargs):
            # change directory so that relative paths to icons would work
            cwd = os.getcwd()
            os.chdir(os.path.join(BASE_DIR, 'ui'))
            super().setupUi(*args, **kwargs)
            os.chdir(cwd)  # change to the previous directory

    return FormClass, BaseClass


def normalize_path(path):
    return os.path.expanduser(os.path.expandvars(path))


def get_config_path():
    config_dir = os.environ.get('XDG_CONFIG_HOME', '$HOME/.config')
    config_file_path = os.path.join(config_dir, 'viewshow')
    return config_file_path


def find_available_path(path):
    path, ext = os.path.splitext(normalize_path(path))
    i = 0
    while True:
        _path = path + ('(%s)' % i if i else '') + ext
        if not os.path.exists(_path):
            break
        i += 1
    return _path
