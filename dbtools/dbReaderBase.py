# -*- coding: utf-8 -*-

#Qt import
from qgis.PyQt import uic, QtCore, QtGui, QtXml

#qgis import
import qgis
from qgis.core import *
from qgis.gui import *

import os
from .connections import create_connection
from .tig_projection import *

class DbReaderBase(QtCore.QObject):

    def __init__(self, iface, parent = None):
        QtCore.QObject.__init__(self, parent)

        self.iface = iface
        self.project = QtCore.QSettings().value('currentProject')
        self.plugin_dir = os.path.dirname(__file__)

        self.db = None
        self.tig_projections = None


    def initDb(self):
        if self.project is None:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                self.tr(u'No current PDS project'), level=QgsMessageBar.CRITICAL)

            return False

        connection = create_connection(self.project)
        scheme = self.project['project']
        try:
            self.db = connection.get_db(scheme)
            self.tig_projections = TigProjections(db=self.db)
            proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
            if proj is not None:
                self.proj4String = 'PROJ4:' + proj.qgis_string
                destSrc = QgsCoordinateReferenceSystem()
                destSrc.createFromProj4(proj.qgis_string)
                sourceCrs = QgsCoordinateReferenceSystem('epsg:4326')
                self.xform = QgsCoordinateTransform(sourceCrs, destSrc)

                screenCrs = QgsCoordinateReferenceSystem(qgis.utils.iface.mapCanvas().mapSettings().destinationCrs())
                self.screenXform = QgsCoordinateTransform(screenCrs, destSrc)
                self.screenXformref = QgsCoordinateTransform(destSrc, screenCrs)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Project projection read error {0}: {1}').format(
                                                    scheme, str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return False
        return True

    def get_sql(self, value):
        sql_file_path = os.path.join(self.plugin_dir, value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')