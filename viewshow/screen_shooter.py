__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

from PyQt4 import QtCore, QtGui
from PyKDE4 import kdecore, kdeui, kio

from viewshow import utils
from viewshow.dropbox_client import DropboxClient


FormClass = utils.load_form('screenshot.ui', QtGui.QDialog)


class ScreenshotDialog(FormClass):

    OPEN_WITH_DEFAULT_ACTION_SETTING_NAME = 'screenshot/open-with-default-action'
    SEND_TO_DEFAULT_ACTION_SETTING_NAME = 'screenshot/send-to-default-action'

    def __init__(self, parent_widget, image_path):
        super().__init__(parent_widget)
        # self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
        self.setupUi(self)

        self.image_path = image_path
        self.file_watcher = QtCore.QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self._load_image)
        self._load_image()

        self.setup_openWithButton()
        self.setup_sendToButton()

    def setup_openWithButton(self):
        menu = QtGui.QMenu(self)
        menu.triggered.connect(self.on_openWithButton_action_triggered)
        services = kdecore.KMimeTypeTrader.self().query('image/png')
        for service in services:
            menu.addAction(KServiceAction(
                service, kdeui.KIcon(service.icon()), service.name().replace('&', '&&'), self))
        menu.addSeparator()
        menu.addAction(KServiceAction(
            None, kdeui.KIcon(), kdecore.i18n('Other Application...'), self))
        self.openWithButton.setMenu(menu)

        settings = QtCore.QSettings()
        default_action_name = settings.value(self.OPEN_WITH_DEFAULT_ACTION_SETTING_NAME)
        for action in menu.actions():
            if action.service.name() == default_action_name:
                break
        else:
            action = menu.actions()[0]
        self.openWithButton.setDefaultAction(action)

    def on_openWithButton_action_triggered(self, action):
        if action is None:
            return
        url_list = kdecore.KUrl.List([self.image_path])
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

    def setup_sendToButton(self):
        menu = QtGui.QMenu(self)
        menu.triggered.connect(self.on_sendToButton_action_triggered)
        services = [kdecore.KService('Dropbox', '', '')]
        for service in services:
            menu.addAction(KServiceAction(
                service, kdeui.KIcon(service.icon()), service.name().replace('&', '&&'), self))
        self.sendToButton.setMenu(menu)

        settings = QtCore.QSettings()
        default_action_name = settings.value(self.SEND_TO_DEFAULT_ACTION_SETTING_NAME)
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
            image_url = DropboxClient(self).upload_image(self.image_path)
        except Exception as exc:
            QtGui.QMessageBox.critical(
                self, 'Error', 'There was an error while trying to upload the image:\n%s' % exc)
            return
        clipboard = QtGui.QApplication.clipboard()
        clipboard.setText(image_url)
        msg_box = QtGui.QMessageBox(
            QtGui.QMessageBox.Information, 'The image was successfully uploaded',
            'Find the uploaded image here: <a href="%s">%s</a>\n'
            'The URL was also copied to the clipboard' % (image_url, image_url),
            QtGui.QMessageBox.Open | QtGui.QMessageBox.Close, self)
        msg_box.setTextFormat(QtCore.Qt.RichText)
        result = msg_box.exec()
        if result == QtGui.QMessageBox.Open:
            import webbrowser
            webbrowser.open(image_url)

    @QtCore.pyqtSlot()
    def on_copyButton_clicked(self):
        clipboard = QtGui.QApplication.clipboard()
        clipboard.setPixmap(self.imageLabel.pixmap())

    def _load_image(self):
        if self.image_path not in self.file_watcher.files():
            self.file_watcher.addPath(self.image_path)
        image = QtGui.QPixmap()
        image.load(self.image_path)
        self.imageLabel.setPixmap(image)

    def done(self, result):
        settings = QtCore.QSettings()
        settings.setValue(self.OPEN_WITH_DEFAULT_ACTION_SETTING_NAME,
                          self.openWithButton.defaultAction().service.name())
        settings.setValue(self.SEND_TO_DEFAULT_ACTION_SETTING_NAME,
                          self.sendToButton.defaultAction().service.name())
        return super().done(result)


class KServiceAction(QtGui.QAction):
    """Action with a related service.
    """
    def __init__(self, service, icon, text, parent):
        super().__init__(icon, text, parent)
        self.service = service
