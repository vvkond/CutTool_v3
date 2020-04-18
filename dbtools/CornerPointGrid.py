# -*- coding: utf-8 -*-

import ctypes
from ctypes import *
import platform
from os import environ,path
from os.path import abspath
import numpy as np
import sys

try:
    if platform.architecture()[0] == "64bit":
        libFolder = path.dirname(path.abspath(__file__))+'\\libs\\x86_64'
        #libFolder='C:/MyProg/OISTerra_Project/debug/win64'
    else:
        libFolder = path.dirname(path.abspath(__file__)) + '\\libs\\i386'

    cdll.LoadLibrary(libFolder + '\\DataCore.dll')
    cdll.LoadLibrary(libFolder + '\\MathCore.dll')
    cutDll = cdll.LoadLibrary(libFolder + '\\QgisCrossSection.dll')
    print('QgisCrossSection.dll loaded')
except Exception as e:
    print(libFolder+'\\QgisCrossSection.dll load error', str(e))

CMPFUNC = CFUNCTYPE(c_int, c_int, c_int, c_int, c_int, POINTER(c_double))
SIM_INDT = -999

class CornerPointGrid:
    def __init__(self, model_no, nCellsX, nCellsY, nCellsZ):
        self.XCoordLine = None
        self.YCoordLine = None
        self.ZCoordLine = None
        self.nCellsX = nCellsX
        self.nCellsY = nCellsY
        self.nCellsZ = nCellsZ
        self.offset = 2 * (self.nCellsX + 1) * (self.nCellsY + 1) #+ 1
        self.runSld = 0
        self.model_no = model_no
        self.layerName = 'unknown'
        self.cube = None
        self.cubeMin = -999
        self.cubeMax = -999

        self.activeCells = None

    def getCornerCoordinates(self, i, j, k, di, dj, dk):
        index = 2*(i+di-1)+2*(self.nCellsX+1)*(j+dj-1)
        index1 = index + 1
        x1 = self.XCoordLine[index]
        y1 = self.YCoordLine[index]
        z1 = self.ZCoordLine[index]
        x2 = self.XCoordLine[index1]
        y2 = self.YCoordLine[index1]
        z2 = self.ZCoordLine[index1]

        z = self.ZCoordLine[self.offset + 2 * (i - 1) + 4 * self.nCellsX * (j - 1) +
                            8 * self.nCellsX * self.nCellsY * (k - 1) +
                            4 * self.nCellsX * self.nCellsY * dk +
                            2 * self.nCellsX * dj + di]

        a = (z-z1)/(z2-z1)
        x = x1+a*(x2-x1)
        y = y1+a*(y2-y1)
        return (x, y, z)

    def getCornerX(self, i, j, k, di, dj, dk):
        x,y,z = self.getCornerCoordinates(i,j,k,di,dj,dk)
        return x

    def getCornerY(self, i, j, k, di, dj, dk):
        x,y,z = self.getCornerCoordinates(i,j,k,di,dj,dk)
        return y


    def getCornerZ(self, i, j, k, di, dj, dk):
        x,y,z = self.getCornerCoordinates(i,j,k,di,dj,dk)
        return z

    def getLeftBackUpperCorner(self, i, j, k):
        return self.getCornerCoordinates(i, j, k, 0, 0, 0)

    def getRightBackUpperCorner(self, i, j, k):
        return self.getCornerCoordinates(i, j, k, 1, 0, 0)

    def getLeftFrontUpperCorner(self, i, j, k):
        return self.getCornerCoordinates(i, j, k, 0, 1, 0)

    def getRightFrontUpperCorner(self, i, j, k):
        return self.getCornerCoordinates(i, j, k, 1, 1, 0)

    def getLeftBackUpperCornerX(self, i, j, k):
        return self.getCornerX(i, j, k, 0, 0, 0)

    def getLeftBackUpperCornerY(self, i, j, k):
        return self.getCornerY(i, j, k, 0, 0, 0)

    def getLeftBackUpperCornerZ(self, i, j, k):
        return self.getCornerZ(i, j, k, 0, 0, 0)

    def getRightBackUpperCornerX(self, i, j, k):
        return self.getCornerX(i, j, k, 1, 0, 0)

    def getRightBackUpperCornerY(self, i, j, k):
        return self.getCornerY(i, j, k, 1, 0, 0)

    def getRightBackUpperCornerZ(self, i, j, k):
        return self.getCornerZ(i, j, k, 1, 0, 0)

    def getLeftFrontUpperCornerX(self, i, j, k):
        return self.getCornerX(i, j, k, 0, 1, 0)

    def getLeftFrontUpperCornerY(self, i, j, k):
        return self.getCornerY(i, j, k, 0, 1, 0)

    def getLeftFrontUpperCornerZ(self, i, j, k):
        return self.getCornerZ(i, j, k, 0, 1, 0)

    def getRightFrontUpperCornerX(self, i, j, k):
        return self.getCornerX(i, j, k, 1, 1, 0)

    def getRightFrontUpperCornerY(self, i, j, k):
        return self.getCornerY(i, j, k, 1, 1, 0)

    def getRightFrontUpperCornerZ(self, i, j, k):
        return self.getCornerZ(i, j, k, 1, 1, 0)

    def getLeftBackLowerCornerX(self, i, j, k):
        return self.getCornerX(i, j, k, 0, 0, 1)

    def getLeftBackLowerCornerY(self, i, j, k):
        return self.getCornerY(i, j, k, 0, 0, 1)

    def getLeftBackLowerCornerZ(self, i, j, k):
        return self.getCornerZ(i, j, k, 0, 0, 1)

    def getRightBackLowerCornerX(self, i, j, k):
        return self.getCornerX(i, j, k, 1, 0, 1)

    def getRightBackLowerCornerY(self, i, j, k):
        return self.getCornerY(i, j, k, 1, 0, 1)

    def getRightBackLowerCornerZ(self, i, j, k):
        return self.getCornerZ(i, j, k, 1, 0, 1)

    def getLeftFrontLowerCornerX(self, i, j, k):
        return self.getCornerX(i, j, k, 0, 1, 1)

    def getLeftFrontLowerCornerY(self, i, j, k):
        return self.getCornerY(i, j, k, 0, 1, 1)

    def getLeftFrontLowerCornerZ(self, i, j, k):
        return self.getCornerZ(i, j, k, 0, 1, 1)

    def getRightFrontLowerCornerX(self, i, j, k):
        return self.getCornerX(i, j, k, 1, 1, 1)

    def getRightFrontLowerCornerY(self, i, j, k):
        return self.getCornerY(i, j, k, 1, 1, 1)

    def getRightFrontLowerCornerZ(self, i, j, k):
        return self.getCornerZ(i, j, k, 1, 1, 1)

    def getPolygon(self, i, j, layer):
        x1 = self.getLeftBackUpperCornerX(i, j, layer)
        y1 = self.getLeftBackUpperCornerY(i, j, layer)
        z1 = self.getLeftBackUpperCornerZ(i, j, layer)

        x2 = self.getRightBackUpperCornerX(i, j, layer)
        y2 = self.getRightBackUpperCornerY(i, j, layer)
        z2 = self.getRightBackUpperCornerZ(i, j, layer)

        x3 = self.getRightFrontUpperCornerX(i, j, layer)
        y3 = self.getRightFrontUpperCornerY(i, j, layer)
        z3 = self.getRightFrontUpperCornerZ(i, j, layer)

        x4 = self.getLeftFrontUpperCornerX(i, j, layer)
        y4 = self.getLeftFrontUpperCornerY(i, j, layer)
        z4 = self.getLeftFrontUpperCornerZ(i, j, layer)

        return (x1,y1,z1, x2,y2,z2, x3,y3,z3, x4,y4,z4)

    def getPolygon1(self, i, j, layer):
        x1, y1, z1 = self.getLeftBackUpperCorner(i, j, layer)
        x2, y2, z2 = self.getRightBackUpperCorner(i, j, layer)
        x3, y3, z3 = self.getRightFrontUpperCorner(i, j, layer)
        x4, y4, z4 = self.getLeftFrontUpperCorner(i, j, layer)

        return (x1,y1,z1, x2,y2,z2, x3,y3,z3, x4,y4,z4)

    def py_cmp_func(self, i, j, k, count, b):
        p = [b[i] for i in range(0,count)]
        self.points.append([ i for i in zip(p[::2], p[1::2])])

        z = SIM_INDT
        cellIndex = self.nCellsX * self.nCellsY * k + self.nCellsX * j + i
        if self.cube is not None and len(self.cube) > cellIndex :
            z = self.cube[cellIndex]
        self.values.append(z)
        return 0

    def createCut(self, profile):
        npProfile = np.array(profile).flatten()

        callback = CMPFUNC(self.py_cmp_func)

        self.points = []
        self.values = []
        cutDll.setModelData(self.XCoordLine.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                            self.YCoordLine.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                            self.ZCoordLine.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                            npProfile.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                            len(npProfile),
                            self.nCellsX, self.nCellsY, self.nCellsZ,
                            callback)

        return self.points, self.values