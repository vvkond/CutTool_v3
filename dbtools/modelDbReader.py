# -*- coding: utf-8 -*-

#Qt import
from qgis.PyQt import QtCore

#qgis import
import qgis
import numpy
from .dbReaderBase import *
from .CornerPointGrid import *

CORNER_POINT = 2
FULL_CORNER_POINT = 4
CARTESIAN = 0

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
                gridSld = input_row[1]
                geometryType = input_row[2]
                nCellsX = input_row[4]
                nCellsY = input_row[5]
                nCellsZ = input_row[6]

                coordLinesCount = 2 * (nCellsX + 1) * (nCellsY + 1)
                cornerPointsCount = 8 * nCellsX * nCellsY * nCellsZ
                nBlocks = (nCellsX + 1) * (nCellsY + 1) * (nCellsZ + 1)

                sql = 'select tig_cell_x_map_coord, tig_cell_y_map_coord, tig_cell_z_map_coord from tig_sim_grid_defn ' \
                      'where db_sldnid = ' + str(gridSld)

                grid_records = self.db.execute(sql)
                for row in grid_records:
                    if geometryType == CARTESIAN:
                        grid = CartesianGrid(modelId, nCellsX, nCellsY, nCellsZ)

                        grid.XCoordLine = numpy.fromstring(self.db.blobToString(row[0]), '>f').astype('d')
                        grid.YCoordLine = numpy.fromstring(self.db.blobToString(row[1]), '>f').astype('d')
                        grid.ZCoordLine = numpy.fromstring(self.db.blobToString(row[2]), '>f').astype('d')
                        if (len(grid.XCoordLine) != nBlocks
                                or len(grid.YCoordLine) != nBlocks
                                or len(grid.ZCoordLine) != nBlocks):
                            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                                self.tr(
                                                                    u'Не верный формат модели: ' + str(geometryType)),
                                                                level=Qgis.Critical)
                            break
                        return grid

                    elif geometryType == CORNER_POINT or geometryType == FULL_CORNER_POINT:
                        grid = CornerPointGrid(modelId, nCellsX, nCellsY, nCellsZ)

                        grid.XCoordLine = numpy.fromstring(self.db.blobToString(row[0]), '>f').astype('d')
                        grid.YCoordLine = numpy.fromstring(self.db.blobToString(row[1]), '>f').astype('d')
                        grid.ZCoordLine = numpy.fromstring(self.db.blobToString(row[2]), '>f').astype('d')
                        if (len(grid.XCoordLine) != coordLinesCount
                                or len(grid.YCoordLine) != coordLinesCount
                                or len(grid.ZCoordLine) != coordLinesCount + cornerPointsCount):
                            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                                self.tr(u'Не верный формат модели: '+str(geometryType)),
                                                                level=Qgis.Critical)
                            break

                        if self.screenXform:
                            for i in range(len(grid.XCoordLine)):
                                pt1 = QgsPointXY(grid.XCoordLine[i], grid.YCoordLine[i])
                                pt1 = self.screenXform.transform(pt1)
                                grid.XCoordLine[i] = pt1.x()
                                grid.YCoordLine[i] = pt1.y()

                        return grid

        return None

    def readPropertyCube(self, grid, simLink):
        sql = 'select ' + simLink.simFldnam + ' from ' + simLink.simSldnam + ' where tig_simultn_model_no=' + str(
            grid.model_no)
        records = self.db.execute(sql)
        if records:
            for row in records:
                grid.cube = numpy.fromstring(self.db.blobToString(row[0]), '>f').astype('d')
                if len(grid.cube) > 0:
                    grid.cubeMin = numpy.amin(grid.cube)
                    grid.cubeMax = numpy.amax(grid.cube)
                break
