__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import os

from PyQt4 import QtCore, QtGui
from PyKDE4 import kdecore, kdeui, kio

from viewshow import utils
from viewshow.dropbox_client import DropboxClient
from viewshow import screenshot


class ImageLabel(QtGui.QLabel):

    def resizeEvent(self, event):
        self.parent().update_image_label()


FormClass = utils.load_form('screenshot.ui', QtGui.QDialog)


class ScreenshotDialog(FormClass):

    SETTINGS = {
        'OPEN_WITH_DEFAULT_ACTION': 'screenshot/open-with-default-action',
        'SEND_TO_DEFAULT_ACTION': 'screenshot/send-to-default-action',
        'LAST_SAVE_PATH': 'screenshot/last-save-path',
    }

    def __init__(self, *args, image):
        assert isinstance(image, screenshot.Screenshot)
        self.image = image

        super().__init__(*args)
        self.setupUi(self)

        self.file_watcher = QtCore.QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.on_image_file_changed)
        self.on_image_file_changed()

        self.setup_openWithButton()
        self.setup_sendToButton()

    def setup_openWithButton(self):
        menu = QtGui.QMenu(self)
        menu.triggered.connect(self.on_openWithButton_action_triggered)
        services = kdecore.KMimeTypeTrader.self().query('image/png')
        for service in services:
            menu.addAction(KServiceAction(
                kdeui.KIcon(service.icon()), service.name().replace('&', '&&'), self,
                service=service))
        menu.addSeparator()
        menu.addAction(KServiceAction(
            kdeui.KIcon(), kdecore.i18n('Other Application...'), self, service=None))
        self.openWithButton.setMenu(menu)

        settings = QtCore.QSettings()
        default_action_name = settings.value(self.SETTINGS['OPEN_WITH_DEFAULT_ACTION'])
        for action in menu.actions():
            if action.service.name() == default_action_name:
                break
        else:
            action = menu.actions()[0]
        self.openWithButton.setDefaultAction(action)

    def on_openWithButton_action_triggered(self, action):
        if action is None:
            return
        url_list = kdecore.KUrl.List([self.image.path])
        service = action.service
        if service is None:
            # other application requested
            open_with_dialog = kio.KOpenWithDialog(url_list, self)
            if not open_with_dialog.exec():
                return
            service = open_with_dialog.service()
            if not service and not open_with_dialog.text().isEmpty():
                # a path to an application was given
                kio.KRun.run(open_with_dialog.text(), url_list, self)
                return
        else:
            self.openWithButton.setDefaultAction(action)
        kio.KRun.run(service, url_list, self)
        QtCore.QSettings().setValue(self.SETTINGS['OPEN_WITH_DEFAULT_ACTION'],
                                    self.openWithButton.defaultAction().service.name())

    def setup_sendToButton(self):
        menu = QtGui.QMenu(self)
        menu.triggered.connect(self.on_sendToButton_action_triggered)
        services = [kdecore.KService('Dropbox', '', '')]
        for service in services:
            menu.addAction(KServiceAction(
                kdeui.KIcon(service.icon()), service.name().replace('&', '&&'), self,
                service=service))
        self.sendToButton.setMenu(menu)

        settings = QtCore.QSettings()
        default_action_name = settings.value(self.SETTINGS['SEND_TO_DEFAULT_ACTION'])
        for action in menu.actions():
            if action.service.name() == default_action_name:
                break
        else:
            action = menu.actions()[0]
        self.sendToButton.setDefaultAction(action)

    def on_sendToButton_action_triggered(self, action):
        if action.service.name() != 'Dropbox':
            QtGui.QMessageBox.critical(
                self, 'Unsupported destination', 'This destination is not supported')
            return
        try:
            image_url = DropboxClient(self).upload_image(self.image.path)
        except Exception as exc:
            QtGui.QMessageBox.critical(
                self, 'Error', 'There was an error while trying to upload the image:\n%s' % exc)
            return
        clipboard = QtGui.QApplication.clipboard()
        clipboard.setText(image_url)
        msg_box = QtGui.QMessageBox(
            QtGui.QMessageBox.Information, 'The image was successfully uploaded',
            'Find the uploaded image here: <a href="%s">%s</a>\n'
            'The URL was also copied to the clipboard.' % (image_url, image_url),
            QtGui.QMessageBox.Open | QtGui.QMessageBox.Close, self)
        msg_box.setTextFormat(QtCore.Qt.RichText)
        result = msg_box.exec()
        if result == QtGui.QMessageBox.Open:
            import webbrowser
            webbrowser.open(image_url)
        QtCore.QSettings().setValue(self.SETTINGS['SEND_TO_DEFAULT_ACTION'],
                                    self.sendToButton.defaultAction().service.name())

    @QtCore.pyqtSlot()
    def on_copyButton_clicked(self):
        clipboard = QtGui.QApplication.clipboard()
        clipboard.setPixmap(self.imageLabel.pixmap())

    def on_image_file_changed(self):
        if self.image.path not in self.file_watcher.files():
            self.file_watcher.addPath(self.image.path)
        image = screenshot.Screenshot()
        image.load(self.image.path)
        image.path = self.image.path
        self.image = image
        self.update_image_label()

    def update_image_label(self):
        self.imageLabel.setPixmap(self.image.scaled(
            self.imageLabel.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

    @QtCore.pyqtSlot()
    def on_saveAsButton_clicked(self):
        save_dir = os.path.dirname(QtCore.QSettings().value(self.SETTINGS['LAST_SAVE_PATH'], ''))
        if save_dir:
            file_path = os.path.join(save_dir, os.path.split(self.image.path)[1])
        else:
            file_path = self.image.path
        file_path = QtGui.QFileDialog.getSaveFileName(
            self, "Save screenshot", file_path, "PNG image (*.png)")
        if not file_path:
            return
        self.imageLabel.pixmap().save(file_path)
        self.image.path = file_path
        QtCore.QSettings().setValue(self.SETTINGS['LAST_SAVE_PATH'], self.image.path)


class KServiceAction(QtGui.QAction):
    """Action with a related service.
    """
    def __init__(self, *args, service):
        super().__init__(*args)
        self.service = service
