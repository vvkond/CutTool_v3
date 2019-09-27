# -*- coding: utf-8 -*-
#-----------------------------------------------------------
#
# Profile
# Copyright (C) 2008  Borys Jurgiel
# Copyright (C) 2012  Patrice Verchere
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
# with this progsram; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#---------------------------------------------------------------------

from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
import qgis
import os


try:
    from qgis.PyQt.QtWidgets import *
except:
    pass


from . import resources
from .tools.profiletool_core import ProfileToolCore

class CutPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.profiletool = None
        self.dockOpened = False        #remember for not reopening dock if there's already one opened
        #self.wdg = None
        #self.tool = None
        #self.lastFreeHandPoints = []

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CutTool_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.canvas.mapToolSet.connect(self.mapToolChanged)


    def initGui(self):
        # create action
        self.action = QAction(QIcon(":/plugins/CutTool/icons/24x24_CrossSection.png"), self.tr("Geology cut"), self.iface.mainWindow())
        self.action.setWhatsThis("Plots geology cut")
        self.action.triggered.connect(self.run)
        self.aboutAction = QAction("About", self.iface.mainWindow())
        self.aboutAction.triggered.connect(self.about)
        # add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Geology cut Tool", self.action)
        self.iface.addPluginToMenu("&Geology cut Tool", self.aboutAction)

        QObject.connect(self.iface, SIGNAL("projectRead()"), self.onProjectLoaded)
        QObject.connect(QgsProject.instance(), SIGNAL("writeProject(QDomDocument &)"), self.onWriteProject)

    def tr(self, message):
        return QCoreApplication.translate('CutTools', message)


    def unload(self):
        try:
            self.profiletool.dockwidget.close()
        except:
            pass

        try:
            self.canvas.mapToolSet.disconnect(self.mapToolChanged)
        except:
            pass

        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&Geology cut Tool", self.action)
        self.iface.removePluginMenu("&Geology cut Tool", self.aboutAction)


    def run(self):

        if not self.dockOpened:
            #if self.profiletool is None:
            self.profiletool = ProfileToolCore(self.iface,self)
            self.iface.addDockWidget(self.profiletool.dockwidget.location, self.profiletool.dockwidget)
            self.profiletool.dockwidget.closed.connect(self.cleaning)
            self.dockOpened = True
            self.profiletool.activateProfileMapTool()
            self.profiletool.restoreSelectedLayers()
        else:
            self.profiletool.activateProfileMapTool()


    def cleaning(self):
        self.dockOpened = False
        self.profiletool.cleaning()
        if self.profiletool.toolrenderer:
            self.canvas.unsetMapTool(self.profiletool.toolrenderer.tool)
        self.canvas.setMapTool(self.profiletool.saveTool)
        self.iface.mainWindow().statusBar().showMessage( "" )

    def mapToolChanged(self,newtool,oldtool = None):
        pass
        #print('maptoolchanged',newtool,oldtool)

    def about(self):
        from ui.dlgabout import DlgAbout
        DlgAbout(self.iface.mainWindow()).exec_()

    def onProjectLoaded(self):
        print 'Project read'

    def onWriteProject(self, domproject):
        print 'Write project'