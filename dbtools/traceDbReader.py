# -*- coding: utf-8 -*-

# Qt import
from qgis.PyQt import uic, QtCore, QtGui, QtXml

# qgis import
import qgis
from qgis.core import *
from qgis.gui import *
import numpy
from math import sqrt
import itertools

from .dbReaderBase import *
from .mesh import *


class TracesDbReader(DbReaderBase):

    def __init__(self, iface, parent=None):
        DbReaderBase.__init__(self, iface, parent)

    def readTrace(self, traceType, name, status, edited, well_sldnid):
        if not self.initDb():
            return None

        newName = name
        if not len(name):
            name = '%'

        minStatus = status
        maxStatus = status
        if status == 100:
            minStatus = 0

        edMin = edited
        edMax = edited
        if edited == 0: #ignore
            edMax = 10
        elif edited > 1:
            edMin = 0
            edMax = 0

        traces = self.db.execute(self.get_sql('trace.sql'), typeName=traceType, alias=name,
                                 status_min=minStatus, status_max=maxStatus,
                                 wellid=well_sldnid, edited_min=edMin, edited_max=edMax)
        if not traces:
            return None

        traceParts = []

        # print traceType, name, edited

        _max = -999.0
        _min = 1e+20
        logOrLinear = 0 #linear by default
        for row in traces:
            top = float(row[4])
            bot = float(row[5])
            interval = float(row[6])
            _min = float(row[9])
            _max = float(row[10])
            logOrLinear = int(row[11])
            values = numpy.fromstring(self.db.blobToString(row[8]), '>f').astype('d')
            count = len(values)
            if count > 1:
                if interval == 0:
                    depth = numpy.fromstring(self.db.blobToString(row[7]), '>f').astype('d')
                else:
                    step = (bot-top)/(count - 1)
                    depth = [top+i*step for i in xrange(count)]

                logTrace = [pt for pt in zip(depth, values)]
                if len(logTrace):
                    parts = [list(g) for k, g in itertools.groupby(logTrace, lambda x: x[1] <= -999.0) if not k]
                    for l in parts:
                        traceParts.append(l)
                newName = row[12]
            break
        return traceParts, _min, _max, logOrLinear, newName



