# -*- coding: utf-8 -*-
#-----------------------------------------------------------
#
# Profile
# Copyright (C) 2013  Peter Wells
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
# with this program; if not, print to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

import qgis
from qgis.PyQt import QtCore
import math

COL_VISIBLE = 0
COL_COLOR = 1
COL_NAME = 2
COL_BAND = 3
COL_BUFFER = 4
COL_LAYER = 5
COL_BACKGROUND = 2
COL_COUNT = 6

def isProfilable(layer):
    """
        Returns True if layer is capable of being profiles,
        else returns False
    """
    if int(QtCore.QT_VERSION_STR[0]) == 4 :    #qgis2
        if int(qgis.utils.QGis.QGIS_VERSION.split('.')[0]) == 2 and int(qgis.utils.QGis.QGIS_VERSION.split('.')[1]) < 18 :
            return    (layer.type() == layer.RasterLayer) or \
                    (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'crayfish_viewer') or \
                    (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'selafin_viewer') 
        elif int(qgis.utils.QGis.QGIS_VERSION.split('.')[0]) == 2 and int(qgis.utils.QGis.QGIS_VERSION.split('.')[1]) >= 18 :
            return    (layer.type() == layer.RasterLayer) or \
                    (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'crayfish_viewer') or \
                    (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'selafin_viewer') or \
                    (layer.type() == layer.VectorLayer and layer.geometryType() == qgis.core.QGis.Point)
    elif int(QtCore.QT_VERSION_STR[0]) == 5 :    #qgis3
        return    (layer.type() == layer.RasterLayer) or \
                (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'crayfish_viewer') or \
                (layer.type() == layer.PluginLayer and layer.LAYER_TYPE == 'selafin_viewer') or \
                (layer.type() == layer.VectorLayer and layer.geometryType() ==  qgis.core.QgsWkbTypes.PointGeometry   )


def getNiceInterval(interval, nextLevel=False, defSteps = []):
    needConvert = False
    if interval < 0:
        needConvert = True
        interval = abs(interval)

    result = interval

    try:
        power = math.floor(math.log10(interval))
        result = math.pow(10, power)
        steps = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10]
        if len(defSteps):
            steps = defSteps

        for step in steps:
            val = step * math.pow(10, power)
            if val > interval:
                if nextLevel:
                    result = val
                break
            result = val
    except:
        pass

    if needConvert:
        return result * -1
    else:
        return result