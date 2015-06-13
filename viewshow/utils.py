import os

from PyQt4 import uic


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def icon_path(icon_file_name):
    return os.path.join(BASE_DIR, 'ui/icons', icon_file_name)


def load_ui_file(file_name):
    FormClass, BaseClass = uic.loadUiType(os.path.join(BASE_DIR, 'ui', file_name))

    class FormClass(FormClass):
        def setupUi(self, *args, **kwargs):
            # change directory so that relative paths to icons would work
            cwd = os.getcwd()
            os.chdir(os.path.join(BASE_DIR, 'ui'))
            super().setupUi(*args, **kwargs)
            os.chdir(cwd)  # change to the previous directory

    return FormClass, BaseClass
