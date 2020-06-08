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
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setGeometry(QtCore.QRect(0, 0, 600, 600))
        self.widget.setObjectName("widget")
        self.addLayerButton = QtWidgets.QPushButton(self.centralwidget)
        self.addLayerButton.setGeometry(QtCore.QRect(760, 330, 113, 32))
        self.addLayerButton.setObjectName("addLayerButton")
        self.textEdit = QtWidgets.QTextEdit(self.centralwidget)
        self.textEdit.setGeometry(QtCore.QRect(610, 340, 141, 31))
        self.textEdit.setLineWidth(2)
        self.textEdit.setObjectName("textEdit")
        self.tableView = QtWidgets.QTableView(self.centralwidget)
        self.tableView.setGeometry(QtCore.QRect(600, 120, 281, 192))
        self.tableView.setLineWidth(2)
        self.tableView.setObjectName("tableView")
        self.tableView.horizontalHeader().setCascadingSectionResizes(True)
        self.tableView.horizontalHeader().setDefaultSectionSize(280)
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(760, 360, 113, 32))
        self.pushButton.setObjectName("pushButton")
        self.savePictureButton = QtWidgets.QPushButton(self.centralwidget)
        self.savePictureButton.setGeometry(QtCore.QRect(750, 460, 140, 35))
        self.savePictureButton.setObjectName("savePictureButton")
        self.fileReadButton = QtWidgets.QPushButton(self.centralwidget)
        self.fileReadButton.setGeometry(QtCore.QRect(750, 420, 140, 35))
        self.fileReadButton.setObjectName("fileReadButton")
        self.colorPickerToolButton = QtWidgets.QToolButton(self.centralwidget)
        self.colorPickerToolButton.setGeometry(QtCore.QRect(810, 530, 71, 22))
        self.colorPickerToolButton.setObjectName("colorPickerToolButton")
        self.selectModeButton = QtWidgets.QPushButton(self.centralwidget)
        self.selectModeButton.setGeometry(QtCore.QRect(610, 70, 121, 41))
        self.selectModeButton.setObjectName("selectModeButton")
        self.displayKneeOperationModeTextLabel = QtWidgets.QLabel(self.centralwidget)
        self.displayKneeOperationModeTextLabel.setGeometry(QtCore.QRect(610, 10, 271, 41))
        self.displayKneeOperationModeTextLabel.setLineWidth(2)
        self.displayKneeOperationModeTextLabel.setTextFormat(QtCore.Qt.PlainText)
        self.displayKneeOperationModeTextLabel.setObjectName("displayKneeOperationModeTextLabel")
        self.readFileNametextEdit = QtWidgets.QTextEdit(self.centralwidget)
        self.readFileNametextEdit.setGeometry(QtCore.QRect(610, 420, 141, 31))
        self.readFileNametextEdit.setLineWidth(2)
        self.readFileNametextEdit.setObjectName("readFileNametextEdit")
        self.saveFileNametextEdit = QtWidgets.QTextEdit(self.centralwidget)
        self.saveFileNametextEdit.setGeometry(QtCore.QRect(610, 460, 141, 31))
        self.saveFileNametextEdit.setLineWidth(2)
        self.saveFileNametextEdit.setObjectName("saveFileNametextEdit")
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
        self.colorPickerToolButton.setText(_translate("MainWindow", "カラーピッカー"))
        self.selectModeButton.setText(_translate("MainWindow", "Mode:0"))
        self.displayKneeOperationModeTextLabel.setText(_translate("MainWindow", "Knee mode: NONE"))

