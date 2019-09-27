# -*- coding: utf-8 -*-

#Qt import
from qgis.PyQt import uic, QtCore, QtGui, QtXml

#qgis import
import qgis
from qgis.core import *
from qgis.gui import *
import numpy
from math import sqrt
from shapely.geometry import LineString, Point

from .dbReaderBase import *


class WellsDbReader(DbReaderBase):

    def __init__(self, iface, parent = None):
        DbReaderBase.__init__(self, iface, parent)

    def readWells(self, pointstoDraw1, dist, aspect, topLimit, bottomLimit):
        if not self.initDb():
            return None

        profileGeom = qgis.core.QgsGeometry.fromPolyline([QgsPoint(point[0], point[1]) for point in pointstoDraw1])
        geominlayercrs = qgis.core.QgsGeometry(profileGeom)
        tempresult = geominlayercrs.transform(self.screenXform)

        pointInCrs = geominlayercrs.asPolyline()
        seg_len = [0]
        for p_start, p_end in zip(pointInCrs[:-1], pointInCrs[1:]):
            dx = p_end.x() - p_start.x()
            dy = p_end.y() - p_start.y()
            seg_len.append(seg_len[-1] + sqrt(dx*dx + dy*dy))

        def interpolate(pt):
            distline = geominlayercrs.closestSegmentWithContext(pt)
            p_end = distline[1]
            vIndex = distline[2] - 1
            p_start = pointInCrs[vIndex]
            dx = p_end.x() - p_start.x()
            dy = p_end.y() - p_start.y()
            len = sqrt(dx*dx + dy*dy)
            return seg_len[vIndex] + len

        def checkPoint(y):
            if ((topLimit < -9998 or (topLimit > -9999 and y >= topLimit)) and
                    (bottomLimit < -9998 or (bottomLimit > -9999 and y <= bottomLimit))):
                return True
            else:
                return False

        dbWells = self._readWells()

        wellsOnProfile = []
        for row in dbWells:
            name = row[0]
            lng = row[19]
            lat = row[20]
            wellId = int(row[1])
            if row[9]:
                elev = float(row[9])
            else:
                elev = 0.0
            if lng and lat:
                pt = QgsPoint(lng, lat)

                if self.xform:
                    pt = self.xform.transform(pt)

                startX = pt.x()
                startY = pt.y()
                polyLine = []
                pt3 = (startX, startY, -elev, 0)
                polyLine = [pt3]

                blob_x = numpy.fromstring(self.db.blobToString(row[21]), '>f').astype('d')
                blob_y = numpy.fromstring(self.db.blobToString(row[22]), '>f').astype('d')
                blob_z = numpy.fromstring(self.db.blobToString(row[23]), '>f').astype('d')
                blob_md = numpy.fromstring(self.db.blobToString(row[24]), '>f').astype('d')
                for ip in xrange(len(blob_x)):
                    dx = blob_x[ip]
                    dy = blob_y[ip]
                    z = blob_z[ip] - elev
                    md = blob_md[ip]
                    pt3 = (startX + dx, startY + dy, z, md)
                    polyLine.append(pt3)

                if len(polyLine) > 1:
                    minDist = min(geominlayercrs.closestSegmentWithContext(QgsPoint(pt[0], pt[1])) for pt in polyLine)

                    if minDist[0] <= dist:
                        trajectory = [(interpolate(QgsPoint(pt[0], pt[1]))*aspect, pt[2], pt[3]) for pt in polyLine if checkPoint(pt[2])]
                        trajectory = self.simplify(trajectory, 0.001)
                        if len(trajectory):
                            wellsOnProfile.append( (name, wellId, trajectory) )

        return wellsOnProfile

    #TODO: realise
    def simplify(self, trajectory, tolerance):
        if len(trajectory) < 3:
            return trajectory

        newLine = [trajectory[0]]
        center = None
        for pt in trajectory[1:]:
            lastPt = newLine[-1]
            if center:
                line = LineString([lastPt, pt])
                point = Point(center[0], center[1])
                if point.distance(line) >= tolerance:
                    newLine.append(center)
            center = pt
        newLine.append(trajectory[-1])
        return newLine


    def _readWells(self):
        try:
            return self.db.execute(self.get_sql('WellBottoms.sql'))

        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)
            return None




