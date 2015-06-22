__author__ = "Victor Varvariuc <victor.varvariuc@gmail.com>"

import os

from PyQt4 import QtGui, QtCore

import dropbox

from viewshow import utils


FormClass = utils.load_form('dropbox-config.ui', QtGui.QDialog)


class DropboxConfigDialog(FormClass):

    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)
        self.client = None

    def on_appKeyEdit_textChanged(self):
        self._make_authorization_url()

    def on_appSecretEdit_textChanged(self):
        self._make_authorization_url()

    def _make_flow(self):
        app_key = self.appKeyEdit.text().strip()
        app_secret = self.appSecretEdit.text().strip()
        if not app_key:
            return None
        flow = dropbox.client.DropboxOAuth2FlowNoRedirect(app_key, app_secret)
        return flow

    def _make_authorization_url(self):
        flow = self._make_flow()
        if not flow:
            return
        authorize_url = flow.start()
        self.authorizationURLEdit.setText(authorize_url)

    @QtCore.pyqtSlot()
    def on_openButton_clicked(self):
        import webbrowser
        webbrowser.open(self.authorizationURLEdit.text())

    @QtCore.pyqtSlot()
    def on_getTokenButton_clicked(self):
        flow = self._make_flow()
        if not flow:
            QtGui.QMessageBox.warning(self, 'Empty field', 'Please app key and secret')
            return
        authorization_code = self.authorizationCodeEdit.text().strip()
        if not authorization_code:
            QtGui.QMessageBox.warning(self, 'Empty field', 'Please enter authorization code')
            return
        try:
            access_token, user_id = flow.finish(authorization_code)
        except Exception as exc:
            QtGui.QMessageBox.critical(self, 'Error', 'Could not get access token:\n%s' % exc)
            return
        self.accessTokenEdit.setText(access_token)

    def done(self, result):
        if result == QtGui.QDialog.Accepted:  # OK was pressed
            access_token = self.accessTokenEdit.text().strip()
            if not access_token:
                QtGui.QMessageBox.critical(self, 'Empty field', 'Please enter access code')
                return
            try:
                self.client = dropbox.client.DropboxClient(access_token)
            except Exception as exc:
                QtGui.QMessageBox.critical(self, 'Bad access token', str(exc))
                return
        return super().done(result)


class DropboxClient():
    """
    """
    class Error(Exception):
        pass

    def __init__(self, parent_widget):
        self.parent_widget = parent_widget
        settings = QtCore.QSettings()
        access_token = settings.value('dropbox/access_token')
        if not access_token:
            self._update_access_token()
        else:
            self._make_client(access_token)

    def upload_image(self, file_path):
        file = open(file_path, 'rb')
        file_name = os.path.split(file_path)[1]
        file_path = self._client_call('put_file', file_name, file, overwrite=True)['path']
        # https://www.dropbox.com/developers/core/docs/python#DropboxClient.share
        response = self._client_call('share', file_path, short_url=False)
        return response['url']

    def _make_client(self, access_token):
        try:
            self.client = dropbox.client.DropboxClient(access_token)
        except Exception as exc:
            raise self.Error(*exc.args)

    def _client_call(self, method_name, *args, **kwargs):
        while True:
            method = getattr(self.client, method_name)
            try:
                return method(*args, **kwargs)
            except dropbox.client.ErrorResponse as exc:
                if exc.status == 401:
                    # looks like the token is invalid
                    self._update_access_token()
            except Exception as exc:
                if isinstance(exc, dropbox.client.ErrorResponse) and exc.status == 401:
                    # looks like the token is invalid
                    self._update_access_token()
                    continue
                raise self.Error(str(exc))

    def _update_access_token(self):
        config_dialog = DropboxConfigDialog(self.parent_widget)
        result = config_dialog.exec()
        if result != QtGui.QDialog.Accepted:  # OK was not pressed
            raise self.Error('Access token was not provided by the user')
        self.client = config_dialog.client
        access_token = self.client.session.access_token

        settings = QtCore.QSettings()
        settings.setValue('dropbox/access_token', access_token)
