# -*- coding: utf-8 -*-

# Qt import
from qgis.PyQt import uic, QtCore, QtGui, QtXml

# qgis import
import qgis
from qgis.core import *
from qgis.gui import *
import fnmatch

from .dbReaderBase import *

class ZoneDbReader(DbReaderBase):

    def __init__(self, iface, parent=None):
        DbReaderBase.__init__(self, iface, parent)

    def readZonationByDesc(self, descPattern):
        if not self.initDb():
            return []

        patterns = [x.strip() for x in descPattern.split(',')]

        rows = self.db.execute(self.get_sql('zonation.sql'))
        zonationId = []

        if rows:
            for row in rows:
                val = row[1]
                vals = [val for w in patterns if fnmatch.fnmatch(val, w)]
                if len(vals) > 0:
                    zonationId.append(int(row[0]))
                    break

        return zonationId

    def readZonationList(self, wells):
        if not self.initDb():
            return None

        sql =self.get_sql('wellZonations.sql').format('IN (' + wells + ')')
        rows = self.db.execute(sql)
        zonations = []

        if rows:
            for row in rows:
                zonations.append((row[0], row[1]))

        return zonations

    def readZonationLatestForWell(self, well_sldnid):
        if not self.initDb():
            return []

        rows = self.db.execute(self.get_sql('zonation_latest.sql'), wellId = well_sldnid)
        zonationId = []

        if rows:
            for row in rows:
                zonationId.append(int(row[0]))
                break

        return zonationId

    def readZone(self, well_sldnid, zonationId):
        if not self.initDb() or not zonationId:
            return []

        # print 'to read', zonationId

        zones = []
        for z in zonationId:
            rows = self.db.execute(self.get_sql('zone.sql'), wellId=well_sldnid, zonation_id=z)
            if not rows:
                continue

            for row in rows:
                if row[3] and row[4]:
                    zones.append((row[2], row[3], row[4], row[6]))

        return zones
