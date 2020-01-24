# -*- coding: utf-8 -*-

class CornerPointGrid:
    def __init__(self, model_no, nCellsX, nCellsY, nCellsZ):
        self.XCoordLine = None
        self.YCoordLine = None
        self.ZCoordLine = None
        self.nCellsX = nCellsX
        self.nCellsY = nCellsY
        self.nCellsZ = nCellsZ
        self.runSld = 0
        self.model_no = model_no
        self.layerName = 'unknown'
        self.cube = None
        self.cubeMin = -999
        self.cubeMax = -999

        self.activeCells = None

    def getCornerCoordinates(self, i, j, k, di, dj, dk):
        x1 = self.XCoordLine[2*(i+di-1)+2*(self.nCellsX+1)*(j+dj-1)]
        y1 = self.YCoordLine[2*(i+di-1)+2*(self.nCellsX+1)*(j+dj-1)]
        z1 = self.ZCoordLine[2*(i+di-1)+2*(self.nCellsX+1)*(j+dj-1)]
        x2 = self.XCoordLine[2*(i+di-1)+2*(self.nCellsX+1)*(j+dj-1)+1]
        y2 = self.YCoordLine[2*(i+di-1)+2*(self.nCellsX+1)*(j+dj-1)+1]
        z2 = self.ZCoordLine[2*(i+di-1)+2*(self.nCellsX+1)*(j+dj-1)+1]

        offset = 2 * (self.nCellsX + 1) * (self.nCellsY + 1) + 1
        z = self.ZCoordLine[offset + 2 * (i - 1) + 4 * self.nCellsX * (j - 1) +
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