# -*- coding: utf-8 -*-

from qgis.core import *
from PyQt4.QtCore import *
import numpy as np
import bisect
import math
from shapely.geometry import LineString, Polygon
import time

class TrajectoryMesh:

    #baseCurve as [(x,tvd,md)...(x,tvd,md)]
    #curve as [(md,value)...(md,value)]
    def curveAlongCurve(self, baseCurve, curve, xyAspect):
        offsetTvd = []
        aspect = xyAspect

        if len(baseCurve) < 2:
            return offsetTvd, -1, -1

        md = [m[4][1] for m in baseCurve]
        # test = [(m[0]*aspect, m[1]) for m in baseCurve ]

        count = len(md)
        firstIndex = -1
        lastIndex = -1
        for pt in curve:
            i = bisect.bisect_left(md, pt[0])
            if i >= count or (i == 0 and abs(pt[0] - md[0]) > 0.1):
                continue

            if firstIndex < 0:
                firstIndex = i
                lastIndex = firstIndex
            else:
                lastIndex = i

            _max = baseCurve[i][4][1]
            _min = baseCurve[i][4][0]
            t = 0
            if _max-_min != 0:
                t = (pt[0] - _min) / (_max - _min)

            quad = baseCurve[i]
            xx = t * (quad[1][0] - quad[0][0]) + quad[0][0]
            yy = t * (quad[1][1] - quad[0][1]) + quad[0][1]
            xx1 = t * (quad[3][0] - quad[2][0]) + quad[2][0]
            yy1 = t * (quad[3][1] - quad[2][1]) + quad[2][1]

            xx = pt[1] * (xx1 - xx) + xx
            yy = pt[1] * (yy1 - yy) + yy

            offsetTvd.append((xx, yy))

        return offsetTvd, firstIndex, lastIndex

    #line in form [(x1,y1), (x2,y2)]
    def _lineLength(self, line):
        return math.hypot(line[1][0]-line[0][0], line[1][1]-line[0][1])


    def create(self, polyline, distance, miterLimit):
        theMesh = []

        if len(polyline) < 2 or distance == 0:
            return theMesh


        segments = []
        rightParts = []
        md = []

        startTime = time.time()
        startI = 0
        for i in xrange(1, len(polyline)):
            x1,y1, x2, y2 = polyline[startI][0], polyline[startI][1], polyline[i][0], polyline[i][1]
            seg = QLineF(x1, y1, x2, y2)
            length = seg.length()

            if length > 0:
                segments.append(seg)
                md.append((polyline[startI][2], polyline[i][2]))

                px = seg.dy() / length
                py = -seg.dx() / length

                p1 = QPointF(x1 + px * distance, y1 + py * distance)
                p2 = QPointF(x2 + px * distance, y2 + py * distance)
                rightParts.append(QLineF(p1, p2))

                startI = i

        self.throwOutRings(rightParts, segments, miterLimit)
        if distance > 0:
            for i in xrange(len(segments)):
                if i > 0:
                    if rightParts[i-1].p2() != rightParts[i].p1():
                        theMesh.append( ((segments[i-1].p2().x(),   segments[i-1].p2().y()),
                                         (segments[i].p1().x(),     segments[i].p1().y()),
                                         (rightParts[i-1].p2().x(), rightParts[i-1].p2().y()),
                                         (rightParts[i].p1().x(),   rightParts[i].p1().y()),
                                         (md[i-1][1], md[i][0])))
                theMesh.append(((segments[i].p1().x(),      segments[i].p1().y()),
                                (segments[i].p2().x(),      segments[i].p2().y()),
                                (rightParts[i].p1().x(),    rightParts[i].p1().y()),
                                (rightParts[i].p2().x(),    rightParts[i].p2().y()),
                                (md[i][0], md[i][1])))
        else:
            for i in xrange(len(segments)):
                if i > 0:
                    if rightParts[i-1].p2() != rightParts[i].p1():
                        theMesh.append( ((rightParts[i-1].p2().x(), rightParts[i-1].p2().y()),
                                         (rightParts[i].p1().x(),   rightParts[i].p1().y()),
                                         (segments[i-1].p2().x(),   segments[i-1].p2().y()),
                                         (segments[i].p1().x(),     segments[i].p1().y()),
                                         (md[i-1][1], md[i][0])))
                theMesh.append(((rightParts[i].p1().x(),    rightParts[i].p1().y()),
                                (rightParts[i].p2().x(),    rightParts[i].p2().y()),
                                (segments[i].p1().x(),      segments[i].p1().y()),
                                (segments[i].p2().x(),  segments[i].p2().y()),
                                (md[i][0], md[i][1])))

        return theMesh


        return tmpResult

    def throwOutRings(self, segData, lineData, miterLimit, processUnbounded = True):
        count = len(segData)
        if processUnbounded:
            pt = QPointF()
            bi = QLineF.UnboundedIntersection
            for line1, line2 in zip(segData[:-1], segData[1:]):
                iType = line1.intersect(line2, pt)
                if iType == bi:
                    miter = QLineF(line1.p2(), pt)
                    if miter.length() > miterLimit:
                        miter.setLength(miterLimit)
                    line1.setP2(miter.p2())
                    line2.setP1(miter.p2())

        #Обработать пересечения внутренних областей
        pt = QPointF()
        bi = QLineF.BoundedIntersection
        numIter = 0
        while True:
            foundIntersection = False
            for i, line1 in enumerate(segData):
                p2 = line1.p2()
                for i1, line2 in enumerate(segData[i+1:]):
                    ii = i1 + 1 + i
                    iType = line1.intersect(line2, pt)
                    if iType == bi and pt != p2 and line2.p1() != pt:
                        line1.setP2(pt)
                        line2.setP1(pt)
                        foundIntersection = True

                        if ii-i > 1:
                            for l in xrange(i + 1, ii):
                                segData[l] = QLineF(pt, pt)
                        break
                if foundIntersection:
                    break
            numIter += 1
            if not foundIntersection or numIter > count:
                if numIter > count:
                    print 'limit exided'
                break

        bounded = QLineF.BoundedIntersection

        def diff(p1, p2):
            return abs(p2.x() - p1.x()) > 0.001 or (p2.y() - p1.y()) > 0.001

        #Если последний сегмент имеет пересечение с одним из внутренних
        numIter = 0
        while True:
            foundIntersection = False
            firstI = 2
            for line, seg in zip(lineData[-1::-1], segData[-1::-1]):
                line1_1 = QLineF(line.p1(), seg.p1())
                line1_2 = QLineF(line.p2(), seg.p2())
                lastI = firstI
                i1 = firstI
                for line1,seg1 in zip(lineData[-firstI::-1], segData[-firstI::-1]):
                    line2 = QLineF(line1.p1(), seg1.p1())
                    iType = line1_1.intersect(line2, pt)
                    if (iType == bounded and diff(pt, line1_1.p1()) and diff(pt, line1_1.p2())
                        and diff(pt, line2.p1()) and diff(pt, line2.p2()) ):
                        pt = seg1.p1()
                        seg.setP1(pt)
                        # line1_1.setP2(pt)
                        lastI = i1
                        foundIntersection = True
                        break
                    else:
                        line2 = QLineF(line1.p2(), seg1.p2())
                        iType = line1_2.intersect(line2, pt)
                        if (iType == bounded and diff(pt, line1_2.p1()) and diff(pt, line1_2.p2())
                            and diff(pt, line2.p1()) and diff(pt, line2.p2())):
                            pt = seg1.p2()
                            # line1_1.setP1(pt)
                            seg.setP2(pt)
                            lastI = i1
                            foundIntersection = True
                            break
                    i1 += 1
                if foundIntersection:
                    for l in xrange(firstI, lastI):
                        segData[-l] = QLineF(pt, pt)
                    break

                firstI += 1
            numIter += 1
            if not foundIntersection or numIter > count:
                break




