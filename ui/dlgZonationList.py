# -*- coding: utf-8 -*-

# Qt import
from qgis.PyQt import uic, QtCore, QtGui

try:
    from qgis.PyQt.QtGui import *
except:
    from qgis.PyQt.QtWidgets import *
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'dlgZonationList.ui'))
class DlgZonationList(QtGui.QDialog, FORM_CLASS):
    def __init__(self, zonations, _title, parent=None):
        super(DlgZonationList, self).__init__(parent)
        self.setupUi(self)

        self.setWindowTitle(_title)

        for z in zonations:
            item = QtGui.QListWidgetItem(z[1], self.listWidget)
            item.setData(QtCore.Qt.UserRole, z[0])
            self.listWidget.addItem(item)

    def selectedZonations(self):
        result = []
        items = self.listWidget.selectedItems()
        for item in items:
            result.append(item.data(QtCore.Qt.UserRole))

        return result