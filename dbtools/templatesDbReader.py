# -*- coding: utf-8 -*-

#Qt import
from qgis.PyQt import uic, QtCore, QtGui, QtXml

#qgis import
import qgis
from qgis.core import *
from qgis.gui import *
import numpy
from math import sqrt

from .dbReaderBase import *


class TemplatesDbReader(DbReaderBase):

    ZONATION_LATEST = 3000
    ZONATION_MATCH = 3001
    ZONATION_SELECT_WHEN_LOADING = 3003

    def __init__(self, iface, parent = None):
        DbReaderBase.__init__(self, iface, parent)

    def readTemplates(self):
        if not self.initDb():
            return None

        records = self._readTemplates()
        templates = []
        if not records:
            return []

        for input_row in records:
            row = {}

            row['sldnid'] = int(input_row[0])
            row['description'] = input_row[1]
            row['app'] = input_row[2]
            row['login'] = input_row[3]
            row['date'] = QtCore.QDateTime.fromTime_t(0).addSecs(int(input_row[4]))

            templates.append(row)

        return templates

    def loadTemplate(self, sldnid):
        if not self.initDb():
            return None

        sql = 'select DB_SLDNID, TIG_TEMPLATE_DATA from tig_template where DB_SLDNID = ' + str(sldnid)
        records = self.db.execute(sql)
        if records:
            for input_row in records:
                if input_row[1]:
                    return self.parceCLob(self.db.blobToString(input_row[1]))
        return None

    def _readTemplates(self):
        try:
            return self.db.execute(self.get_sql('template.sql'), app_name='tmpltA')

        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), str(e), level=QgsMessageBar.CRITICAL)
            return None

    def parceCLob(self, strToParce):
        #3-black
        #4-серый
        #1428716544 - fixed
        tracks = []
        # try:

        doc = QtXml.QDomDocument()
        if doc.setContent(strToParce):
            # print doc.toString()
            root = doc.documentElement()

            #Треки
            daks = root.elementsByTagName('GPT_DAK')
            if daks:
                for i in xrange(daks.count()):
                    track = {}

                    item = daks.at(i).toElement()
                    if item.hasAttribute('Name'):
                        track['name'] = item.attribute('Name')
                    else:
                        track['name'] = ''

                    twds = item.elementsByTagName('GPA_TWD')
                    if twds:
                        for ii in xrange(twds.count()):
                            twd = twds.at(ii).toElement()
                            if twd.hasAttribute('Normalized'):
                                track['width'] = float(twd.attribute('Normalized'))

                    #Кривые
                    trcs = item.elementsByTagName('GPT_TRC')
                    if trcs:
                        traces = []
                        for ii in xrange(trcs.count()):
                            trc = trcs.at(ii).toElement()
                            trace = {}
                            if trc.hasAttribute('Name'):
                                trace['name'] = trc.attribute('Name')
                            if trc.hasAttribute('TraceType'):
                                trace['type'] = trc.attribute('TraceType')
                            if trc.hasAttribute('Alias'):
                                trace['alias'] = trc.attribute('Alias')
                            if trc.hasAttribute('Merged'):
                                trace['merged'] = int(trc.attribute('Merged'))
                            if trc.hasAttribute('Status'):
                                trace['status'] = int(trc.attribute('Status'))
                            if trc.hasAttribute('Edited'):
                                trace['edited'] = int(trc.attribute('Edited'))

                            #Масштабы кривой
                            items = trc.elementsByTagName('GPA_HSC')
                            if items:
                                for jj in xrange(items.count()):
                                    item = items.at(jj).toElement()
                                    if item.hasAttribute('ScaleType'):
                                        trace['scaleType'] = int(item.attribute('ScaleType')) - 1
                                    if item.hasAttribute('Min'):
                                        trace['min'] = float(item.attribute('Min'))
                                    if item.hasAttribute('Max'):
                                        trace['max'] = float(item.attribute('Max'))

                            #Стиль отрисовки кривой
                            items = trc.elementsByTagName('GPA_GFN')
                            if items:
                                for jj in xrange(items.count()):
                                    item = items.at(jj).toElement()
                                    if item.hasAttribute('Colour'):
                                        trace['color'] = int(item.attribute('Colour'))
                                    if item.hasAttribute('LineWidth'):
                                        trace['LineWidth'] = float(item.attribute('LineWidth'))
                                    if item.hasAttribute('LineStyle'):
                                        trace['LineStyle'] = int(item.attribute('LineStyle'))

                            traces.append(trace)

                        if len(traces):
                            track['traces'] = traces

                    #Zonations
                    zons = item.elementsByTagName('GPT_ZON')
                    if zons:
                        zonations = []
                        for ii in xrange(zons.count()):
                            zn = zons.at(ii).toElement()
                            zone = {}
                            if zn.hasAttribute('Type'):
                                zone['Type'] = zn.attribute('Type')
                            if zn.hasAttribute('Name'):
                                zone['Name'] = zn.attribute('Name')
                            if zn.hasAttribute('ZonSLD'):
                                zone['ZonSLD'] = [int(zn.attribute('ZonSLD'))]
                            if zn.hasAttribute('SelectMode'):
                                sm = int(zn.attribute('SelectMode'))
                                zone['SelectMode'] = sm
                                if sm == TemplatesDbReader.ZONATION_SELECT_WHEN_LOADING \
                                        or sm == TemplatesDbReader.ZONATION_MATCH:
                                    #Select when loading or Match pattern
                                    zone['ZonSLD'] = []
                            if zn.hasAttribute('DescPattern'):
                                zone['DescPattern'] = zn.attribute('DescPattern')

                            zonations.append(zone)

                        if len(zonations):
                            track['zonations'] = zonations

                    tracks.append(track)

            # print tracks

        # except Exception as e:
        #     QgsMessageLog.logMessage('CLOB: ' + str(e), 'CutTool')

        return tracks