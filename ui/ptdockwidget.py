# -*- coding: utf-8 -*-
#-----------------------------------------------------------
#
# Profile
# Copyright (C) 2012  Patrice Verchere
#-----------------------------------------------------------
#
# licensed under the terms of GNU GPL 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, print to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

#Qt import
from qgis.PyQt import uic, QtCore, QtGui
try:
    from qgis.PyQt.QtGui import QDockWidget
except:
    from qgis.PyQt.QtWidgets import QDockWidget

#qgis import
from qgis.core import *
from qgis.gui import *
#other
import platform
import os
#plugin import
from ..tools.plottingtool import *
from ..tools.tableviewtool import TableViewTool
from ..tools.utils import *
from ..cutCanvas import *
from ..dbtools.templatesDbReader import *
from ..dbtools.modelDbReader import *

try:
    from PyQt4.Qwt5 import *
    Qwt5_loaded = True
except ImportError:
    Qwt5_loaded = False

try:
    from matplotlib import *
    import matplotlib
    matplotlib_loaded = True
except ImportError:
    matplotlib_loaded = False



uiFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'profiletool.ui'))
FormClass = uic.loadUiType(uiFilePath)[0]

class PTDockWidget(QDockWidget, FormClass):

    TITLE = "Geology cut"
    TYPE = None

    closed = QtCore.pyqtSignal()


    def __init__(self, iface1, profiletoolcore, parent=None):
        QDockWidget.__init__(self, parent)
        self.setupUi(self)
        self.profiletoolcore = profiletoolcore
        self.iface = iface1
        #Apperance
        self.location = QtCore.Qt.BottomDockWidgetArea
        minsize = self.minimumSize()
        maxsize = self.maximumSize()
        self.setMinimumSize(minsize)
        self.setMaximumSize(maxsize)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        #init scale widgets
        # self.sbMaxVal.setValue(0)
        # self.sbMinVal.setValue(0)
        # self.sbMaxVal.setEnabled(False)
        # self.sbMinVal.setEnabled(False)
        # self.connectYSpinbox()
        #self.sbMinVal.valueChanged.connect(self.reScalePlot)
        #self.sbMaxVal.valueChanged.connect(self.reScalePlot)

        #model
        self.mdl = QStandardItemModel(0, COL_COUNT)         #the model whitch in are saved layers analysed caracteristics
        self.tableView.setModel(self.mdl)
        self.tableView.setColumnWidth(COL_VISIBLE, 20)
        self.tableView.setColumnWidth(COL_COLOR, 20)
        #self.tableView.setColumnWidth(2, 150)
        hh = self.tableView.horizontalHeader()
        hh.setStretchLastSection(True)
        self.tableView.setColumnHidden(COL_LAYER , True)
        self.mdl.setHorizontalHeaderLabels(["","",self.tr("Layer"), self.tr("Band/Field"), self.tr("Search buffer")])
        self.tableViewTool = TableViewTool()

        #other
        self.addOptionComboboxItems()
        self.selectionmethod = 0
        self.plotlibrary = None                            #The plotting library to use
        self.showcursor = True
        self.plotCanvas = None
        self.currentProjectName = None

        #Временно
        self.cbxSaveAs.setVisible(False)
        self.butSaveAs.setVisible(False)
        self.profileInterpolationCheckBox.setVisible(False)
        self.groupBox_3.setVisible(False)
        self.groupBox_2.setVisible(False)

        #Signals
        self.butSaveAs.clicked.connect(self.saveAs)
        self.tableView.clicked.connect(self._onClick)
        self.mdl.itemChanged.connect(self._onChange)
        self.pushButton_2.clicked.connect(self.addLayer)
        self.pushButton.clicked.connect(self.removeLayer)
        self.comboBox.currentIndexChanged.connect(self.selectionMethod)
        self.cboLibrary.currentIndexChanged.connect(self.changePlotLibrary)
        self.tableViewTool.layerAddedOrRemoved.connect(self.refreshPlot)
        self.pushButton_reinitview.clicked.connect(self.reScalePlot)

        self.checkBox_showcursor.stateChanged.connect(self.showCursor)

        self.fullResolutionCheckBox.stateChanged.connect(self.refreshPlot)
        self.profileInterpolationCheckBox.stateChanged.connect(self.refreshPlot)

        self.fillTemplateList()
        self.fillModelList()

        # self.wellLayerComboBox = QgsMapLayerComboBox(self.groupBox)
        # self.wellLayerComboBox.setFilters(QgsMapLayerProxyModel.Filters(8)) #Line layers only
        # self.parameterGridLayout.addWidget(self.wellLayerComboBox, 2, 1)

    #********************************************************************************
    #init things ****************************************************************
    #********************************************************************************

    def isProjectChanged(self):
        project = QtCore.QSettings().value('currentProject')
        if project:
            return self.currentProjectName != project['project']
        else:
            return False

    def fillTemplateList(self):
        dbReader = TemplatesDbReader(self.iface, self)
        templates = dbReader.readTemplates()

        project = QtCore.QSettings().value('currentProject')
        if project:
            self.currentProjectName = project['project']

        self.wellTemplates.clear()
        self.wellTemplates.addItem(u'Не выбрано', -1)

        for t in templates:
            self.wellTemplates.addItem(t['description'], t['sldnid'])

    def fillModelList(self):
        dbReader = ModelDbReader(self.iface, self)
        modelList = dbReader.readModelList()
        self.mModelListWidget.clear()
        for model in modelList:
            item = QtGui.QListWidgetItem(model[1])
            item.setData(Qt.UserRole, model[0])
            self.mModelListWidget.addItem(item)

    def addOptionComboboxItems(self):
        self.cboLibrary.addItem("PyQtGraph")
        if matplotlib_loaded:
            self.cboLibrary.addItem("Matplotlib")
        if Qwt5_loaded:
            self.cboLibrary.addItem("Qwt5")

    def selectionMethod(self,item):

        self.profiletoolcore.toolrenderer.setSelectionMethod(item)

        if self.iface.mapCanvas().mapTool() == self.profiletoolcore.toolrenderer.tool:
            self.iface.mapCanvas().setMapTool(self.profiletoolcore.toolrenderer.tool)
            self.profiletoolcore.toolrenderer.connectTool()

    def changePlotLibrary(self, item):
        self.plotlibrary = self.cboLibrary.itemText(item)
        self.addPlotWidget(self.plotlibrary)

        if self.plotlibrary == 'PyQtGraph':
            self.checkBox_mpl_tracking.setEnabled(True)
            self.checkBox_showcursor.setEnabled(True)
            self.checkBox_mpl_tracking.setCheckState(2)
            self.profiletoolcore.activateMouseTracking(2)
            self.checkBox_mpl_tracking.stateChanged.connect(self.profiletoolcore.activateMouseTracking)


        elif self.plotlibrary == 'Matplotlib':
            self.checkBox_mpl_tracking.setEnabled(True)
            self.checkBox_showcursor.setEnabled(False)
            self.checkBox_mpl_tracking.setCheckState(2)
            self.profiletoolcore.activateMouseTracking(2)
            self.checkBox_mpl_tracking.stateChanged.connect(self.profiletoolcore.activateMouseTracking)

        else:
            self.checkBox_mpl_tracking.setCheckState(0)
            self.checkBox_mpl_tracking.setEnabled(False)



    def addPlotWidget(self, library):
        layout = self.frame_for_plot.layout()

        # while layout.count():
        #                 child = layout.takeAt(0)
        #                 child.widget().deleteLater()

        if not self.plotCanvas:
            self.plotCanvas = MirrorMap(self.frame_for_plot, self.iface)
            layout.addWidget(self.plotCanvas)

        if library == "PyQtGraph":
            self.stackedWidget.setCurrentIndex(0)
            self.plotWdg = PlottingTool().changePlotWidget("PyQtGraph", self.frame_for_plot)
            # layout.addWidget(self.plotWdg)
            self.TYPE = "PyQtGraph"
            self.cbxSaveAs.clear()
            self.cbxSaveAs.addItems(['Graph - PNG','Graph - SVG','3D line - DXF'])

        elif library == "Qwt5":
            self.stackedWidget.setCurrentIndex(0)
            widget1 = self.stackedWidget.widget(1)
            if widget1:
                self.stackedWidget.removeWidget( widget1 )
                widget1 = None
            self.widget_save_buttons.setVisible( True )
            self.plotWdg = PlottingTool().changePlotWidget("Qwt5", self.frame_for_plot)
            # layout.addWidget(self.plotWdg)

            if QT_VERSION < 0X040100:
                idx = self.cbxSaveAs.model().index(0, 0)
                self.cbxSaveAs.model().setData(idx, QVariant(0), QtCore.Qt.UserRole - 1)
                self.cbxSaveAs.setCurrentIndex(1)
            if QT_VERSION < 0X040300:
                idx = self.cbxSaveAs.model().index(1, 0)
                self.cbxSaveAs.model().setData(idx, QVariant(0), QtCore.Qt.UserRole - 1)
                self.cbxSaveAs.setCurrentIndex(2)
            self.TYPE = "Qwt5"

        elif library == "Matplotlib":
            self.stackedWidget.setCurrentIndex(0)
            #self.widget_save_buttons.setVisible( False )
            self.plotWdg = PlottingTool().changePlotWidget("Matplotlib", self.frame_for_plot)
            # layout.addWidget(self.plotWdg)

            if int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 4 :
                #from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
                mpltoolbar = matplotlib.backends.backend_qt4agg.NavigationToolbar2QTAgg(self.plotWdg, self.frame_for_plot)
                #layout.addWidget( mpltoolbar )
                self.stackedWidget.insertWidget(1, mpltoolbar)
                self.stackedWidget.setCurrentIndex(1)
                lstActions = mpltoolbar.actions()
                mpltoolbar.removeAction( lstActions[ 7 ] )
                mpltoolbar.removeAction( lstActions[ 8 ] )

            elif int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 5 :
                #from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
                #mpltoolbar = matplotlib.backends.backend_qt5agg.NavigationToolbar2QTAgg(self.plotWdg, self.frame_for_plot)
                pass
            self.TYPE = "Matplotlib"
            self.cbxSaveAs.clear()
            self.cbxSaveAs.addItems(['Graph - PDF','Graph - PNG','Graph - SVG','Graph - print (PS)','3D line - DXF'])

    # ********************************************************************************
    # properties ****************************************************************
    # ********************************************************************************

    @property
    def showWells(self):
        return self.mShowWells.isChecked()

    @property
    def distanceToWell(self):
        return float(self.mWellDistance.value())

    @property
    def xyAspect(self):
        return self.mXyAspectRatio.value()

    @property
    def wellTopDepth(self):
        return self.wellTopDepthEdit.value()

    @property
    def wellBottomDepth(self):
        return self.wellBottomDepthEdit.value()

    @property
    def currentTemplateId(self):
        return self.wellTemplates.itemData(self.wellTemplates.currentIndex())

    @currentTemplateId.setter
    def currentTemplateId(self, newId):
        index = self.wellTemplates.findData(newId)
        if index >= 0:
            self.wellTemplates.setCurrentIndex(index)

    @property
    def isDefaultTrackWidth(self):
        return self.defaultTrackWidth.isChecked()

    @isDefaultTrackWidth.setter
    def isDefaultTrackWidth(self, val):
        self.defaultTrackWidth.setChecked(val)

    @property
    def trackWidth(self):
        return self.trackWidthSpinBox.value()

    @trackWidth.setter
    def trackWidth(self, newWidth):
        self.trackWidthSpinBox.setValue(newWidth)

    @property
    def showModel(self):
        return self.mShowModel.isChecked()

    @property
    def currentModelNumber(self):
        if self.mModelListWidget.currentItem() is not None:
            return self.mModelListWidget.currentItem().data(Qt.UserRole)
        return -1


    #********************************************************************************
    #graph things ****************************************************************
    #********************************************************************************


    # def connectYSpinbox(self):
    #     self.sbMinVal.valueChanged.connect(self.reScalePlot)
    #     self.sbMaxVal.valueChanged.connect(self.reScalePlot)
    #
    # def disconnectYSpinbox(self):
    #     try:
    #         self.sbMinVal.valueChanged.disconnect(self.reScalePlot)
    #         self.sbMaxVal.valueChanged.disconnect(self.reScalePlot)
    #     except:
    #         pass

    def connectPlotRangechanged(self):
        self.plotWdg.getViewBox().sigRangeChanged.connect(self.plotRangechanged)

    def disconnectPlotRangechanged(self):
        try:
            self.plotWdg.getViewBox().sigRangeChanged.disconnect(self.plotRangechanged)
        except:
            pass

    def plotRangechanged(self, param = None):                         # called when pyqtgraph view changed
        PlottingTool().plotRangechanged(self,  self.cboLibrary.currentText () )


    def reScalePlot(self, param):                         # called when a spinbox value changed
        self.on_mApplyPushButton_clicked()
        # if type(param) == bool: #comes from button
        #     PlottingTool().reScalePlot(self, self.profiletoolcore.profiles, self.cboLibrary.currentText () , True)
        #     self.plotCanvas._updateExtent()
        #
        # else:   #spinboxchanged
        #
        #     if self.sbMinVal.value() == self.sbMaxVal.value() == 0:
        #         # don't execute it on init
        #         pass
        #     else:
        #         #print('rescale',self.sbMinVal.value(),self.sbMaxVal.value())
        #         PlottingTool().reScalePlot(self, self.profiletoolcore.profiles, self.cboLibrary.currentText () )

    # @pyqtSlot(float)
    def on_mXyAspectRatio_editingFinished(self):
        if not self.profiletoolcore.finishing:
            self.refreshPlot()
            self.profiletoolcore.updateWells()
            self.plotCanvas._updateExtent()

    @pyqtSlot(bool)
    def on_mShowWells_toggled(self, val):
        if val:
            self.profiletoolcore.updateWells()
        else:
            self.plotCanvas.delLayerByName(PlottingTool.WellsLayerName)

    # @pyqtSlot(int)
    # def on_wellTemplates_activated(self, index):
    #     sldnid = self.wellTemplates.itemData(index)
    #     self.profiletoolcore.redrawLogs(sldnid)
    #
    # def on_wellTopDepthEdit_editingFinished(self):
    #     if not self.profiletoolcore.finishing:
    #         self.profiletoolcore.updateWells()
    #
    # def on_wellBottomDepthEdit_editingFinished(self):
    #     if not self.profiletoolcore.finishing:
    #         self.profiletoolcore.updateWells()
    #
    # def on_trackWidthSpinBox_editingFinished(self):
    #     if not self.profiletoolcore.finishing:
    #         self.profiletoolcore.redrawLogs(self.currentTemplateId)
    #
    # def on_defaultTrackWidth_toggled(self, val):
    #     if not self.profiletoolcore.finishing:
    #         self.profiletoolcore.redrawLogs(self.currentTemplateId)

    def on_mApplyPushButton_clicked(self):
        if not self.profiletoolcore.finishing:
            if self.isProjectChanged():
                self.fillTemplateList()
            self.refreshPlot()
            self.profiletoolcore.updateWells()


    def blockAllSignals(self, val):
        self.plotComboBox.blockSignals(val)
        self.mXyAspectRatio.blockSignals(val)
        self.comboBox.blockSignals(val)
        self.mWellDistance.blockSignals(val)
        self.wellTopDepthEdit.blockSignals(val)
        self.wellBottomDepthEdit.blockSignals(val)
        self.wellTemplates.blockSignals(val)
        self.defaultTrackWidth.blockSignals(val)
        self.trackWidthSpinBox.blockSignals(val)

    def invertY(self, isInvert):
        if self.plotlibrary == 'PyQtGraph':
            self.plotWdg.getViewBox().invertY(isInvert)

    def showCursor(self,int1):
        #For pyqtgraph mode
        if self.plotlibrary == 'PyQtGraph':
            if int1 == 2 :
                self.showcursor = True
                self.profiletoolcore.doTracking = bool(self.checkBox_mpl_tracking.checkState() )
                self.checkBox_mpl_tracking.setEnabled(True)
                for item in self.plotWdg.allChildItems():
                    if str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.InfiniteLine.InfiniteLine'>":
                        if item.name() == 'cross_vertical':
                            item.show()
                        elif item.name() == 'cross_horizontal':
                            item.show()
                    elif str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.TextItem.TextItem'>":
                        if item.textItem.toPlainText()[0] == 'X':
                            item.show()
                        elif item.textItem.toPlainText()[0] == 'Y':
                            item.show()
            elif int1 == 0 :
                self.showcursor = False
                self.profiletoolcore.doTracking = False
                self.checkBox_mpl_tracking.setEnabled(False)


                for item in self.plotWdg.allChildItems():
                    if str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.InfiniteLine.InfiniteLine'>":
                        if item.name() == 'cross_vertical':
                            item.hide()
                        elif item.name() == 'cross_horizontal':
                            item.hide()
                    elif str(type(item)) == "<class 'profiletool.pyqtgraph.graphicsItems.TextItem.TextItem'>":
                        if item.textItem.toPlainText()[0] == 'X':
                            item.hide()
                        elif item.textItem.toPlainText()[0] == 'Y':
                            item.hide()
            self.profiletoolcore.plotProfil()

    #********************************************************************************
    #tablebiew things ****************************************************************
    #********************************************************************************

    def addLayer(self, layer1 = None):

        if isinstance(layer1,bool): #comes from click
            layer1 = self.iface.activeLayer()
        """
        if layer1 is None:
            layer1 = self.iface.activeLayer()
        """
        self.tableViewTool.addLayer(self.iface, self.mdl, layer1)
        self.profiletoolcore.updateProfil(self.profiletoolcore.pointstoDraw, False)
        layer1.dataChanged.connect(self.refreshPlot)


    def removeLayer(self, index=None):
        #if index is None:
        if isinstance(index,bool):  #come from button
            index = self.tableViewTool.chooseLayerForRemoval(self.iface, self.mdl)

        if index is not None:
            layer = self.mdl.index(index, COL_LAYER).data()

            try:
                layer.dataChanged.disconnect(self.refreshPlot)
            except:
                pass
            self.tableViewTool.removeLayer(self.mdl, index)
        self.profiletoolcore.updateProfil(self.profiletoolcore.pointstoDraw,
                                          False, True)

    def refreshPlot(self):
        self.profiletoolcore.updateProfil(self.profiletoolcore.pointstoDraw, False, True)


    def _onClick(self,index1):                    #action when clicking the tableview
        self.tableViewTool.onClick(self.iface, self, self.mdl, self.plotlibrary, index1)
        self.iface.mapCanvas().refreshAllLayers()
        self.plotCanvas.canvas.refreshAllLayers()

    def _onChange(self,item):
        if (not self.mdl.item(item.row(), COL_LAYER) is None
                and item.column() == 4
                and self.mdl.item(item.row(), COL_LAYER).data(QtCore.Qt.EditRole).type() == qgis.core.QgsMapLayer.VectorLayer):

            self.profiletoolcore.plotProfil()



    #********************************************************************************
    #coordinate tab ****************************************************************
    #********************************************************************************

    def updateCoordinateTab(self):
        try:                                                                    #Reinitializing the table tab
            self.VLayout = self.scrollAreaWidgetContents.layout()
            while 1:
                child = self.VLayout.takeAt(0)
                if not child:
                    break
                child.widget().deleteLater()
        except:
            self.VLayout = QVBoxLayout(self.scrollAreaWidgetContents)
            self.VLayout.setContentsMargins(9, -1, -1, -1)
        #Setup the table tab
        self.groupBox = []
        self.profilePushButton = []
        self.coordsPushButton = []
        self.tolayerPushButton = []
        self.tableView = []
        self.verticalLayout = []
        if self.mdl.rowCount() != self.profiletoolcore.profiles:
            # keep the number of profiles and the model in sync.
            self.profiletoolcore.updateProfil(
                self.profiletoolcore.pointstoDraw, False, False)
        for i in range(0 , self.mdl.rowCount()):
            self.groupBox.append( QGroupBox(self.scrollAreaWidgetContents) )
            sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.groupBox[i].sizePolicy().hasHeightForWidth())
            self.groupBox[i].setSizePolicy(sizePolicy)
            self.groupBox[i].setMinimumSize(QSize(0, 150))
            self.groupBox[i].setMaximumSize(QSize(16777215, 150))
            try:    #qgis2
                self.groupBox[i].setTitle(QApplication.translate("GroupBox" + str(i), self.profiletoolcore.profiles[i]["layer"].name(), None, QApplication.UnicodeUTF8))
            except: #qgis3
                self.groupBox[i].setTitle(QApplication.translate("GroupBox" + str(i), self.profiletoolcore.profiles[i]["layer"].name(), None))
            self.groupBox[i].setObjectName("groupBox" + str(i))

            self.verticalLayout.append( QVBoxLayout(self.groupBox[i]) )
            self.verticalLayout[i].setObjectName("verticalLayout")
            #The table
            self.tableView.append( QTableView(self.groupBox[i]) )
            self.tableView[i].setObjectName("tableView" + str(i))
            font = QFont("Arial", 8)
            column = len(self.profiletoolcore.profiles[i]["l"])

            self.mdl2 = QStandardItemModel(2, column)
            for j in range(len(self.profiletoolcore.profiles[i]["l"])):
                self.mdl2.setData(self.mdl2.index(0, j, QModelIndex())  ,self.profiletoolcore.profiles[i]["l"][j])
                self.mdl2.setData(self.mdl2.index(0, j, QModelIndex())  ,font ,QtCore.Qt.FontRole)
                self.mdl2.setData(self.mdl2.index(1, j, QModelIndex())  ,self.profiletoolcore.profiles[i]["z"][j])
                self.mdl2.setData(self.mdl2.index(1, j, QModelIndex())  ,font ,QtCore.Qt.FontRole)
            self.tableView[i].verticalHeader().setDefaultSectionSize(18)
            self.tableView[i].horizontalHeader().setDefaultSectionSize(60)
            self.tableView[i].setModel(self.mdl2)
            self.verticalLayout[i].addWidget(self.tableView[i])

            self.horizontalLayout = QHBoxLayout()

            #the copy to clipboard button
            self.profilePushButton.append( QPushButton(self.groupBox[i]) )
            sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.profilePushButton[i].sizePolicy().hasHeightForWidth())
            self.profilePushButton[i].setSizePolicy(sizePolicy)
            try:    #qgis2
                self.profilePushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard", None, QApplication.UnicodeUTF8))
            except: #qgis3
                self.profilePushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard", None))
            self.profilePushButton[i].setObjectName(str(i))
            self.horizontalLayout.addWidget(self.profilePushButton[i])

            #button to copy to clipboard with coordinates
            self.coordsPushButton.append(QPushButton(self.groupBox[i]))
            sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.coordsPushButton[i].sizePolicy().hasHeightForWidth())
            self.coordsPushButton[i].setSizePolicy(sizePolicy)
            try:    #qgis2
                self.coordsPushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard (with coordinates)", None, QApplication.UnicodeUTF8))
            except: #qgis3
                self.coordsPushButton[i].setText(QApplication.translate("GroupBox", "Copy to clipboard (with coordinates)", None))

            #button to copy to clipboard with coordinates
            self.tolayerPushButton.append(QPushButton(self.groupBox[i]))
            sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(self.tolayerPushButton[i].sizePolicy().hasHeightForWidth())
            self.tolayerPushButton[i].setSizePolicy(sizePolicy)
            try:    #qgis2
                self.tolayerPushButton[i].setText(QApplication.translate("GroupBox", "Create Temporary layer", None, QApplication.UnicodeUTF8))
            except: #qgis3
                self.tolayerPushButton[i].setText(QApplication.translate("GroupBox", "Create Temporary layer", None))



            self.coordsPushButton[i].setObjectName(str(i))
            self.horizontalLayout.addWidget(self.coordsPushButton[i])

            self.tolayerPushButton[i].setObjectName(str(i))
            self.horizontalLayout.addWidget(self.tolayerPushButton[i])

            self.horizontalLayout.addStretch(0)
            self.verticalLayout[i].addLayout(self.horizontalLayout)

            self.VLayout.addWidget(self.groupBox[i])

            self.profilePushButton[i].clicked.connect(self.copyTable)
            self.coordsPushButton[i].clicked.connect(self.copyTableAndCoords)
            self.tolayerPushButton[i].clicked.connect(self.createTemporaryLayer)



    def copyTable(self):                            #Writing the table to clipboard in excel form
        nr = int( self.sender().objectName() )
        self.clipboard = QApplication.clipboard()
        text = ""
        for i in range( len(self.profiletoolcore.profiles[nr]["l"]) ):
            text += str(self.profiletoolcore.profiles[nr]["l"][i]) + "\t" + str(self.profiletoolcore.profiles[nr]["z"][i]) + "\n"
        self.clipboard.setText(text)

    def copyTableAndCoords(self):                    #Writing the table with coordinates to clipboard in excel form
        nr = int( self.sender().objectName() )
        self.clipboard = QApplication.clipboard()
        text = ""
        for i in range( len(self.profiletoolcore.profiles[nr]["l"]) ):
            text += str(self.profiletoolcore.profiles[nr]["l"][i]) + "\t" + str(self.profiletoolcore.profiles[nr]["x"][i]) + "\t"\
                 + str(self.profiletoolcore.profiles[nr]["y"][i]) + "\t" + str(self.profiletoolcore.profiles[nr]["z"][i]) + "\n"
        self.clipboard.setText(text)


    def createTemporaryLayer(self):
        nr = int( self.sender().objectName() )
        type = "Point?crs="+str(self.profiletoolcore.profiles[nr]["layer"].crs().authid())
        name = 'ProfileTool_'+str(self.profiletoolcore.profiles[nr]['layer'].name())
        vl = QgsVectorLayer(type, name, "memory")
        pr = vl.dataProvider()
        vl.startEditing()
        # add fields
        #pr.addAttributes([QgsField("PointID", QVariant.Int)])
        pr.addAttributes([QgsField("Value", QVariant.Double) ])
        vl.updateFields()
        #Add features to layer
        for i in range( len(self.profiletoolcore.profiles[nr]["l"]) ):

            fet = QgsFeature(vl.fields())
            #set geometry
            fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(self.profiletoolcore.profiles[nr]['x'][i],self.profiletoolcore.profiles[nr]['y'][i])))
            #set attributes
            fet.setAttributes( [self.profiletoolcore.profiles[nr]["z"][i]] )
            pr.addFeatures([fet])
        vl.commitChanges()
        #labeling/enabled
        if False:
            labelsettings = vl.labeling().settings()
            labelsettings.enabled = True

        #vl.setCustomProperty("labeling/enabled", "true")
        #show layer
        try:    #qgis2
            qgis.core.QgsMapLayerRegistry.instance().addMapLayer(vl)
        except:     #qgis3
            qgis.core.QgsProject.instance().addMapLayer(vl)



    #********************************************************************************
    #other things ****************************************************************
    #********************************************************************************

    def closeEvent(self, event):
        self.closed.emit()
        #self.butSaveAs.clicked.disconnect(self.saveAs)
        #return QDockWidget.closeEvent(self, event)


    # generic save as button
    def saveAs(self):

        idx = self.cbxSaveAs.currentText()
        if idx == 'Graph - PDF':
                self.outPDF()
        elif idx == 'Graph - PNG':
                self.outPNG()
        elif idx == 'Graph - SVG':
                self.outSVG()
        elif idx == 'Graph - print (PS)':
                self.outPrint()
        elif idx == '3D line - DXF':
                self.outDXF()
        else:
            print('plottingtool: invalid index '+str(idx))

    def outPrint(self): # Postscript file rendering doesn't work properly yet.
        PlottingTool().outPrint(self.iface, self, self.mdl, self.cboLibrary.currentText ())

    def outPDF(self):
        PlottingTool().outPDF(self.iface, self, self.mdl, self.cboLibrary.currentText ())

    def outSVG(self):
        PlottingTool().outSVG(self.iface, self, self.mdl, self.cboLibrary.currentText ())

    def outPNG(self):
        PlottingTool().outPNG(self.iface, self, self.mdl, self.cboLibrary.currentText ())

    def outDXF(self):
        PlottingTool().outDXF(self.iface, self, self.mdl, self.cboLibrary.currentText (), self.profiletoolcore.profiles)
