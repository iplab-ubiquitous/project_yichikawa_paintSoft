# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'colorpicker.ui'
#
# Created by: PyQt5 UI code generator 5.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(200, 400)
        self.verticalLayoutWidget = QtWidgets.QWidget(Form)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(20, 30, 160, 201))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.hueLabel = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.hueLabel.setObjectName("hueLabel")
        self.verticalLayout.addWidget(self.hueLabel)
        self.hueSlider = QtWidgets.QSlider(self.verticalLayoutWidget)
        self.hueSlider.setOrientation(QtCore.Qt.Horizontal)
        self.hueSlider.setObjectName("hueSlider")
        self.verticalLayout.addWidget(self.hueSlider)
        self.saturationLabel = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.saturationLabel.setObjectName("saturationLabel")
        self.verticalLayout.addWidget(self.saturationLabel)
        self.saturationSlider = QtWidgets.QSlider(self.verticalLayoutWidget)
        self.saturationSlider.setOrientation(QtCore.Qt.Horizontal)
        self.saturationSlider.setObjectName("saturationSlider")
        self.verticalLayout.addWidget(self.saturationSlider)
        self.valueLabel = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.valueLabel.setObjectName("valueLabel")
        self.verticalLayout.addWidget(self.valueLabel)
        self.valueSlider = QtWidgets.QSlider(self.verticalLayoutWidget)
        self.valueSlider.setOrientation(QtCore.Qt.Horizontal)
        self.valueSlider.setObjectName("valueSlider")
        self.verticalLayout.addWidget(self.valueSlider)
        self.cancelButton = QtWidgets.QPushButton(Form)
        self.cancelButton.setGeometry(QtCore.QRect(10, 300, 81, 32))
        self.cancelButton.setObjectName("cancelButton")
        self.OKButton = QtWidgets.QPushButton(Form)
        self.OKButton.setGeometry(QtCore.QRect(100, 300, 81, 32))
        self.OKButton.setObjectName("OKButton")

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.hueLabel.setText(_translate("Form", "Hue: 0"))
        self.saturationLabel.setText(_translate("Form", "Saturation: 0"))
        self.valueLabel.setText(_translate("Form", "Brightness: 0"))
        self.cancelButton.setText(_translate("Form", "Cancel"))
        self.OKButton.setText(_translate("Form", "OK"))

