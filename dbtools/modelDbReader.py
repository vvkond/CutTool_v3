# -*- coding: utf-8 -*-

#Qt import
from qgis.PyQt import QtCore

#qgis import
import qgis
import numpy

from .dbReaderBase import *


class ModelDbReader(DbReaderBase):

    ZONATION_LATEST = 3000
    ZONATION_MATCH = 3001
    ZONATION_SELECT_WHEN_LOADING = 3003

    def __init__(self, iface, parent = None):
        DbReaderBase.__init__(self, iface, parent)

    def readModelList(self):
        if not self.initDb():
            return None

        models = []
        sql = 'select tig_simultn_model_no, tig_description from TIG_SIM_MODEL'
        records = self.db.execute(sql)
        if records:
            for input_row in records:
                models.append((input_row[0], input_row[1]))
        return models

    def readModelDef(self, defSld, nCelsX, nCelsY, nCelsZ):
        sql = 'select * from tig_sim_grid_defn where '

    def readModel(self, modelId):
        if not self.initDb():
            return None

        sql = 'select tig_simultn_model_no, tig_model_def_sldnid, tig_radial_geometry, tig_geometry_type, ' \
              'tig_cells_in_x_or_r_dir, tig_cells_in_y_or_0_dir, tig_cells_in_z_dir ' \
              'from TIG_SIM_MODEL where tig_simultn_model_no = ' + str(modelId)
        records = self.db.execute(sql)
        if records:
            for input_row in records:
                defSld = input_row[1]
                nCelsX = input_row[4]
                nCelsY = input_row[5]
                nCelsZ = input_row[6]

        return None