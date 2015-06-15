__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

from PyQt4 import QtCore, QtGui
from PyKDE4 import kdecore, kdeui, kio

from viewshow import utils


FormClass = utils.load_form('screenshot.ui', QtGui.QDialog)


class ScreenshotDialog(FormClass):

    def __init__(self, parent_widget, image_path):
        super().__init__(parent_widget)
        self.setupUi(self)

        self.image_path = image_path
        self.file_watcher = QtCore.QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self._load_image)
        self._load_image()

        self.setup_openWithButton()
        self.sendToButton.setText('Upload to Dropbox')

        self.sendToButton.clicked.connect(
            lambda: QtGui.QMessageBox.information(self, '', 'Send to'))

    def setup_openWithButton(self):
        menu = QtGui.QMenu(self)
        menu.triggered.connect(self.on_openWithButton_menu_triggered)
        services = kdecore.KMimeTypeTrader.self().query('image/png')
        for service in services:
            menu.addAction(QServiceAction(
                service, kdeui.KIcon(service.icon()), service.name().replace('&', '&&'), self))
        menu.addSeparator()
        menu.addAction(QServiceAction(
            None, kdeui.KIcon(), kdecore.i18n('Other Application...'), self))
        self.openWithButton.setMenu(menu)

        settings = QtCore.QSettings()
        default_action_name = settings.value('screenshot/open-with-default-action')
        for action in menu.actions():
            if action.service.name() == default_action_name:
                break
        else:
            action = menu.actions()[0]
        self.openWithButton.setDefaultAction(action)

    def on_openWithButton_menu_triggered(self, action):
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
        settings.setValue('screenshot/open-with-default-action',
                          self.openWithButton.defaultAction().service.name())
        return super().done(result)


class QServiceAction(QtGui.QAction):
    def __init__(self, service, icon, text, parent):
        super().__init__(icon, text, parent)
        self.service = service
