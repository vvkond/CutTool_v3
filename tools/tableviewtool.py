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
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
# 
#---------------------------------------------------------------------
#Qt import
from qgis.PyQt import uic, QtCore, QtGui, QtXml
try:
    from qgis.PyQt.QtGui import *
except:
    from qgis.PyQt.QtWidgets import *
#qgis import
from qgis.core import *
from qgis.gui import *
#plugin import
from .plottingtool import *
from .utils import isProfilable


class TableViewTool(QtCore.QObject):
    
    layerAddedOrRemoved = QtCore.pyqtSignal() # Emitted when a new layer is added

    def addLayer(self , iface, mdl, layer1 = None):
        if layer1 == None:
            templist=[]
            j=0
            # Ask the layer by a input dialog 
            for i in range(0, iface.mapCanvas().layerCount()):
                donothing = False
                layer = iface.mapCanvas().layer(i)
                if isProfilable(layer):
                    for j in range(0, mdl.rowCount()):
                        if str(mdl.item(j,COL_NAME).data(QtCore.Qt.EditRole)) == str(layer.name()):
                            donothing = True
                else:
                    donothing = True
                    
                if donothing == False:
                    templist +=  [[layer, layer.name()]]
                        
            if len(templist) == 0:
                QMessageBox.warning(iface.mainWindow(), self.tr("Geology cut"), self.tr("No raster to add"))
                return
            else:    
                testqt, ok = QInputDialog.getItem(iface.mainWindow(), self.tr("Layer selector"), self.tr("Choose layer"),
                                                  [templist[k][1] for k in range( len(templist) )], False)
                if ok:
                    for i in range (0,len(templist)):
                        if templist[i][1] == testqt:
                            layer2 = templist[i][0]
                else:
                    return
        else : 
            if isProfilable(layer1):
                layer2 = layer1
            else:
                QMessageBox.warning(iface.mainWindow(), self.tr("Geology cut"), self.tr("Active layer is not a profilable layer"))
                return

        # Ask the Band by a input dialog
        #First, if isProfilable, considerate the real band number (instead of band + 1 for raster)
        if layer2.type() == layer2.PluginLayer and  isProfilable(layer2):
            self.bandoffset = 0
            typename = 'parameter'
        elif layer2.type() == layer2.RasterLayer:
            self.bandoffset = 1
            typename = 'band'
        elif layer2.type() == layer2.VectorLayer:
            self.bandoffset = 0
            typename = 'field'

            
        if layer2.type() == layer2.RasterLayer and layer2.bandCount() != 1:
            listband = []
            for i in range(0,layer2.bandCount()):
                listband.append(str(i+self.bandoffset))
            testqt, ok = QInputDialog.getItem(iface.mainWindow(), typename + " selector", "Choose the " + typename, listband, False)
            if ok :
                choosenBand = int(testqt) - self.bandoffset
            else:
                return 2
        elif layer2.type() == layer2.VectorLayer :
            fieldstemp = [field.name() for field in layer2.fields() ]
            if int(QtCore.QT_VERSION_STR[0]) == 4 :    #qgis2
                fields = [field.name() for field in layer2.fields() if field.type() in [2,3,4,5,6]]
            
            elif int(QtCore.QT_VERSION_STR[0]) == 5 :    #qgis3
                fields = [field.name() for field in layer2.fields() if field.isNumeric()]
            if len(fields)==0:
                QMessageBox.warning(iface.mainWindow(), self.tr("Geology cut"), self.tr("Active layer is not a profilable layer"))
                return
            elif len(fields) == 1 :
                choosenBand = fieldstemp.index(fields[0])
                
            else:
                testqt, ok = QInputDialog.getItem(iface.mainWindow(), typename + " selector", "Choose the " + typename, fields, False)
                if ok :
                    choosenBand = fieldstemp.index(testqt)
                else:
                    return 2
            
        else:
            choosenBand = 0

        #Complete the tableview
        row = mdl.rowCount()
        mdl.insertRow(row)
        mdl.setData( mdl.index(row, COL_VISIBLE, QModelIndex())  ,True, QtCore.Qt.CheckStateRole)
        mdl.item(row, COL_VISIBLE).setFlags(QtCore.Qt.ItemIsSelectable)
        lineColour = QtCore.Qt.red
        fillColor = QtCore.Qt.green
        if row < 1:
            fillColor = QtCore.Qt.white
        if layer2.type() == layer2.PluginLayer and layer2.LAYER_TYPE == 'crayfish_viewer':
            lineColour = QtCore.Qt.blue
        mdl.setData( mdl.index(row, COL_COLOR, QModelIndex())  ,QColor(lineColour) , QtCore.Qt.BackgroundRole)
        mdl.item(row, COL_COLOR).setFlags(QtCore.Qt.NoItemFlags)

        symbol = QgsFillSymbolV2.createSimple({'color': '#0000FF',
                                               'style': 'solid',
                                               'style_border': 'solid',
                                               'color_border': 'black',
                                               'width_border': '0.3'})
        icon = QgsSymbolLayerV2Utils.symbolPreviewIcon(symbol, QSize(50, 50))
        mdl.setData(mdl.index(row, COL_BACKGROUND, QModelIndex()), symbol, QtCore.Qt.UserRole)
        mdl.setData(mdl.index(row, COL_BACKGROUND, QModelIndex()), icon, QtCore.Qt.DecorationRole)
        mdl.item(row, COL_BACKGROUND).setFlags(QtCore.Qt.NoItemFlags)

        mdl.setData( mdl.index(row, COL_NAME, QModelIndex())  ,layer2.name())
        mdl.item(row, COL_NAME).setFlags(QtCore.Qt.ItemIsEnabled)

        mdl.setData( mdl.index(row, COL_BAND, QModelIndex())  ,choosenBand + self.bandoffset)
        mdl.item(row, COL_BAND).setFlags(QtCore.Qt.NoItemFlags)

        if layer2.type() == layer2.VectorLayer :
            mdl.setData( mdl.index(row, COL_BUFFER, QModelIndex()), 100.0)
        else:
            mdl.setData( mdl.index(row, COL_BUFFER, QModelIndex())  ,'')
            mdl.item(row, COL_BUFFER).setFlags(QtCore.Qt.NoItemFlags)
            
            
        mdl.setData( mdl.index(row, COL_LAYER, QModelIndex())  ,layer2)
        mdl.item(row, COL_LAYER).setFlags(QtCore.Qt.NoItemFlags)
        self.layerAddedOrRemoved.emit()
        
        
    def removeLayer(self, mdl, index):
            try:
                mdl.removeRow(index)
                self.layerAddedOrRemoved.emit()
            except:
                return

    def chooseLayerForRemoval(self, iface, mdl):
        
        if mdl.rowCount() < 2:
            if mdl.rowCount() == 1:
                return 0
            return None

        list1 = []
        for i in range(0,mdl.rowCount()):
            list1.append(str(i +1) + " : " + mdl.item(i, COL_NAME).data(QtCore.Qt.EditRole))
        testqt, ok = QInputDialog.getItem(iface.mainWindow(), "Layer selector", "Choose the Layer", list1, False)
        if ok:
            for i in range(0,mdl.rowCount()):
                if testqt == (str(i+1) + " : " + mdl.item(i, COL_NAME).data(QtCore.Qt.EditRole)):
                    return i
        return None
        
    def onClick(self, iface, wdg, mdl, plotlibrary, index1):                    #action when clicking the tableview
        temp = mdl.itemFromIndex(index1)
        if index1.column() == COL_COLOR:                #modifying color
            name = ("%s#%d") % (mdl.item(index1.row(), COL_NAME).data(QtCore.Qt.EditRole), mdl.item(index1.row(), COL_BAND).data(QtCore.Qt.EditRole))
            color = QColorDialog().getColor(temp.data(QtCore.Qt.BackgroundRole))
            if color.isValid():
                mdl.setData( mdl.index(temp.row(), COL_COLOR, QModelIndex())  ,color , QtCore.Qt.BackgroundRole)
                PlottingTool().changeColor(wdg, plotlibrary, color, name, mdl)

        elif index1.column() == COL_BACKGROUND:                #modifying fill color
            name = ("%s#%d") % (mdl.item(index1.row(), COL_NAME).data(QtCore.Qt.EditRole), mdl.item(index1.row(), COL_BAND).data(QtCore.Qt.EditRole))
            tmp_fill_name = name + "_fill"

            self.showFillStyleDialog(wdg, plotlibrary, mdl, temp.row(), tmp_fill_name)


        elif index1.column() == COL_VISIBLE:                #modifying checkbox
            name = ("%s#%d") % (mdl.item(index1.row(), COL_NAME).data(QtCore.Qt.EditRole), mdl.item(index1.row(), COL_BAND).data(QtCore.Qt.EditRole))
            booltemp = temp.data(QtCore.Qt.CheckStateRole)
            if booltemp == True:
                booltemp = False
            else:
                booltemp = True
            mdl.setData( mdl.index(temp.row(), COL_VISIBLE, QModelIndex()), booltemp, QtCore.Qt.CheckStateRole)
            PlottingTool().changeAttachCurve(wdg, plotlibrary, booltemp, name)

        elif False and index1.column() == 4:
            name = mdl.item(index1.row(), COL_BUFFER).data(QtCore.Qt.EditRole)
            print(name)
            
        else:
            return


    def showFillStyleDialog(self, wdg, plotlibrary, mdl, row, name):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=Name:string", 'tempLayer', "memory")

        symbol = mdl.data(mdl.index(row, COL_BACKGROUND, QModelIndex()), QtCore.Qt.UserRole)
        if not symbol:
            symbol = QgsFillSymbolV2.createSimple({'color': '#0F00FF',
                                          'style': 'solid',
                                          'style_border': 'solid',
                                          'color_border': 'black',
                                          'width_border': '0.3'})


        w = QgsSymbolV2SelectorDialog(symbol, QgsStyleV2.defaultStyle(), layer)
        if w.exec_():
            icon = QgsSymbolLayerV2Utils.symbolPreviewIcon(symbol, QSize(50, 50))
            mdl.setData(mdl.index(row, COL_BACKGROUND, QModelIndex()), icon, QtCore.Qt.DecorationRole)
            mdl.setData(mdl.index(row, COL_BACKGROUND, QModelIndex()), symbol, QtCore.Qt.UserRole)

            PlottingTool().changeFillColor(wdg, plotlibrary, symbol, name, mdl)


        
