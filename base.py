# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'base.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(889, 650)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(600, 410, 291, 101))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalSlider = QtWidgets.QSlider(self.verticalLayoutWidget)
        self.horizontalSlider.setEnabled(True)
        self.horizontalSlider.setMaximumSize(QtCore.QSize(256, 22))
        self.horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.verticalLayout.addWidget(self.horizontalSlider)
        self.horizontalSlider_3 = QtWidgets.QSlider(self.verticalLayoutWidget)
        self.horizontalSlider_3.setEnabled(True)
        self.horizontalSlider_3.setMaximumSize(QtCore.QSize(256, 22))
        self.horizontalSlider_3.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_3.setObjectName("horizontalSlider_3")
        self.verticalLayout.addWidget(self.horizontalSlider_3)
        self.horizontalSlider_2 = QtWidgets.QSlider(self.verticalLayoutWidget)
        self.horizontalSlider_2.setEnabled(True)
        self.horizontalSlider_2.setMaximumSize(QtCore.QSize(256, 22))
        self.horizontalSlider_2.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_2.setObjectName("horizontalSlider_2")
        self.verticalLayout.addWidget(self.horizontalSlider_2)
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setGeometry(QtCore.QRect(0, 0, 600, 600))
        self.widget.setObjectName("widget")
        self.addLayerButton = QtWidgets.QPushButton(self.centralwidget)
        self.addLayerButton.setGeometry(QtCore.QRect(760, 330, 113, 32))
        self.addLayerButton.setObjectName("addLayerButton")
        self.textEdit = QtWidgets.QTextEdit(self.centralwidget)
        self.textEdit.setGeometry(QtCore.QRect(610, 340, 141, 31))
        self.textEdit.setObjectName("textEdit")
        self.tableView = QtWidgets.QTableView(self.centralwidget)
        self.tableView.setGeometry(QtCore.QRect(600, 120, 281, 192))
        self.tableView.setObjectName("tableView")
        self.tableView.horizontalHeader().setCascadingSectionResizes(True)
        self.tableView.horizontalHeader().setDefaultSectionSize(280)
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(760, 360, 113, 32))
        self.pushButton.setObjectName("pushButton")
        self.savePictureButton = QtWidgets.QPushButton(self.centralwidget)
        self.savePictureButton.setGeometry(QtCore.QRect(740, 80, 140, 35))
        self.savePictureButton.setObjectName("savePictureButton")
        self.fileReadButton = QtWidgets.QPushButton(self.centralwidget)
        self.fileReadButton.setGeometry(QtCore.QRect(740, 50, 140, 35))
        self.fileReadButton.setObjectName("fileReadButton")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 889, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.addLayerButton.setText(_translate("MainWindow", "レイヤを追加"))
        self.pushButton.setText(_translate("MainWindow", "PushButton"))
        self.savePictureButton.setText(_translate("MainWindow", "キャンバスを保存"))
        self.fileReadButton.setText(_translate("MainWindow", "ファイルを読込む"))

