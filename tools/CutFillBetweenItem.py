# -*- coding: utf-8 -*-

from ..pyqtgraph.Qt import QtGui, USE_PYQT5, USE_PYQT4, USE_PYSIDE
from ..pyqtgraph import functions as fn
from ..pyqtgraph import PlotDataItem
from ..pyqtgraph import PlotCurveItem

#Qt import
from qgis.PyQt import QtCore, QtGui
from qgis.core import *
from qgis.gui import *
import math
try:
    import itertools
except:
    pass



class CutFillBetweenItem(QtGui.QGraphicsPathItem):
    def __init__(self, iface1, curve1=None, curve2=None, symbol = None):
        QtGui.QGraphicsPathItem.__init__(self)

        if symbol:
            self.mShapeStyleSymbol = symbol.clone()
        else:
            self.mShapeStyleSymbol = QgsFillSymbolV2.createSimple({'color': '#0F00FF',
                                                               'style': 'solid',
                                                               'style_border': 'solid',
                                                               'color_border': 'black',
                                                               'width_border': '0.3'})

        self.iface = iface1

        self.curves = None
        if curve1 is not None and curve2 is not None:
            self.setCurves(curve1, curve2)
        elif curve1 is not None or curve2 is not None:
            raise Exception("Must specify two curves to fill between.")

        self.updatePath()

    def setStyleSymbol(self, symbol):
        self.mShapeStyleSymbol = symbol.clone()
        self.update()

    def paint(self, painter, style, widget):
        painter.save()

        painter.setRenderHint(QtGui.QPainter.Antialiasing )

        dotsPerMM = painter.device().logicalDpiX() / 25.4;
        ms = self.iface.mapCanvas().mapSettings()
        ms.setOutputDpi(painter.device().logicalDpiX())

        # QgsMessageLog.logMessage(u"DpiX={0}, dotPerMm = {1}".format(painter.device().logicalDpiX(), dotsPerMM), tag="CutPlugin")

        context = QgsRenderContext.fromMapSettings(ms)
        context.setPainter(painter)
        context.setForceVectorOutput(True)

        self.mShapeStyleSymbol.startRender(context)
        pathPolygons = self.path().toFillPolygons()
        tr = painter.transform()
        painter.setTransform(QtGui.QTransform())

        for p in pathPolygons:
            pathPolygon = tr.map(p)
            rings = []
            self.mShapeStyleSymbol.renderPolygon( pathPolygon, rings, QgsFeature(), context )


        self.mShapeStyleSymbol.stopRender(context)

        painter.restore()

    def setBrush(self, *args, **kwds):
        QtGui.QGraphicsPathItem.setBrush(self, fn.mkBrush(*args, **kwds))

    def setPen(self, *args, **kwds):
        QtGui.QGraphicsPathItem.setPen(self, fn.mkPen(*args, **kwds))

    def setCurves(self, curve1, curve2):
        """Set the curves to fill between.

        Arguments must be instances of PlotDataItem or PlotCurveItem.

        Added in version 0.9.9
        """
        if self.curves is not None:
            for c in self.curves:
                try:
                    c.sigPlotChanged.disconnect(self.curveChanged)
                except (TypeError, RuntimeError):
                    pass

        curves = [curve1, curve2]
        for c in curves:
            if not isinstance(c, PlotDataItem) and not isinstance(c, PlotCurveItem):
                raise TypeError("Curves must be PlotDataItem or PlotCurveItem.")
        self.curves = curves
        curve1.sigPlotChanged.connect(self.curveChanged)
        curve2.sigPlotChanged.connect(self.curveChanged)
        self.setZValue(min(curve1.zValue(), curve2.zValue()) - 1)
        self.curveChanged()

    def setBrush(self, *args, **kwds):
        """Change the fill brush. Acceps the same arguments as pg.mkBrush()"""
        QtGui.QGraphicsPathItem.setBrush(self, fn.mkBrush(*args, **kwds))

    def curveChanged(self):
        self.updatePath()

    def updatePath(self):
        if self.curves is None:
            self.setPath(QtGui.QPainterPath())
            return

        points = []
        for c in self.curves:
            if isinstance(c, PlotDataItem):
                x, y = c.curve.getData()
                points.append(zip(x, y))
            elif isinstance(c, PlotCurveItem):
                x, y = c.getData()
                points.append(zip(x, y))

        if len(points) < 2:
            return

        pp1 = [list(g) for k, g in itertools.groupby(points[0], lambda x: math.isnan(x[1])) if not k]
        pp2 = [list(g) for k, g in itertools.groupby(points[1], lambda x: math.isnan(x[1])) if not k]

        path = QtGui.QPainterPath()
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
                        path.moveTo(newP1[0][0], newP1[0][1])
                        for p in newP1:
                            path.lineTo(p[0], p[1])
                        for p in reversed(newP2):
                            path.lineTo(p[0], p[1])
                        path.closeSubpath()



        # paths = []
        # for c in self.curves:
        #     if isinstance(c, PlotDataItem):
        #         paths.append(c.curve.getPath())
        #     elif isinstance(c, PlotCurveItem):
        #         paths.append(c.getPath())
        #
        # path = QtGui.QPainterPath()
        # transform = QtGui.QTransform()
        # ps1 = paths[0].toSubpathPolygons(transform)
        # ps2 = paths[1].toReversed().toSubpathPolygons(transform)
        # ps2.reverse()
        # if len(ps1) == 0 or len(ps2) == 0:
        #     self.setPath(QtGui.QPainterPath())
        #     return
        #
        # for p1, p2 in zip(ps1, ps2):
        #     path.addPolygon(p1 + p2)

        self.setPath(path)