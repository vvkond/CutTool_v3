# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
# Profile
# Copyright (C) 2008  Borys Jurgiel
# Copyright (C) 2012  Patrice Verchere
# -----------------------------------------------------------
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
# ---------------------------------------------------------------------

# Qt import
from qgis.PyQt import uic, QtCore, QtGui, QtXml

try:
    from qgis.PyQt.QtGui import QWidget, QInputDialog
except:
    from qgis.PyQt.QtWidgets import QWidget, QInputDialog
from qgis.PyQt.QtSvg import *  # required in some distros
# qgis import
import qgis
from qgis.core import *
from qgis.gui import *
# other
import platform
import sys
from math import sqrt
import numpy as np
import ast
from shapely.geometry import LineString
# plugin import
from .dataReaderTool import DataReaderTool
from .plottingtool import PlottingTool
from .ptmaptool import ProfiletoolMapTool, ProfiletoolMapToolRenderer
from ..ui.ptdockwidget import PTDockWidget
from ..ui.dlgZonationList import *
from . import profilers
from .utils import *
from ..dbtools.wellsDbReader import *
from ..dbtools.templatesDbReader import *
from ..dbtools.traceDbReader import *
from ..dbtools.zoneDbReader import *
from ..dbtools.mesh import *
import os


class ProfileToolCore(QWidget):

    def __init__(self, iface, plugincore, parent=None):
        QWidget.__init__(self, parent)
        self.iface = iface
        self.plugincore = plugincore

        # remimber repository for saving
        if QtCore.QSettings().value("profiletool/lastdirectory") != '':
            self.loaddirectory = QtCore.QSettings().value("profiletool/lastdirectory")
        else:
            self.loaddirectory = ''

        self.isInitialised = False
        self.finishing = False
        # mouse tracking
        self.doTracking = False
        # the datas / results
        self.profiles = None  # dictionary where is saved the plotting data {"l":[l],"z":[z], "layer":layer1, "curve":curve1}
        # The line information
        self.pointstoDraw = []
        self.wellsOnProfile = []
        self.logsOnWells = []
        self.zonesOnWells = []
        # he renderer for temporary polyline
        # self.toolrenderer = ProfiletoolMapToolRenderer(self)
        self.toolrenderer = None
        # the maptool previously loaded
        self.saveTool = None  # Save the standard mapttool for restoring it at the end
        # Used to remove highlighting from previously active layer.
        self.previousLayerId = None
        self.x_cursor = None  # Keep track of last x position of cursor
        # the dockwidget
        self.dockwidget = PTDockWidget(self.iface, self)
        # Initialize the dockwidget combo box with the list of available profiles.
        # (Use sorted list to be sure that Height is always on top and
        # the combobox order is consistent)
        for profile in sorted(profilers.PLOT_PROFILERS):
            self.dockwidget.plotComboBox.addItem(profile)
        self.dockwidget.plotComboBox.setCurrentIndex(0)
        self.dockwidget.plotComboBox.currentIndexChanged.connect(self.plotComboBox_indexChanged)
        # lambda index: self.plotProfil())
        # dockwidget graph zone
        self.dockwidget.changePlotLibrary(self.dockwidget.cboLibrary.currentIndex())

    def activateProfileMapTool(self):
        self.saveTool = self.iface.mapCanvas().mapTool()  # Save the standard mapttool for restoring it at the end
        # Listeners of mouse
        self.toolrenderer = ProfiletoolMapToolRenderer(self)
        self.toolrenderer.connectTool()
        self.toolrenderer.setSelectionMethod(
            self.dockwidget.comboBox.currentIndex())
        # init the mouse listener comportement and save the classic to restore it on quit
        self.iface.mapCanvas().setMapTool(self.toolrenderer.tool)

    def plotComboBox_indexChanged(self, index):
        if type(index) is int:
            self.plotProfil()
            self.dockwidget.plotCanvas._updateExtent()

    # ******************************************************************************************
    # **************************** function part *************************************************
    # ******************************************************************************************

    def clearProfil(self):
        self.updateProfilFromFeatures(None, [])

    def updateProfilFromFeatures(self, layer, features, plotProfil=True):
        """Updates self.profiles from given feature list.

        This function extracts the list of coordinates from the given
        feature set and calls updateProfil.
        This function also manages selection/deselection of features in the
        active layer to highlight the feature being profiled.
        """
        pointstoDraw = []

        # Remove selection from previous layer if it still exists
        previousLayer = QgsProject.instance().mapLayer(self.previousLayerId)
        if previousLayer:
            previousLayer.removeSelection()

        if layer:
            self.previousLayerId = layer.id()
        else:
            self.previousLayerId = None

        if layer:
            layer.removeSelection()
            layer.select([f.id() for f in features])
            first_segment = True
            for feature in features:
                if not feature.geometry():
                    continue

                if first_segment:
                    k = 0
                    first_segment = False
                else:
                    k = 1
                while not feature.geometry().vertexAt(k) == QgsPoint(0, 0):
                    point2 = self.toolrenderer.tool.toMapCoordinates(
                        layer,
                        QgsPointXY(feature.geometry().vertexAt(k)))
                    pointstoDraw += [[point2.x(), point2.y()]]
                    k += 1
        self.updateProfil(pointstoDraw, False, plotProfil)

    def updateProfil(self, points1, removeSelection=True, plotProfil=True):
        if not self.isInitialised or len(points1) < 2:
            return

        """Updates self.profiles from values in points1.

        This function can be called from updateProfilFromFeatures or from
        ProfiletoolMapToolRenderer (with a list of points from rubberband).
        """
        if removeSelection:
            # Be sure that we unselect anything in the previous layer.
            previousLayer = QgsProject.instance().mapLayer(self.previousLayerId)
            if previousLayer:
                previousLayer.removeSelection()

        self.pointstoDraw = points1
        self.profiles = []

        self.dockwidget.plotComboBox.setEnabled(len(points1) > 0)

        # calculate profiles
        for i in range(0, self.dockwidget.mdl.rowCount()):
            self.profiles.append({"layer": self.dockwidget.mdl.item(i, COL_LAYER).data(QtCore.Qt.EditRole)})
            self.profiles[i]["band"] = self.dockwidget.mdl.item(i, COL_BAND).data(QtCore.Qt.EditRole)

            if self.dockwidget.mdl.item(i, COL_LAYER).data(
                    QtCore.Qt.EditRole).type() == qgis.core.QgsMapLayer.VectorLayer:
                self.profiles[i], _, _ = DataReaderTool().dataVectorReaderTool(self.iface, self.toolrenderer.tool,
                                                                               self.profiles[i], self.pointstoDraw,
                                                                               float(self.dockwidget.mdl.item(i,
                                                                                                              COL_BUFFER).data(
                                                                                   QtCore.Qt.EditRole)))
            else:
                if self.dockwidget.profileInterpolationCheckBox.isChecked():
                    if self.dockwidget.fullResolutionCheckBox.isChecked():
                        resolution_mode = "full"
                    else:
                        resolution_mode = "limited"
                else:
                    resolution_mode = "samples"

                self.profiles[i] = DataReaderTool().dataRasterReaderTool(self.iface, self.toolrenderer.tool,
                                                                         self.profiles[i], self.pointstoDraw,
                                                                         resolution_mode)
            # Plotting coordinate values are initialized on plotProfil
            self.profiles[i]["plot_x"] = []
            self.profiles[i]["plot_y"] = []

        if plotProfil:
            self.plotProfil()

    def plotProfil(self, vertline=True):
        self.disableMouseCoordonates()

        self.removeClosedLayers(self.dockwidget.mdl)
        # PlottingTool().clearData(self.dockwidget, self.profiles, self.dockwidget.plotlibrary)

        # if not self.pointstoDraw:
        #    self.updateCursorOnMap(self.x_cursor)
        #    return

        if vertline:  # Plotting vertical lines at the node of polyline draw
            PlottingTool().drawVertLine(self.dockwidget, self.pointstoDraw, self.dockwidget.plotlibrary)

        # calculate buffer geometries if search buffer is set in mdt layer
        geoms = []
        for i in range(0, self.dockwidget.mdl.rowCount()):
            if self.dockwidget.mdl.item(i, COL_LAYER).data(
                    QtCore.Qt.EditRole).type() == qgis.core.QgsMapLayer.VectorLayer:
                _, buffer, multipoly = DataReaderTool().dataVectorReaderTool(self.iface, self.toolrenderer.tool,
                                                                             self.profiles[i], self.pointstoDraw,
                                                                             float(self.dockwidget.mdl.item(i,
                                                                                                            COL_BUFFER).data(
                                                                                 QtCore.Qt.EditRole)))
                geoms.append(buffer)
                geoms.append(multipoly)

        if self.dockwidget.showModel:
            DataReaderTool().simModelReaderTool(self.iface, self.dockwidget, self.pointstoDraw)

        self.toolrenderer.setBufferGeometry(geoms)

        # Update coordinates to use in plot (height, slope %...)
        profile_func, setup_func = profilers.PLOT_PROFILERS[self.dockwidget.plotComboBox.currentText()]

        for profile in self.profiles:
            profile["plot_x"], profile["plot_y"] = profile_func(profile)

        setup_func(self.dockwidget)

        # plot profiles
        PlottingTool().attachCurves(self.dockwidget, self.profiles, self.dockwidget.mdl, self.dockwidget.plotlibrary,
                                    self.dockwidget.mXyAspectRatio.value())
        # PlottingTool().reScalePlot(self.dockwidget, self.profiles, self.dockwidget.plotlibrary)
        # create tab with profile xy
        self.dockwidget.updateCoordinateTab()
        # Mouse tracking

        self.updateCursorOnMap(self.x_cursor)
        self.enableMouseCoordonates(self.dockwidget.plotlibrary)

    def updateWells(self):
        if self.dockwidget.showWells:
            reader = WellsDbReader(self.iface)

            aspect = 1.0 / self.dockwidget.mXyAspectRatio.value()

            topDepthLimit = self.dockwidget.wellTopDepth
            bottomDepthLimit = self.dockwidget.wellBottomDepth
            self.wellsOnProfile = reader.readWells(self.pointstoDraw, self.dockwidget.distanceToWell,
                                                   aspect, topDepthLimit, bottomDepthLimit)

            # Mesh test
            flag = False
            if flag:
                tmpWells = []
                for p in self.wellsOnProfile:
                    wellId = p[1]
                    wellTrajectory = p[2]

                    mesh = TrajectoryMesh().create(wellTrajectory, 126, 10)
                    for m in mesh:
                        tmpWells.append((p[0], wellId, [(m[0][0], m[0][1], 0), (m[2][0], m[2][1], 100)]))
                        tmpWells.append((p[0], wellId, [(m[1][0], m[1][1], 0), (m[3][0], m[3][1], 100)]))

                PlottingTool().attachWells(self.dockwidget, tmpWells, self.dockwidget.mdl)
            else:
                PlottingTool().attachWells(self.dockwidget, self.wellsOnProfile, self.dockwidget.mdl)

            if len(self.wellsOnProfile) > 0:
                self.redrawLogs(self.dockwidget.currentTemplateId)
            else:
                PlottingTool().clearLogLayer(self.dockwidget)
                self.iface.messageBar().pushMessage(self.tr(u"Geology cut"), u'Скважины не найдены, убедитесь в правильности выбора проекта',
                                                    level=QgsMessageBar.CRITICAL, duration=10)

    def redrawLogs(self, templateId):
        self.updateLogs(templateId)
        pt = PlottingTool()
        pt.attachLogs(self.dockwidget, self.logsOnWells, self.dockwidget.mdl,
                                  self.dockwidget.mXyAspectRatio.value())
        pt.attachZones(self.dockwidget, self.zonesOnWells, self.dockwidget.mdl,
                                  self.dockwidget.mXyAspectRatio.value())


    def updateLogs(self, templateId):
        self.logsOnWells = []
        self.zonesOnWells = []
        if templateId < 0:
            return False

        defTrackWidth = self.dockwidget.trackWidth  # m
        isDefaultWidth = self.dockwidget.isDefaultTrackWidth

        tracks = TemplatesDbReader(self.iface).loadTemplate(templateId)

        if not tracks:
            return False

        logReader = TracesDbReader(self.iface)
        zoneReader = ZoneDbReader(self.iface)
        aspect = 1.0  # / self.dockwidget.mXyAspectRatio.value()

        topDepthLimit = self.dockwidget.wellTopDepth
        bottomDepthLimit = self.dockwidget.wellBottomDepth

        plugin_dir = os.path.dirname(__file__).replace('\\', '/')
        uri = u'file:///{0}?type=csv&geomType=none&subsetIndex=no&delimiter=;&watchFile=no'.format(
            plugin_dir + u'/../styles/curve_colors.csv')
        curveTypeColors = {}
        try:
            curveColorLayer = QgsVectorLayer(uri, 'CurveColors', "delimitedtext")

            features = curveColorLayer.getFeatures()
            for f in features:
                curveTypeColors[f.attribute('type')] = int(f.attribute('color'))
        except Exception as e:
            QgsMessageLog.logMessage(u"Curve colors read error: {0}".format(str(e)), tag="CutPlugin")

        wellFilter = ','.join(str(p[1]) for p in self.wellsOnProfile)

        for p in self.wellsOnProfile:
            wellId = p[1]
            wellTrajectory = p[2]
            # print p[0]

            if len(wellTrajectory) < 2:
                continue

            sumTrackWidth = 0
            for track in tracks:
                trackWidth = float(defTrackWidth)  # m
                if 'width' in track and not isDefaultWidth:
                    trackWidth = track['width'] / 10.0
                sumTrackWidth += trackWidth

            wellLogTraces = []
            wellZones = []
            mesh = TrajectoryMesh().create(wellTrajectory, sumTrackWidth, 10)

            trackOffset = 0
            headerOffset = wellTrajectory[0][0]
            trackIndex = 1
            for track in tracks:
                trackName = str(trackIndex)
                trackIndex+=1
                if 'name' in track:
                    trackName = track['name']

                trackWidth = float(defTrackWidth)  # m
                if 'width' in track and not isDefaultWidth:
                    trackWidth = track['width'] / 10.0

                needBorder = False

                scaledTrackTraces = []
                scaledTrackZones = []
                if 'traces' in track:
                    trackTraces = track['traces']
                    trackStart = len(mesh)
                    trackEnd = 0
                    for trace in trackTraces:
                        traceType = trace['type']
                        traceColor = 3
                        if 'color' in trace:
                            traceColor = trace['color']
                        elif traceType in curveTypeColors:
                            traceColor = curveTypeColors[traceType]

                        traceParts, realMinValue, realMaxValue, logOrLinear, tmpAlias = logReader.readTrace(
                            trace['type'],
                            trace['alias'], trace['status'], trace['edited'], wellId)
                        traceName = tmpAlias  # + '/' + traceType

                        if 'scaleType' in trace:
                            logOrLinear = trace['scaleType']

                        if 'min' in trace and 'max' in trace:
                            realMinValue = float(trace['min'])
                            realMaxValue = float(trace['max'])
                        minValue = realMinValue
                        maxValue = realMaxValue
                        if logOrLinear > 0:
                            minValue = math.log10(minValue)
                            maxValue = math.log10(maxValue)
                        kx = trackWidth / (maxValue - minValue)

                        scaledTraceParts = []
                        prevScaleNum = 0
                        for l in traceParts:
                            scaledLog = []
                            for pt in l:
                                val = pt[1]
                                if logOrLinear > 0:
                                    try:
                                        val = math.log10(val)
                                    except:
                                        val = 0
                                val = kx * (val - minValue)
                                if val < 0:
                                    val = 0
                                scaleNum = 0
                                while val > trackWidth:
                                    val = val / 5.0
                                    scaleNum += 1
                                    if scaleNum > 5:
                                        break

                                if prevScaleNum != scaleNum:
                                    if prevScaleNum < scaleNum:
                                        scaledLog.append((pt[0], trackWidth / sumTrackWidth + trackOffset))
                                    scaledLog.append((pt[0], -9999))
                                    if prevScaleNum > scaleNum:
                                        scaledLog.append((pt[0], trackWidth / sumTrackWidth + trackOffset))
                                scaledLog.append((pt[0], val / sumTrackWidth + trackOffset))
                                prevScaleNum = scaleNum

                            scaledLogs = [list(g) for k, g in itertools.groupby(scaledLog, lambda x: x[1] < -9998) if
                                          not k]
                            for scaledLog in scaledLogs:
                                logOnCut, start, end = TrajectoryMesh().curveAlongCurve(mesh, scaledLog, aspect)
                                if len(logOnCut):
                                    scaledTraceParts.append(logOnCut)
                                    if start < trackStart:
                                        trackStart = start
                                    if end > trackEnd:
                                        trackEnd = end

                        if len(scaledTraceParts):
                            scaledTrackTraces.append((traceName, scaledTraceParts, traceColor, headerOffset,
                                                      trackWidth, realMinValue, realMaxValue))
                            needBorder = True

                if 'zonations' in track:
                    zonations = track['zonations']
                    for zone in zonations:
                        zonationId = zone['ZonSLD']
                        selectMode = zone['SelectMode']
                        if selectMode == TemplatesDbReader.ZONATION_LATEST: #Latest
                            zonationId = zoneReader.readZonationLatestForWell(wellId)
                        elif selectMode == TemplatesDbReader.ZONATION_MATCH: #Match description pattern
                            if len(zonationId) == 0:
                                zonationId = zoneReader.readZonationByDesc(zone['DescPattern'])
                                zone['ZonSLD'] = zonationId
                        elif selectMode == TemplatesDbReader.ZONATION_SELECT_WHEN_LOADING: #Select when loading
                            if len(zonationId) == 0:
                                zonations = zoneReader.readZonationList(wellFilter)
                                dlg = DlgZonationList(zonations, self.tr('Select zonations for Template track ')+trackName, self)
                                if dlg.exec_():
                                    zonationId = dlg.selectedZonations()
                                zone['ZonSLD'] = zonationId

                        zones = zoneReader.readZone(wellId, zonationId)
                        for z in zones:
                            rightBorderMd = [(m[2], trackOffset) for m in wellTrajectory if m[2] >= z[1] and m[2] <= z[2]]
                            if len(rightBorderMd):
                                rightBorderMd.insert(0, (z[1], trackOffset))
                                rightBorderMd.append((z[2], trackOffset))
                                ww = trackOffset + trackWidth / sumTrackWidth
                                leftBorderMd = [(m[0], ww) for m in rightBorderMd]
                                leftBorderOnCut, start, end = TrajectoryMesh().curveAlongCurve(mesh, leftBorderMd, aspect)
                                rightBorderOnCut, start, end = TrajectoryMesh().curveAlongCurve(mesh, rightBorderMd, aspect)
                                for m in reversed(rightBorderOnCut):
                                    leftBorderOnCut.append(m)
                                wellZones.append((z[0], z[3], leftBorderOnCut))
                                needBorder = True

                if needBorder:
                    trackOffset += trackWidth / sumTrackWidth
                    headerOffset += trackWidth

                    # Add track border
                    borderMd = [(m[2], trackOffset) for m in wellTrajectory]
                    borderOnCut, start, end = TrajectoryMesh().curveAlongCurve(mesh, borderMd, aspect)
                    if len(borderOnCut):
                        scaledTrackTraces.append(('track', [borderOnCut], 3, headerOffset, -1, 0, 0))

                    wellLogTraces.append(scaledTrackTraces)


            if len(wellLogTraces):
                self.logsOnWells.append((wellId, wellLogTraces))
            if len(wellZones):
                self.zonesOnWells.append((wellId, wellZones))

        return True

    def getWellsLayer(self):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(PlottingTool.LayerGroupName)
        if group:
            for l in group.findLayers():
                if l.layerName() == PlottingTool.WellsLayerName:
                    return l.layer()

        return None

    def updateCursorOnMap(self, x):
        self.x_cursor = x
        if self.pointstoDraw and self.doTracking:
            if x is not None:
                points = [QgsPointXY(*p) for p in self.pointstoDraw]
                geom = qgis.core.QgsGeometry.fromPolylineXY(points)
                try:
                    if len(points) > 1:
                        # May crash with a single point in polyline on 
                        # QGis 3.0.2, 
                        # Issue #1 on PANOimagen's repo,
                        # Bug report #18987 on qgis.                    
                        pointprojected = geom.interpolate(x).asPoint()
                    else:
                        pointprojected = points[0]
                except (IndexError, AttributeError):
                    print 'Error'
                    pointprojected = None

                if pointprojected:
                    self.toolrenderer.rubberbandpoint.setCenter(pointprojected)
            self.toolrenderer.rubberbandpoint.show()
        else:
            self.toolrenderer.rubberbandpoint.hide()

    # remove layers which were removed from QGIS
    def removeClosedLayers(self, model1):
        qgisLayerNames = []
        if int(QtCore.QT_VERSION_STR[0]) == 4:  # qgis2
            qgisLayerNames = [layer.name() for layer in self.iface.legendInterface().layers()]
            """
            for i in range(0, self.iface.mapCanvas().layerCount()):
                    qgisLayerNames.append(self.iface.mapCanvas().layer(i).name())
            """
        elif int(QtCore.QT_VERSION_STR[0]) == 5:  # qgis3
            qgisLayerNames = [layer.name() for layer in qgis.core.QgsProject.instance().mapLayers().values()]

        # print('qgisLayerNames',qgisLayerNames)
        for i in range(0, model1.rowCount()):
            layerName = model1.item(i, COL_NAME).data(QtCore.Qt.EditRole)
            if not layerName in qgisLayerNames:
                self.dockwidget.removeLayer(i)
                self.removeClosedLayers(model1)
                break

    def cleaning(self):
        self.saveSelectedLayers()

        self.finishing = True
        # self.clearProfil()
        if self.toolrenderer:
            self.dockwidget.plotCanvas.cleaning()
            self.toolrenderer.cleaning()

    # ******************************************************************************************
    # **************************** mouse interaction *******************************************
    # ******************************************************************************************

    def activateMouseTracking(self, int1):

        if self.dockwidget.TYPE == 'PyQtGraph':

            if int1 == 2:
                self.doTracking = True
            elif int1 == 0:
                self.doTracking = False

        elif self.dockwidget.TYPE == 'Matplotlib':
            if int1 == 2:
                self.doTracking = True
                self.cid = self.dockwidget.plotWdg.mpl_connect('motion_notify_event', self.mouseevent_mpl)
            elif int1 == 0:
                self.doTracking = False
                try:
                    self.dockwidget.plotWdg.mpl_disconnect(self.cid)
                except:
                    pass
                try:
                    if self.vline:
                        self.dockwidget.plotWdg.figure.get_axes()[0].lines.remove(self.vline)
                        self.dockwidget.plotWdg.draw()
                except Exception as e:
                    print(str(e))

    def mouseevent_mpl(self, event):
        """
        case matplotlib library
        """
        if event.xdata:
            try:
                if self.vline:
                    self.dockwidget.plotWdg.figure.get_axes()[0].lines.remove(self.vline)
            except Exception as e:
                pass
            xdata = float(event.xdata)
            self.vline = self.dockwidget.plotWdg.figure.get_axes()[0].axvline(xdata, linewidth=2, color='k')
            self.dockwidget.plotWdg.draw()
            """
            i=1
            while  i < len(self.tabmouseevent) and xdata > self.tabmouseevent[i][0] :
                i=i+1
            i=i-1
            x = self.tabmouseevent[i][1] +(self.tabmouseevent[i+1][1] - self.tabmouseevent[i][1] )/ ( self.tabmouseevent[i+1][0] - self.tabmouseevent[i][0]  )  *   (xdata - self.tabmouseevent[i][0])
            y = self.tabmouseevent[i][2] +(self.tabmouseevent[i+1][2] - self.tabmouseevent[i][2] )/ ( self.tabmouseevent[i+1][0] - self.tabmouseevent[i][0]  )  *   (xdata - self.tabmouseevent[i][0])
            self.toolrenderer.rubberbandpoint.show()
            point = QgsPoint( x,y )
            self.toolrenderer.rubberbandpoint.setCenter(point)
            """
            self.updateCursorOnMap(xdata)

    def enableMouseCoordonates(self, library):
        self.dockwidget.plotCanvas.canvas.xyCoordinates.connect(self.xyCoordinates)

        # if library == "PyQtGraph":
        # self.dockwidget.plotWdg.scene().sigMouseMoved.connect(self.mouseMovedPyQtGraph)
        # self.dockwidget.plotWdg.getViewBox().autoRange( items=self.dockwidget.plotWdg.getPlotItem().listDataItems())
        # self.dockwidget.plotWdg.getViewBox().sigRangeChanged.connect(self.dockwidget.plotRangechanged)
        # self.dockwidget.connectPlotRangechanged()

    def disableMouseCoordonates(self):
        try:
            self.dockwidget.plotCanvas.canvas.xyCoordinates.disconnect(self.xyCoordinates)
            # self.dockwidget.plotWdg.scene().sigMouseMoved.disconnect(self.mouseMovedPyQtGraph)
        except:
            pass

        # self.dockwidget.disconnectPlotRangechanged()

    def xyCoordinates(self, pos):
        if self.dockwidget.showcursor:
            self.updateCursorOnMap(pos.x() * self.dockwidget.xyAspect)

    def mouseMovedPyQtGraph(self,
                            pos):  # si connexion directe du signal "mouseMoved" : la fonction reçoit le point courant
        roundvalue = 3

        if self.dockwidget.plotWdg.sceneBoundingRect().contains(pos):  # si le point est dans la zone courante

            if self.dockwidget.showcursor:
                range = self.dockwidget.plotWdg.getViewBox().viewRange()
                mousePoint = self.dockwidget.plotWdg.getViewBox().mapSceneToView(
                    pos)  # récupère le point souris à partir ViewBox

                datas = []
                pitems = self.dockwidget.plotWdg.getPlotItem()
                ytoplot = None
                xtoplot = None

                if len(pitems.listDataItems()) > 0:
                    # get data and nearest xy from cursor
                    compt = 0
                    try:
                        for item in pitems.listDataItems():
                            if item.isVisible():
                                x, y = item.getData()
                                nearestindex = np.argmin(abs(np.array(x) - mousePoint.x()))
                                if compt == 0:
                                    xtoplot = np.array(x)[nearestindex]
                                    ytoplot = np.array(y)[nearestindex]
                                else:
                                    if abs(np.array(y)[nearestindex] - mousePoint.y()) < abs(ytoplot - mousePoint.y()):
                                        ytoplot = np.array(y)[nearestindex]
                                        xtoplot = np.array(x)[nearestindex]
                                compt += 1
                    except ValueError:
                        ytoplot = None
                        xtoplot = None
                    # plot xy label and cursor
                    if not xtoplot is None and not ytoplot is None:
                        for item in self.dockwidget.plotWdg.allChildItems():
                            if str(type(item)) == "<class 'CutTool.pyqtgraph.graphicsItems.InfiniteLine.InfiniteLine'>":
                                if item.name() == 'cross_vertical':
                                    item.show()
                                    item.setPos(xtoplot)
                                elif item.name() == 'cross_horizontal':
                                    item.show()
                                    item.setPos(ytoplot)
                            elif str(type(item)) == "<class 'CutTool.pyqtgraph.graphicsItems.TextItem.TextItem'>":
                                if item.textItem.toPlainText()[0] == 'X':
                                    item.show()
                                    item.setText('X : ' + str(round(xtoplot, roundvalue)))
                                    item.setPos(xtoplot, range[1][0])
                                elif item.textItem.toPlainText()[0] == 'Y':
                                    item.show()
                                    item.setText('Y : ' + str(round(ytoplot, roundvalue)))
                                    item.setPos(range[0][0], ytoplot)
                # tracking part
                self.updateCursorOnMap(xtoplot)

    # ******************************************************************************************
    # **************************** save/restore state *******************************************
    # ******************************************************************************************
    def saveSelectedLayers(self):
        if self.finishing:
            return

        cutDef = []
        for i in range(0, self.dockwidget.mdl.rowCount()):
            rowDef = {}
            rowDef['selected'] = self.dockwidget.mdl.item(i, COL_VISIBLE).data(QtCore.Qt.CheckStateRole)
            color = self.dockwidget.mdl.item(i, COL_COLOR).data(QtCore.Qt.BackgroundRole)
            if color:
                rowDef['color'] = color.name()
            rowDef['name'] = self.dockwidget.mdl.item(i, COL_NAME).data(QtCore.Qt.EditRole)
            rowDef['band'] = self.dockwidget.mdl.item(i, COL_BAND).data(QtCore.Qt.EditRole)
            rowDef['searchBuffer'] = self.dockwidget.mdl.item(i, COL_BUFFER).data(QtCore.Qt.EditRole)
            layer = self.dockwidget.mdl.item(i, COL_LAYER).data(QtCore.Qt.EditRole)
            rowDef['id'] = layer.id()

            symbol = self.dockwidget.mdl.item(i, COL_BACKGROUND).data(QtCore.Qt.UserRole)
            rowDef['backColor'] = self.symbolToString(symbol)

            cutDef.append(rowDef)

        proj = QgsProject.instance()
        proj.writeEntry("CutPlugin", "GeologyCut", str(cutDef))
        proj.writeEntry("CutPlugin", "PointToDraw", str(self.pointstoDraw))
        proj.writeEntry("CutPlugin", "XyAspectRatio", self.dockwidget.mXyAspectRatio.value())
        proj.writeEntry("CutPlugin", "plotIndex", self.dockwidget.plotComboBox.currentIndex())
        proj.writeEntry("CutPlugin", "comboBox", self.dockwidget.comboBox.currentIndex())
        proj.writeEntry("CutPlugin", "distanceToWell", self.dockwidget.distanceToWell)
        proj.writeEntry("CutPlugin", "wellTopDepth", self.dockwidget.wellTopDepth)
        proj.writeEntry("CutPlugin", "wellBottomDepth", self.dockwidget.wellBottomDepth)
        proj.writeEntry("CutPlugin", "currentTemplateId", self.dockwidget.currentTemplateId)
        proj.writeEntry("CutPlugin", "isDefaultTrackWidth", 'True' if self.dockwidget.isDefaultTrackWidth else 'False')
        proj.writeEntry("CutPlugin", "trackWidth", self.dockwidget.trackWidth)

    def symbolToString(self, symbol):
        if not symbol:
            return ''
        doc = QtXml.QDomDocument()
        styleEl = QgsSymbolLayerV2Utils.saveSymbol('Background', symbol, doc)
        doc.appendChild(styleEl)
        return doc.toString()

    def stringToSymbol(self, symbolXml):
        doc = QtXml.QDomDocument()
        if doc.setContent(symbolXml):
            el = doc.documentElement()
            return QgsSymbolLayerV2Utils.loadSymbol(el)

        return None

    def restoreSelectedLayers(self):
        proj = QgsProject.instance()
        cutDefStr = proj.readEntry("CutPlugin", "GeologyCut", "[]")[0]
        pointsStr = proj.readEntry("CutPlugin", "PointToDraw", '[]')[0]

        self.dockwidget.blockAllSignals(True)

        try:
            self.dockwidget.mXyAspectRatio.setValue(float(proj.readEntry("CutPlugin", "XyAspectRatio", '1.0')[0]))
            self.dockwidget.plotComboBox.setCurrentIndex(int(proj.readEntry("CutPlugin", "plotIndex", '0')[0]))
            self.dockwidget.comboBox.setCurrentIndex(int(proj.readEntry("CutPlugin", "comboBox", '0')[0]))
            self.dockwidget.mWellDistance.setValue(float(proj.readEntry("CutPlugin", "distanceToWell", '50')[0]))
            self.dockwidget.wellTopDepthEdit.setValue(float(proj.readEntry("CutPlugin", "wellTopDepth", '-9999')[0]))
            self.dockwidget.wellBottomDepthEdit.setValue(
                float(proj.readEntry("CutPlugin", "wellBottomDepth", '-9999')[0]))
            self.dockwidget.currentTemplateId = int(proj.readEntry("CutPlugin", "currentTemplateId", "-1")[0])
            self.dockwidget.isDefaultTrackWidth = proj.readEntry("CutPlugin", "isDefaultTrackWidth", 'True')[
                                                      0] == 'True'
            self.dockwidget.trackWidth = int(proj.readEntry("CutPlugin", "trackWidth", '10')[0])

            cutDefs = ast.literal_eval(cutDefStr)

            self.dockwidget.tableViewTool.blockSignals(True)

            reg = QgsMapLayerRegistry.instance()
            for row in cutDefs:
                layer = reg.mapLayer(row['id'])
                if layer:
                    self.dockwidget.addLayer(layer)

                    mdl = self.dockwidget.mdl
                    r = mdl.rowCount() - 1
                    mdl.setData(mdl.index(r, COL_VISIBLE, QtCore.QModelIndex()), bool(row['selected']),
                                QtCore.Qt.CheckStateRole)
                    mdl.setData(mdl.index(r, COL_COLOR, QtCore.QModelIndex()), QtGui.QColor(row['color']),
                                QtCore.Qt.BackgroundRole)

                    symbolXml = str(row['backColor'])
                    symbol = self.stringToSymbol(symbolXml)
                    if not symbol:
                        symbol = QgsFillSymbolV2.createSimple({'color': '#0000FF',
                                                               'style': 'solid',
                                                               'style_border': 'solid',
                                                               'color_border': 'black',
                                                               'width_border': '0.3'})
                    icon = QgsSymbolLayerV2Utils.symbolPreviewIcon(symbol, QtCore.QSize(50, 50))
                    mdl.setData(mdl.index(r, COL_BACKGROUND, QtCore.QModelIndex()), symbol, QtCore.Qt.UserRole)
                    mdl.setData(mdl.index(r, COL_BACKGROUND, QtCore.QModelIndex()), icon, QtCore.Qt.DecorationRole)
                    mdl.setData(mdl.index(r, COL_NAME, QtCore.QModelIndex()), icon, QtCore.Qt.DecorationRole)

            self.pointstoDraw = ast.literal_eval(pointsStr)

            if len(self.pointstoDraw):
                self.isInitialised = True
                PlottingTool().addAllLayers(self.dockwidget)
                # self.updateProfil(self.pointstoDraw, False, True)
                # self.updateWells()

                self.toolrenderer.setPointsToDraw(self.pointstoDraw)

        except Exception as e:
            QgsMessageLog.logMessage(u"Cut restore error: {0}".format(str(e)), tag="CutPlugin")

        self.dockwidget.tableViewTool.blockSignals(False)
        self.isInitialised = True

        self.dockwidget.blockAllSignals(False)
