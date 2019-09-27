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

from qgis.core import *
from qgis.gui import *
import qgis

from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtSvg import *
try:
    from qgis.PyQt.QtWidgets import *
except:
    pass

import platform
from math import sqrt
import shapely
from shapely.geometry import LineString

import numpy as np

from .. import pyqtgraph as pg
from ..pyqtgraph import exporters
pg.setConfigOption('background', 'w')

from .. import dxfwrite
from ..dxfwrite import DXFEngine as dxf

has_qwt = False
has_mpl = False
try:
    from PyQt4.Qwt5 import *
    has_qwt = True
    import itertools # only needed for Qwt plot
except:
    pass


try:
    from matplotlib import *
    import matplotlib
    #print("profiletool : matplotlib %s imported" % matplotlib.__version__)
    has_mpl = True
except:
    pass

from .utils import *
from .CutFillBetweenItem import *


class PlottingTool:

    PolylineLayerName = u'_cutLines'
    PolylineLayerDef = u"Linestring?crs=epsg:4326&field=ID:integer"
    PolygonLayerName = u'_cutLayers'
    PolygonLayerDef = u"Polygon?crs=epsg:4326&field=ID:integer"
    WellsLayerName = u'_wellLines'
    WellsLayerDef = u"Linestring?crs=epsg:4326&field=ID:integer&field=well_name:string&field=well_id:integer"
    LogLineLayerName = u'_logLines'
    LogLineLayerDef = u"Linestring?crs=epsg:4326&field=ID:integer&field=well_id:integer&field=name:string&field=header:string"
    LabelsLayerName = u'_cutLabels'
    LabelsLayerDef = u"point?crs=epsg:4326&field=name:string&field=angle:double&field=kind:integer"
    ZoneLayerName = u'_cutZones'
    ZoneLayerDef = u"Polygon?crs=epsg:4326&field=ID:integer&field=well_id:integer&field=name:string&field=header:string"

    LayerGroupName = u'Разрез'

    """This class manages profile plotting.

    A call to changePlotWidget creates the widget where profiles will be
    plotted.
    Subsequent calls to functions on this class pass along the wdg object
    where profiles are to be plotted.
    Input data is the "profiles" vector, and the ["plot_x"] and ["plot_y"] values
    are used as the data series x and y values respectively.
    """

    def __init__(self):
        plugin_dir = os.path.dirname(__file__)
        self.styleForLayer = {}
        self.styleForLayer[PlottingTool.LabelsLayerName] = plugin_dir + '/../styles/cutlabels.qml'
        self.styleForLayer[PlottingTool.WellsLayerName] = plugin_dir + '/../styles/wellLines.qml'
        self.styleForLayer[PlottingTool.LogLineLayerName] = plugin_dir + '/../styles/logLines.qml'
        self.styleForLayer[PlottingTool.ZoneLayerName] = plugin_dir + '/../styles/zones.qml'

        self.colorRamp = {}
        self.colorRamp[3] = QColor(Qt.black)
        self.colorRamp[4] = QColor(Qt.white)
        self.colorRamp[5] = QColor(255, 0, 255)
        self.colorRamp[6] = QColor(255, 0, 0)
        self.colorRamp[7] = QColor(255, 255, 0)
        self.colorRamp[8] = QColor(0, 255, 0)
        self.colorRamp[9] = QColor(0, 255, 255)
        self.colorRamp[10] = QColor(0, 0, 255)
        self.colorRamp[11] = QColor(191, 191, 191)
        self.colorRamp[12] = QColor(204, 204, 204)
        self.colorRamp[13] = QColor(102, 102, 102)
        self.colorRamp[14] = QColor(0, 0, 128)
        self.colorRamp[15] = QColor(106, 90, 205)
        self.colorRamp[16] = QColor(95, 158, 160)
        self.colorRamp[17] = QColor(64, 224, 208)
        self.colorRamp[18] = QColor(102, 205, 170)
        self.colorRamp[19] = QColor(154, 205, 50)
        self.colorRamp[20] = QColor(34, 139, 34)
        self.colorRamp[21] = QColor(0, 100, 0)
        self.colorRamp[22] = QColor(255, 240, 245)
        self.colorRamp[23] = QColor(218, 165, 32)
        self.colorRamp[24] = QColor(210, 180, 140)
        self.colorRamp[25] = QColor(255, 215, 0)
        self.colorRamp[26] = QColor(255, 127, 80)
        self.colorRamp[27] = QColor(255, 165, 0)
        self.colorRamp[28] = QColor(178, 34, 34)
        self.colorRamp[29] = QColor(250, 128, 114)
        self.colorRamp[30] = QColor(153, 50, 204)
        self.colorRamp[31] = QColor(208, 32, 144)
        self.colorRamp[32] = QColor(255, 69, 0)
        self.colorRamp[33] = QColor(218, 112, 214)
        self.colorRamp[34] = QColor(221, 160, 221)


    def changePlotWidget(self, library, frame_for_plot):

        if library == "PyQtGraph":
            plotWdg = pg.PlotWidget()
            plotWdg.showGrid(True,True,0.5)
            datavline = pg.InfiniteLine(0, angle=90 ,pen=pg.mkPen('r',  width=1) , name = 'cross_vertical' )
            datahline = pg.InfiniteLine(0, angle=0 , pen=pg.mkPen('r',  width=1) , name = 'cross_horizontal')
            plotWdg.addItem(datavline)
            plotWdg.addItem(datahline)
            #cursor
            xtextitem = pg.TextItem('X : /', color = (0,0,0), border = pg.mkPen(color=(0, 0, 0),  width=1), fill=pg.mkBrush('w'), anchor=(0,1))
            ytextitem = pg.TextItem('Y : / ', color = (0,0,0) , border = pg.mkPen(color=(0, 0, 0),  width=1), fill=pg.mkBrush('w'), anchor=(0,0))
            plotWdg.addItem(xtextitem)
            plotWdg.addItem(ytextitem)

            plotWdg.getViewBox().autoRange( items=[])
            plotWdg.getViewBox().disableAutoRange()
            plotWdg.getViewBox().border = pg.mkPen(color=(0, 0, 0),  width=1)

            return plotWdg


        elif library == "Qwt5" and has_qwt:
            plotWdg = QwtPlot(frame_for_plot)
            sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            sizePolicy.setHeightForWidth(plotWdg.sizePolicy().hasHeightForWidth())
            plotWdg.setSizePolicy(sizePolicy)
            plotWdg.setMinimumSize(QSize(0,0))
            plotWdg.setAutoFillBackground(False)
            #Decoration
            plotWdg.setCanvasBackground(Qt.white)
            plotWdg.plotLayout().setAlignCanvasToScales(True)
            zoomer = QwtPlotZoomer(QwtPlot.xBottom, QwtPlot.yLeft, QwtPicker.DragSelection, QwtPicker.AlwaysOff, plotWdg.canvas())
            zoomer.setRubberBandPen(QPen(Qt.blue))
            if platform.system() != "Windows":
                # disable picker in Windows due to crashes
                picker = QwtPlotPicker(QwtPlot.xBottom, QwtPlot.yLeft, QwtPicker.NoSelection, QwtPlotPicker.CrossRubberBand, QwtPicker.AlwaysOn, plotWdg.canvas())
                picker.setTrackerPen(QPen(Qt.green))
            #self.dockwidget.qwtPlot.insertLegend(QwtLegend(), QwtPlot.BottomLegend);
            grid = Qwt.QwtPlotGrid()
            grid.setPen(QPen(QColor('grey'), 0, Qt.DotLine))
            grid.attach(plotWdg)
            return plotWdg

        elif library == "Matplotlib" and has_mpl:
            from matplotlib.figure import Figure
            if int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 4 :
                from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
            elif int(qgis.PyQt.QtCore.QT_VERSION_STR[0]) == 5 :
                from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

            fig = Figure( (1.0, 1.0), linewidth=0.0, subplotpars = matplotlib.figure.SubplotParams(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)    )

            font = {'family' : 'arial', 'weight' : 'normal', 'size'   : 12}
            rc('font', **font)

            rect = fig.patch
            rect.set_facecolor((0.9,0.9,0.9))

            self.subplot = fig.add_axes((0.05, 0.15, 0.92,0.82))
            self.subplot.set_xbound(0,1000)
            self.subplot.set_ybound(0,1000)
            self.manageMatplotlibAxe(self.subplot)
            canvas = FigureCanvasQTAgg(fig)
            sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            canvas.setSizePolicy(sizePolicy)
            return canvas




    def drawVertLine(self, wdg, pointstoDraw, library):
        if library == "PyQtGraph":
            pass

        elif library == "Qwt5" and has_qwt:
            profileLen = 0
            for i in range(0, len(pointstoDraw)-1):
                x1 = float(pointstoDraw[i][0])
                y1 = float(pointstoDraw[i][1])
                x2 = float(pointstoDraw[i+1][0])
                y2 = float(pointstoDraw[i+1][1])
                profileLen = sqrt (((x2-x1)*(x2-x1)) + ((y2-y1)*(y2-y1))) + profileLen
                vertLine = QwtPlotMarker()
                vertLine.setLineStyle(QwtPlotMarker.VLine)
                vertLine.setXValue(profileLen)
                vertLine.attach(wdg.plotWdg)
            profileLen = 0
        elif library == "Matplotlib" and has_mpl:
            profileLen = 0
            for i in range(0, len(pointstoDraw)-1):
                x1 = float(pointstoDraw[i][0])
                y1 = float(pointstoDraw[i][1])
                x2 = float(pointstoDraw[i+1][0])
                y2 = float(pointstoDraw[i+1][1])
                profileLen = sqrt (((x2-x1)*(x2-x1)) + ((y2-y1)*(y2-y1))) + profileLen
                wdg.plotWdg.figure.get_axes()[0].vlines(profileLen, 0, 1000, linewidth = 1)
            profileLen = 0

    def createGeoLayer(self, pp1, pp2, polygonLayer, id):
        fields = polygonLayer.fields()

        with edit(polygonLayer):
            for p1 in pp1:
                minX = min(p1[0][0], p1[-1][0])
                maxX = max(p1[0][0], p1[-1][0])

                for p2 in pp2:
                    newP2 = [k for k in p2 if k[0] >= minX and k[0] <= maxX]
                    if len(newP2):
                        minX1 = min(newP2[0][0], newP2[-1][0])
                        maxX1 = max(newP2[0][0], newP2[-1][0])
                        newP1 = [k for k in p1 if k[0] >= minX1 and k[0] <= maxX1]
                        if len(newP1):
                            polygon = []
                            for p in newP1:
                                polygon.append(QgsPoint(p[0], p[1]))
                            for p in reversed(newP2):
                                polygon.append(QgsPoint(p[0], p[1]))

                            if len(polygon):
                                f = QgsFeature(fields)
                                f.setGeometry(QgsGeometry.fromPolygon([polygon]))
                                f.setAttribute('ID', id-1)
                                polygonLayer.addFeatures([f])


    def getPolygonLayer(self):
        polygonLayers = QgsProject.instance().mapLayersByName(PlottingTool.PolygonLayerName)
        if polygonLayers:
            return polygonLayers[0]
        return None

    def getLineLayer(self):
        lineLayers = QgsProject.instance().mapLayersByName(PlottingTool.PolylineLayerName)
        if lineLayers:
            return lineLayers[0]
        return None

    def profilesToLayer(self, wdg, profiles, xyAspect):
        lineLayer = self.getOrCreateCutLayer(wdg, PlottingTool.PolylineLayerName, PlottingTool.PolylineLayerDef)
        polygonLayer = self.getOrCreateCutLayer(wdg, PlottingTool.PolygonLayerName, PlottingTool.PolygonLayerDef)

        with edit(lineLayer):
            for feat in lineLayer.getFeatures():
                lineLayer.deleteFeature(feat.id())

        with edit(polygonLayer):
            for feat in polygonLayer.getFeatures():
                polygonLayer.deleteFeature(feat.id())

        if profiles is None or len(profiles) < 1:
            return None, None

        aspect = 1.0 / xyAspect

        fields = lineLayer.fields()
        allCurves = []
        with edit(lineLayer):
            for i, profile in enumerate(profiles):
                tmp_name = ("%s#%d") % (profile["layer"].name(), profile["band"])
                tmp_fill_name = tmp_name + "_fill"

                xx = profile["plot_x"]
                yy = profile["plot_y"]
                for j in range(len(yy)):
                    if yy[j] is None:
                        xx[j] = None

                # Split xx and yy into single lines at None values
                xx = [list(g) for k, g in itertools.groupby(xx, lambda x: x is None) if not k]
                yy = [list(g) for k, g in itertools.groupby(yy, lambda x: x is None) if not k]

                curve = []
                for j in range(len(xx)):
                    grpX = xx[j]
                    grpY = yy[j]

                    subLine = []
                    polyLine = []
                    for n in range(len(grpX)):
                        xPos = grpX[n] * aspect# + extent.xMaximum()
                        yPos = grpY[n]# + extent.yMaximum()
                        polyLine.append(QgsPoint(xPos, yPos))
                        subLine.append( (xPos, yPos) )

                    if len(polyLine):
                        curve.append(subLine)

                        f = QgsFeature(fields)
                        f.setGeometry(QgsGeometry.fromPolyline(polyLine))
                        f.setAttribute('ID', i)
                        lineLayer.addFeatures([f])

                allCurves.append(curve)

        for i, c in enumerate(allCurves):
            if i > 0:
                self.createGeoLayer(allCurves[i-1], allCurves[i], polygonLayer, i)

        lineLayer.removeSelection()
        polygonLayer.removeSelection()

        return lineLayer, polygonLayer

    def createPolylineStyle(self, lineLayer, model1):
        categories = []
        for i in range(0, model1.rowCount()):
            symbol = QgsSymbolV2.defaultSymbol(lineLayer.geometryType())
            color = model1.item(i, COL_COLOR).data(QtCore.Qt.BackgroundRole)
            if color:
                symbol.setColor(color)

            nm = model1.item(i, COL_NAME).data(QtCore.Qt.EditRole)
            category = QgsRendererCategoryV2(i, symbol, nm)
            categories.append(category)

        #Rule for frame
        symbol = QgsSymbolV2.defaultSymbol(lineLayer.geometryType())
        symbol.setColor(QtCore.Qt.black)
        category = QgsRendererCategoryV2(1000, symbol, u'Frame')
        categories.append(category)

        renderer = QgsCategorizedSymbolRendererV2('ID', categories)
        lineLayer.setRendererV2(renderer)

    def createPolygonStyle(self, polygonLayer, model1):
        categories = []
        for i in range(0, model1.rowCount()-1):
            ss = model1.item(i, COL_BACKGROUND).data(QtCore.Qt.UserRole)
            if not ss:
                symbol = QgsSymbolV2.defaultSymbol(polygonLayer.geometryType())
            else:
                symbol = ss.clone()

            nm = model1.item(i, COL_NAME).data(QtCore.Qt.EditRole)
            category = QgsRendererCategoryV2(i, symbol, nm)
            categories.append(category)

        renderer = QgsCategorizedSymbolRendererV2('ID', categories)
        polygonLayer.setRendererV2(renderer)


    def getOrCreateLayerGroup(self):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(PlottingTool.LayerGroupName)
        if not group:
            group = root.addGroup(PlottingTool.LayerGroupName)
        return group

    def moveLayerToGroup(self, group, layer):
        root = QgsProject.instance().layerTreeRoot()
        if not group.findLayer(layer.id()):
            rootLayer = root.findLayer(layer.id())
            if rootLayer:
                group.addChildNode(rootLayer.clone())
                root.removeChildNode(rootLayer)
            else:
                group.addLayer(layer)

    def getOrCreateCutLayer(self, wdg, layerName, fields, insertIndex = -1):
        mapCanvas = wdg.iface.mapCanvas()
        renderer = mapCanvas.mapRenderer()

        group = self.getOrCreateLayerGroup()
        lineLayers = QgsProject.instance().mapLayersByName(layerName)
        if not lineLayers:
            lineLayer = QgsVectorLayer(fields, layerName, "memory")
            lineLayer.setCrs(renderer.destinationCrs())
            QgsMapLayerRegistry.instance().addMapLayer(lineLayer, False)
            if insertIndex >= 0:
                group.insertLayer(insertIndex, lineLayer)
            else:
                group.addLayer(lineLayer)

            if layerName in self.styleForLayer:
                lineLayer.loadNamedStyle(self.styleForLayer[layerName])
        else:
            lineLayer = lineLayers[0]
            self.moveLayerToGroup(group, lineLayer)
        return lineLayer

    def clearLayer(self, layer):
        with edit(layer):
            for feat in layer.getFeatures():
                layer.deleteFeature(feat.id())

    def removeCutFrame(self, lineLayer):
        if not lineLayer:
            return

        expr = QgsExpression('\"ID\" = 1000')
        with edit(lineLayer):
            for feat in lineLayer.getFeatures(QgsFeatureRequest(expr)):
                lineLayer.deleteFeature(feat.id())
        lineLayer.updateExtents()

    def addCutFrame(self, layer, extent):
        if not layer:
            return

        pt1 = QgsPoint(extent.xMinimum(), extent.yMinimum())
        pt2 = QgsPoint(extent.xMaximum(), extent.yMinimum())
        pt3 = QgsPoint(extent.xMaximum(), extent.yMaximum())
        pt4 = QgsPoint(extent.xMinimum(), extent.yMaximum())

        fields = layer.fields()
        with edit(layer):
            f = QgsFeature(fields)
            f.setGeometry(QgsGeometry.fromPolyline([pt1, pt2, pt3, pt4, pt1]))
            f.setAttribute('ID', 1000)
            layer.addFeatures([f])
        layer.removeSelection()



    def createCutLabels(self, wdg, extent):
        pointLayer = self.getOrCreateCutLayer(wdg, PlottingTool.LabelsLayerName, PlottingTool.LabelsLayerDef)
        wdg.plotCanvas.addNewLayer(pointLayer.id(), True)

        expr = QgsExpression('\"kind\" = 1')
        with edit(pointLayer):
            for feat in pointLayer.getFeatures(QgsFeatureRequest(expr)):
                pointLayer.deleteFeature(feat.id())

        start = extent.yMinimum()
        end = extent.yMaximum()
        x = extent.xMinimum()
        fields = pointLayer.fields()
        with edit(pointLayer):
            while start <= end:
                f = QgsFeature(fields)
                f.setGeometry(QgsGeometry.fromPoint(QgsPoint(x, start)))
                f.setAttribute('name', '%.0f' % start)
                f.setAttribute('kind', 1)
                pointLayer.addFeatures([f])
                start += 100
        pointLayer.removeSelection()

    def getCutExtent(self, wdg):
        wdg.plotCanvas._updateExtent()

        extent = wdg.plotCanvas.getExtent()

        topLimit = wdg.wellTopDepth
        bottomLimit = wdg.wellBottomDepth
        if extent.yMinimum() < 0:
            topLimit = wdg.wellBottomDepth
            bottomLimit = wdg.wellTopDepth

        if topLimit > -9999:
            newMinY = extent.yMinimum()
        else:
            newMinY = getNiceInterval(extent.yMinimum(), extent.yMinimum() < 0)
        if bottomLimit > -9999:
            newMaxY =extent.yMaximum()
        else:
            newMaxY = getNiceInterval(extent.yMaximum(), extent.yMaximum() > 0)
        return QgsRectangle(extent.xMinimum() - 5, newMinY, extent.xMaximum() + 5, newMaxY)

    def updateDecorations(self, wdg, lineLayer = None):
        if not lineLayer:
            lineLayer = self.getOrCreateCutLayer(wdg, PlottingTool.PolylineLayerName, PlottingTool.PolylineLayerDef)

        self.removeCutFrame(lineLayer)

        newExtent = self.getCutExtent(wdg)
        self.addCutFrame(lineLayer, newExtent)
        self.createCutLabels(wdg, newExtent)

    def addAllLayers(self, wdg):
        lineLayer = self.getOrCreateCutLayer(wdg, PlottingTool.PolylineLayerName, PlottingTool.PolylineLayerDef)
        if lineLayer:
            wdg.plotCanvas.addNewLayer(lineLayer.id())

        polygonLayer = self.getOrCreateCutLayer(wdg, PlottingTool.PolygonLayerName, PlottingTool.PolygonLayerDef)
        if polygonLayer:
            wdg.plotCanvas.addNewLayer(polygonLayer.id())

        lineLayer = self.getOrCreateCutLayer(wdg, PlottingTool.WellsLayerName, PlottingTool.WellsLayerDef, 0)
        if lineLayer:
            wdg.plotCanvas.addNewLayer(lineLayer.id())

        lineLayer = self.getOrCreateCutLayer(wdg, PlottingTool.LogLineLayerName, PlottingTool.LogLineLayerDef, 0)
        if lineLayer:
            wdg.plotCanvas.addNewLayer(lineLayer.id(), True)

        pointLayer = self.getOrCreateCutLayer(wdg, PlottingTool.LabelsLayerName, PlottingTool.LabelsLayerDef)
        if pointLayer:
            wdg.plotCanvas.addNewLayer(pointLayer.id(), True)

        polyLayer = self.getOrCreateCutLayer(wdg, PlottingTool.ZoneLayerName, PlottingTool.ZoneLayerDef, 1)
        if polyLayer:
            wdg.plotCanvas.addNewLayer(polyLayer.id())


    def attachCurves(self, wdg, profiles, model1, library, xyAspect):

        lineLayer, polygonLayer = self.profilesToLayer(wdg, profiles, xyAspect)
        if lineLayer:
            wdg.plotCanvas.addNewLayer(lineLayer.id())
            self.createPolylineStyle(lineLayer, model1)

        if polygonLayer:
            wdg.plotCanvas.addNewLayer(polygonLayer.id())
            self.createPolygonStyle(polygonLayer, model1)

        self.updateDecorations(wdg, lineLayer)


    def attachWells(self, wdg, profiles, model1):
        lineLayer = self.getOrCreateCutLayer(wdg, PlottingTool.WellsLayerName, PlottingTool.WellsLayerDef, 0)

        step = 100.0
        with edit(lineLayer):
            for feat in lineLayer.getFeatures():
                lineLayer.deleteFeature(feat.id())

            fields = lineLayer.fields()
            for p in profiles:
                wellName = p[0]
                wellId = p[1]
                trajectory = p[2]
                polyline = [QgsPoint(pt[0], pt[1]*-1.0) for pt in trajectory]
                f = QgsFeature(fields)
                geom = QgsGeometry.fromPolyline(polyline)
                f.setGeometry(geom)
                f.setAttribute('well_name', wellName)
                f.setAttribute('well_id', wellId)
                lineLayer.addFeatures([f])


        decorLayer = self.getOrCreateCutLayer(wdg, PlottingTool.LabelsLayerName, PlottingTool.LabelsLayerDef, 0)
        fields = decorLayer.fields()

        with edit(decorLayer):
            expr = QgsExpression('\"kind\" = 2')
            for feat in decorLayer.getFeatures(QgsFeatureRequest(expr)):
                decorLayer.deleteFeature(feat.id())

            for p in profiles:
                trajectory = p[2]
                startMd = trajectory[0][2]
                polyline = [(pt[0], pt[1] * -1.0) for pt in trajectory]
                line = LineString(polyline)
                count = int(line.length / step) + 1
                for interval in xrange(0, count):
                    pt1 = line.interpolate(interval * step)
                    pt2 = line.interpolate(interval * step + 1)
                    angle = QLineF(QPointF(pt1.coords[0][0], pt1.coords[0][1]),
                                   QPointF(pt2.coords[0][0], pt2.coords[0][1])).angle()
                    f = QgsFeature(fields)
                    f.setGeometry(QgsGeometry.fromPoint(QgsPoint(pt1.coords[0][0], pt1.coords[0][1])))
                    f.setAttribute('name', "%.0f" % (interval * step + startMd))
                    f.setAttribute('kind', 2)
                    f.setAttribute('angle', angle)
                    decorLayer.addFeatures([f])

        lineLayer.removeSelection()
        wdg.plotCanvas.addNewLayer(lineLayer.id(), False)
        decorLayer.removeSelection()

        self.updateDecorations(wdg)

    def clearLogLayer(self, wdg):
        lineLayer = self.getOrCreateCutLayer(wdg, PlottingTool.LogLineLayerName, PlottingTool.LogLineLayerDef, 0)
        with edit(lineLayer):
            for feat in lineLayer.getFeatures():
                lineLayer.deleteFeature(feat.id())

    def attachLogs(self, wdg, logsOnWells, model1, xyAspect):
        lineLayer = self.getOrCreateCutLayer(wdg, PlottingTool.LogLineLayerName, PlottingTool.LogLineLayerDef, 0)

        aspect = 1.0 / xyAspect
        extent = wdg.plotCanvas.getExtent()
        topY = extent.yMaximum()

        traceColors = {}
        with edit(lineLayer):
            for feat in lineLayer.getFeatures():
                lineLayer.deleteFeature(feat.id())

            fields = lineLayer.fields()
            for p in logsOnWells:
                wellId = p[0]
                tracks = p[1]

                for track in tracks:
                    curY = topY + 10
                    for trace in track:
                        name = trace[0]
                        trajectories = trace[1]
                        traceColors[name] = trace[2]
                        for trajectory in trajectories:
                            polyline = [QgsPoint(pt[0], pt[1]*-1.0) for pt in trajectory]
                            f = QgsFeature(fields)
                            f.setGeometry(QgsGeometry.fromPolyline(polyline))
                            f.setAttribute('well_id', wellId)
                            f.setAttribute('name', name)
                            lineLayer.addFeatures([f])

                        #Add header
                        trackWidth = trace[4]
                        if trackWidth > 0:
                            text = '{0} - {1} - {2}'.format(trace[5], name, trace[6])
                            headerLeft = trace[3]
                            headerWidth = headerLeft + trackWidth
                            polyline = [QgsPoint(headerLeft, curY), QgsPoint(headerWidth, curY)]
                            f = QgsFeature(fields)
                            f.setGeometry(QgsGeometry.fromPolyline(polyline))
                            f.setAttribute('well_id', wellId)
                            f.setAttribute('header', text)
                            f.setAttribute('name', name)
                            f.setAttribute('ID', 1)
                            lineLayer.addFeatures([f])
                            curY += 10


        lineLayer.removeSelection()

        categories = []
        for key in traceColors.keys():
            symbol = QgsSymbolV2.defaultSymbol(lineLayer.geometryType())
            colorIndex = int(traceColors[key])
            if colorIndex in self.colorRamp:
                symbol.setColor(self.colorRamp[colorIndex])
            else:
                symbol.setColor(QColor(int(colorIndex)))

            category = QgsRendererCategoryV2(key, symbol, key)
            categories.append(category)

        renderer = QgsCategorizedSymbolRendererV2('name', categories)
        lineLayer.setRendererV2(renderer)

        wdg.plotCanvas.addNewLayer(lineLayer.id(), True)

    def attachZones(self, wdg, zoneOnWells, model1, xyAspect):
        polyLayer = self.getOrCreateCutLayer(wdg, PlottingTool.ZoneLayerName, PlottingTool.ZoneLayerDef, 1)

        aspect = 1.0 / xyAspect
        extent = wdg.plotCanvas.getExtent()
        topY = extent.yMaximum()

        with edit(polyLayer):
            for feat in polyLayer.getFeatures():
                polyLayer.deleteFeature(feat.id())

            fields = polyLayer.fields()
            zoneColors = {}
            for p in zoneOnWells:
                wellId = p[0]
                intervals = p[1]
                for inter in intervals:
                    name = inter[0]
                    zoneColor = inter[1]
                    points = inter[2]
                    zoneColors[name] = zoneColor
                    polyline = [QgsPoint(pt[0], pt[1] * -1.0) for pt in points]
                    f = QgsFeature(fields)
                    f.setGeometry(QgsGeometry.fromPolygon([polyline]))
                    f.setAttribute('well_id', wellId)
                    f.setAttribute('name', name)
                    polyLayer.addFeatures([f])

        polyLayer.removeSelection()

        categories = []
        for key in zoneColors.keys():
            symbol = QgsSymbolV2.defaultSymbol(polyLayer.geometryType())
            colorIndex = int(zoneColors[key])
            if colorIndex in self.colorRamp:
                symbol.setColor(self.colorRamp[colorIndex])
            else:
                symbol.setColor(QColor(int(colorIndex)))

            category = QgsRendererCategoryV2(str(key), symbol, str(key))
            categories.append(category)

        renderer = QgsCategorizedSymbolRendererV2('name', categories)
        polyLayer.setRendererV2(renderer)

        wdg.plotCanvas.addNewLayer(polyLayer.id())

    def findMin(self, values):
        minVal = min( z for z in values if z is not None )
        return minVal


    def findMax(self, values):
        maxVal = max( z for z in values if z is not None )
        return maxVal



    def plotRangechanged(self, wdg, library):

        if library == "PyQtGraph":
            range = wdg.plotWdg.getViewBox().viewRange()
            wdg.disconnectYSpinbox()
            wdg.sbMaxVal.setValue(range[1][1])
            wdg.sbMinVal.setValue(range[1][0])
            wdg.connectYSpinbox()


    def reScalePlot(self, wdg, profiles, library,auto = False):                         # called when spinbox value changed
        if profiles == None:
            return

        minimumValue = wdg.sbMinVal.value()
        maximumValue = wdg.sbMaxVal.value()

        y_vals = [p["plot_y"] for p in profiles]

        if minimumValue == maximumValue:
            # Automatic mode
            minimumValue = 1000000000
            maximumValue = -1000000000
            for i in range(0,len(y_vals)):
                if profiles[i]["layer"] != None and len([z for z in y_vals[i] if z is not None]) > 0:
                    minimumValue = min(self.findMin(y_vals[i]), minimumValue)
                    maximumValue = max(self.findMax(y_vals[i]) + 1,
                                       maximumValue)
                    wdg.sbMaxVal.setValue(maximumValue)
                    wdg.sbMinVal.setValue(minimumValue)
                    wdg.sbMaxVal.setEnabled(True)
                    wdg.sbMinVal.setEnabled(True)

        if minimumValue < maximumValue:
            if library == "PyQtGraph":
                wdg.disconnectPlotRangechanged()
                if auto:
                    wdg.plotWdg.getViewBox().autoRange( items=wdg.plotWdg.getPlotItem().listDataItems())
                    wdg.plotRangechanged()
                else:
                    wdg.plotWdg.getViewBox().setYRange( minimumValue,maximumValue , padding = 0 )
                wdg.connectPlotRangechanged()


            if library == "Qwt5" and has_qwt:
                wdg.plotWdg.setAxisScale(0,minimumValue,maximumValue,0)
                wdg.plotWdg.replot()

            elif library == "Matplotlib" and has_mpl:
                if auto:
                    wdg.sbMaxVal.setValue(wdg.sbMinVal.value())
                    self.reScalePlot(wdg, profiles, library)
                else:
                    wdg.plotWdg.figure.get_axes()[0].set_ybound(minimumValue,maximumValue)
                    wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
                    wdg.plotWdg.draw()


    def clearData(self, wdg, profiles, library):                             # erase one of profiles
        pass
        # if library == "PyQtGraph":
        #     allItems = wdg.plotWdg.getPlotItem().items
        #     for item in allItems:
        #         if type(item) is CutFillBetweenItem:
        #             wdg.plotWdg.removeItem(item)
        #
        #     pitems = wdg.plotWdg.getPlotItem().listDataItems()
        #     for item in pitems:
        #         wdg.plotWdg.removeItem(item)
        #     try:
        #         wdg.plotWdg.scene().sigMouseMoved.disconnect(self.mouseMoved)
        #     except:
        #         pass
        #
        # elif library == "Qwt5" and has_qwt:
        #     wdg.plotWdg.clear()
        #     for i in range(0,len(profiles)):
        #         profiles[i]["plot_x"] = []
        #         profiles[i]["plot_y"] = []
        #     temp1 = wdg.plotWdg.itemList()
        #     for j in range(len(temp1)):
        #         if temp1[j].rtti() == QwtPlotItem.Rtti_PlotCurve:
        #             temp1[j].detach()
        #     #wdg.plotWdg.replot()
        #
        # elif library == "Matplotlib" and has_mpl:
        #     wdg.plotWdg.figure.get_axes()[0].cla()
        #     self.manageMatplotlibAxe(wdg.plotWdg.figure.get_axes()[0])
        #     #wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
        #     #wdg.plotWdg.draw()
        # wdg.sbMaxVal.setEnabled(False)
        # wdg.sbMinVal.setEnabled(False)
        # wdg.sbMaxVal.setValue(0)
        # wdg.sbMinVal.setValue(0)





    def changeColor(self,wdg, library, color1, name, model1):                    #Action when clicking the tableview - color
        lineLayer = self.getLineLayer()
        if lineLayer:
            self.createPolylineStyle(lineLayer, model1)

        if library == "PyQtGraph":
            pitems = wdg.plotWdg.getPlotItem()
            for i, item in enumerate(pitems.listDataItems()):
                if item.name() == name:
                    item.setPen( color1,  width=2)

        if library == "Qwt5":
            temp1 = wdg.plotWdg.itemList()
            for i in range(len(temp1)):
                if name == str(temp1[i].title().text()):
                    curve = temp1[i]
                    curve.setPen(QPen(color1, 3))
                    wdg.plotWdg.replot()
                    # break  # Don't break as there may be multiple curves with a common name (segments separated with None values)

        if library == "Matplotlib":
            temp1 = wdg.plotWdg.figure.get_axes()[0].get_lines()
            for i in range(len(temp1)):
                if name == str(temp1[i].get_gid()):
                    temp1[i].set_color((color1.red() / 255.0 , color1.green() / 255.0 , color1.blue() / 255.0 ,  color1.alpha() / 255.0 ))
                    wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
                    wdg.plotWdg.figure.canvas.draw()
                    wdg.plotWdg.draw()
                    break

    def changeFillColor(self,wdg, library, symbol, name, model1):                    #Action when clicking the tableview - fill

        polygonLayer = self.getPolygonLayer()
        if polygonLayer:
            self.createPolygonStyle(polygonLayer, model1)


    def changeAttachCurve(self, wdg, library, bool, name):                #Action when clicking the tableview - checkstate

        if library == "PyQtGraph":
            pitems = wdg.plotWdg.getPlotItem()
            for i, item in enumerate(pitems.listDataItems()):
                if item.name() == name:
                    if bool:
                        item.setVisible(True)
                    else:
                        item.setVisible(False)

        elif library == "Qwt5":
            temp1 = wdg.plotWdg.itemList()
            for i in range(len(temp1)):
                if name == str(temp1[i].title().text()):
                    curve = temp1[i]
                    if bool:
                        curve.setVisible(True)
                    else:
                        curve.setVisible(False)
                    wdg.plotWdg.replot()
                    break

        if library == "Matplotlib":

            temp1 = wdg.plotWdg.figure.get_axes()[0].get_lines()
            for i in range(len(temp1)):
                if name == str(temp1[i].get_gid()):
                    if bool:
                        temp1[i].set_visible(True)
                    else:
                        temp1[i].set_visible(False)
                    wdg.plotWdg.figure.get_axes()[0].redraw_in_frame()
                    wdg.plotWdg.figure.canvas.draw()
                    wdg.plotWdg.draw()

                    break


    def manageMatplotlibAxe(self, axe1):
        axe1.grid()
        axe1.tick_params(axis = "both", which = "major", direction= "out", length=10, width=1, bottom = True, top = False, left = True, right = False)
        axe1.minorticks_on()
        axe1.tick_params(axis = "both", which = "minor", direction= "out", length=5, width=1, bottom = True, top = False, left = True, right = False)


    def outPrint(self, iface, wdg, mdl, library): # Postscript file rendering doesn't work properly yet.
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i, COL_VISIBLE).data(Qt.CheckStateRole):
                name = str(mdl.item(i, COL_NAME).data(Qt.EditRole))
                #return
        fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".ps","PostScript Format (*.ps)")
        if fileName:
            if library == "Qwt5" and has_qwt:
                printer = QPrinter()
                printer.setCreator("QGIS Profile Plugin")
                printer.setDocName("QGIS Profile")
                printer.setOutputFileName(fileName)
                printer.setColorMode(QPrinter.Color)
                printer.setOrientation(QPrinter.Portrait)
                dialog = QPrintDialog(printer)
                if dialog.exec_():
                    wdg.plotWdg.print_(printer)
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))


    def outPDF(self, iface, wdg, mdl, library):
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i, COL_VISIBLE).data(Qt.CheckStateRole):
                name = str(mdl.item(i, COL_NAME).data(Qt.EditRole))
                break
        fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As","Profile of " + name + ".pdf","Portable Document Format (*.pdf)")
        if fileName:
            if library == "Qwt5" and has_qwt:
                printer = QPrinter()
                printer.setCreator('QGIS Profile Plugin')
                printer.setOutputFileName(fileName)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOrientation(QPrinter.Landscape)
                wdg.plotWdg.print_(printer)
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))



    def outSVG(self, iface, wdg, mdl, library):
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i, COL_VISIBLE).data(Qt.CheckStateRole):
                name = str(mdl.item(i, COL_NAME).data(Qt.EditRole))
                #return
        #fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As",wdg.profiletoolcore.loaddirectory,"Profile of " + name + ".svg","Scalable Vector Graphics (*.svg)")
        fileName = QFileDialog.getSaveFileName(parent = iface.mainWindow(),
                                               caption = "Save As",
                                               directory = wdg.profiletoolcore.loaddirectory,
                                               #filter = "Profile of " + name + ".png",
                                               filter = "Scalable Vector Graphics (*.svg)")


        if fileName:
            if isinstance(fileName,tuple):  #pyqt5 case
                fileName = fileName[0]

            wdg.profiletoolcore.loaddirectory = os.path.dirname(fileName)
            qgis.PyQt.QtCore.QSettings().setValue("profiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)

            if library == "PyQtGraph":
                exporter = exporters.SVGExporter(wdg.plotWdg.getPlotItem().scene())
                # exporter = pg.exporters.SVGExporter(wdg.plotWdg.getPlotItem().scene())
                exporter.export(fileName = fileName)

            elif library == "Qwt5" and has_qwt:
                printer = QSvgGenerator()
                printer.setFileName(fileName)
                printer.setSize(QSize(800, 400))
                wdg.plotWdg.print_(printer)
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))

    def outPNG(self, iface, wdg, mdl, library):
        for i in range (0,mdl.rowCount()):
            if  mdl.item(i, COL_VISIBLE).data(Qt.CheckStateRole):
                name = str(mdl.item(i, COL_NAME).data(Qt.EditRole))
                #return
        fileName = QFileDialog.getSaveFileName(parent = iface.mainWindow(),
                                               caption = "Save As",
                                               directory = wdg.profiletoolcore.loaddirectory,
                                               #filter = "Profile of " + name + ".png",
                                               filter = "Portable Network Graphics (*.png)")

        if fileName:

            if isinstance(fileName,tuple):  #pyqt5 case
                fileName = fileName[0]

            wdg.profiletoolcore.loaddirectory = os.path.dirname(fileName)
            qgis.PyQt.QtCore.QSettings().setValue("profiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)

            if library == "PyQtGraph":
                exporter =  exporters.ImageExporter(wdg.plotWdg.getPlotItem())
                exporter.export(fileName)
            elif library == "Qwt5" and has_qwt:
                QPixmap.grabWidget(wdg.plotWdg).save(fileName, "PNG")
            elif library == "Matplotlib" and has_mpl:
                wdg.plotWdg.figure.savefig(str(fileName))

    def outDXF(self, iface, wdg, mdl, library, profiles):

        for i in range (0,mdl.rowCount()):
            if  mdl.item(i, COL_VISIBLE).data(Qt.CheckStateRole):
                name = str(mdl.item(i, COL_NAME).data(Qt.EditRole))
                #return
        #fileName = QFileDialog.getSaveFileName(iface.mainWindow(), "Save As",wdg.profiletoolcore.loaddirectory,"Profile of " + name + ".dxf","dxf (*.dxf)")
        fileName = QFileDialog.getSaveFileName(parent = iface.mainWindow(),
                                               caption = "Save As",
                                               directory = wdg.profiletoolcore.loaddirectory,
                                               #filter = "Profile of " + name + ".png",
                                               filter = "dxf (*.dxf)")
        if fileName:
            if isinstance(fileName,tuple):  #pyqt5 case
                fileName = fileName[0]

            wdg.profiletoolcore.loaddirectory = os.path.dirname(fileName)
            qgis.PyQt.QtCore.QSettings().setValue("profiletool/lastdirectory", wdg.profiletoolcore.loaddirectory)

            drawing = dxf.drawing(fileName)
            for profile in profiles:
                name = profile['layer'].name()
                drawing.add_layer(name)
                points = [(profile['x'][i], profile['y'][i],profile['z'][i]) for i in range(len(profile['l']))]
                drawing.add(dxf.polyline(points, color=7, layer=name))
            drawing.save()
