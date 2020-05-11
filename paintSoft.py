import sys, math, serial
from PyQt5.QtCore import Qt, QPoint, QPointF, QRect, QSize, QMetaObject, QCoreApplication, QAbstractTableModel, \
    QModelIndex, QTimer, QThread, QObject, pyqtSignal
from PyQt5.QtGui import QPainter, QPainterPath, QPolygon, QMouseEvent, QImage, qRgb, QPalette, QColor, QPaintEvent, \
    QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QSlider, QTableView, QMenuBar, QStatusBar, \
    QPushButton, QTextEdit, QAbstractItemView, QFileDialog, QLabel, QToolButton, QColorDialog
import PyQt5.sip
import numpy as np
from enum import Enum


NUM_OF_SENSORS = 10
WAITING_FRAMES = 100
ALPHA_EMA = 0.7



class KneeControlMode(Enum):
    NONE = 0
    COLOR_PICKER = 1

class KneePosition(QObject):

    def __init__(self, usbSerialCommunication, parent=None):
        super().__init__(parent)
        self.distanceSensorArray = usbSerialCommunication
        # self.distanceSensorArray = serial.Serial('/dev/cu.usbmodem141201', 460800)
        for i in range(10):
            self.distanceSensorArray.readline()  # 読み飛ばし(欠けたデータが読み込まれるのを避ける)

        #（仮の）膝の座標値
        self.oldX = 0
        self.oldY = 0

        # キャリブレーションの記録
        self.kneePosXMinumum = 2
        self.kneePosXCenter = 4
        self.kneePosXMaximum = 6
        self.kneePosYMinimum = 46
        self.kneePosYCenter = 48
        self.neePosYMaximum = 53

        #膝検出・位置計算用
        self.sensor_val = np.zeros(NUM_OF_SENSORS, dtype=np.float)
        self.weight = ([1.00] * NUM_OF_SENSORS)
        self.val = np.zeros((WAITING_FRAMES, NUM_OF_SENSORS), dtype=np.float)
        self.leg_flag = False
        self.sensor_flt = np.zeros((WAITING_FRAMES,NUM_OF_SENSORS),dtype=np.float)

    def setCalibrateValues(self, calibratedCenterX, calibratedCenterY):
        self.kneePosXCenter  = calibratedCenterX
        self.kneePosXMaximum = calibratedCenterX + 2
        self.kneePosXMinumum = calibratedCenterX - 2

        self.kneePosYCenter  = calibratedCenterY
        self.kneePosYMaximum = calibratedCenterY + 4
        self.kneePosYMinumum = calibratedCenterY - 2


    def getDistance(self):
        distances = float(0)
        while self.distanceSensorArray.in_waiting > 1 or distances == float(0):
            distances = self.distanceSensorArray.readline().strip().decode("utf-8").split(',')

        return distances

    def getMappedValue(self, val, in_min, in_max, out_min, out_max):
        return (val - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def getMappedPositions8bit(self, x, y):
        x = self.getMappedValue(x, self.kneePosXMinumum, self.kneePosXMaximum, 0, 255)
        if x > 255: x = 255
        elif x < 0: x = 0

        if y < self.kneePosYCenter:
            y = self.getMappedValue(y, self.kneePosYMinimum, self.kneePosYCenter, 0, 127)
        else:
            y = self.getMappedValue(y, self.kneePosYCenter, self.kneePosYMaximum, 127, 255)


        if y > 255: y = 255
        elif y < 0: y = 0

        return x, y


    def getPosition(self):
        weight = ([1.00] * NUM_OF_SENSORS)

        sensorValues = self.getDistance()
        sensorValues = [64-float(v) for v in sensorValues] # 計算を容易にするため膝との距離を反転（要らないかもしれない）

        maxDistance = np.max(sensorValues)

        newY = maxDistance

        for i in range(NUM_OF_SENSORS):
            weight[i] = 1 / (maxDistance - sensorValues[i] + 2)
        weightSum = np.sum(weight)

        newX = 0

        for i in range(NUM_OF_SENSORS):

            newX += (i * weight[i] / weightSum)

        newX = (newX - self.oldX) * ALPHA_EMA + self.oldX
        self.oldX = newX

        newY = (newY - self.oldY) * ALPHA_EMA + self.oldY
        self.oldY = newY

        return newX, newY


# 任意の点を通る曲線を描くためのパスを作る
class RoundedPolygon(QPolygon):
    def __init__(self, iRadius: int, parent=None):
        self.mPath = QPainterPath()
        self.iRadius = iRadius

    def setRadius(self, iRadius: int):
        self.iRadius = iRadius

    def getDistance(self, pt1: QPoint, pt2: QPoint) -> float:
        return math.sqrt((pt1.x() - pt2.x()) * (pt1.x() - pt2.x()) +
                         (pt1.y() - pt2.y()) * (pt1.y() - pt2.y()))

    def getLineStart(self, index: int) -> QPointF:
        pt = QPointF()
        pt1 = self.clickedPoints[index]
        pt2 = self.clickedPoints[(index + 1) %
                                 len(self.clickedPoints)]
        if self.getDistance(pt1, pt2) == 0:
            fRat = 0.5
        else:
            fRat = float(self.iRadius) / self.getDistance(pt1, pt2)
            if fRat > 0.5:
                fRat = 0.5

        pt.setX((1.0 - fRat) * pt1.x() + fRat * pt2.x())
        pt.setY((1.0 - fRat) * pt1.y() + fRat * pt2.y())
        return pt

    def getLineEnd(self, index: int) -> QPointF:
        pt = QPointF()
        pt1 = self.clickedPoints[index]
        pt2 = self.clickedPoints[(index + 1) %
                                 len(self.clickedPoints)]
        # pt2 = self.clickedPoints[index+1]
        if self.getDistance(pt1, pt2) == 0:
            fRat = 0.5
        else:
            fRat = float(self.iRadius) / self.getDistance(pt1, pt2)
            if fRat > 0.5:
                fRat = 0.5

        pt.setX(fRat * pt1.x() + (1.0 - fRat) * pt2.x())
        pt.setY(fRat * pt1.y() + (1.0 - fRat) * pt2.y())
        return pt

    def getPath(self, clickedPoints) -> QPainterPath:
        mPath = QPainterPath()
        self.clickedPoints = clickedPoints

        if len(self.clickedPoints) < 3:
            print("still have 2 points or less.")
            return mPath

        pt1 = QPointF()
        pt2 = QPointF()

        for i in range(len(self.clickedPoints) - 1):
            pt1 = self.getLineStart(i)

            if i == 0:
                mPath.moveTo(pt1)
            else:
                mPath.quadTo(clickedPoints[i], pt1)

            # pt2 = self.getLineEnd(i)
            # mPath.lineTo(pt2)

        # pt1 = self.getLineStart(0)
        # mPath.quadTo(clickedPoints[0], pt1)

        return mPath

class CanvasNameTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvasName: List[str] = ["canvas[0]"]

    def rowCount(self, parent=None):
        return len(self.canvasName)

    def columnCount(self, parent=None):
        return 1

    def data(self, index: QModelIndex, role: int):
        if role == Qt.DisplayRole:
            return self.canvasName[index.row()]

    def headerData(self, section: int, orientation: int, role: int):
        if role == Qt.DisplayRole & orientation == Qt.Horizontal:
            return "CanvasName"
        else:
            return ""

    def addCanvas(self, canvasName: str):
        self.canvasName.append(canvasName)

    def deleteLastCanvas(self):
        self.canvasName.pop()

class Canvas(QWidget):
    def __init__(self, parent=None):
        super(Canvas, self).__init__(parent)

        # 画像専用のレイヤであるかを制御する
        # 1度Trueになったら2度とFalseにならないことを意図する
        self.isPictureCanvas = False
        self.pictureFileName = ""

        # self.setGeometry(300, 50, 300, 300)
        # self.setWindowTitle("Canvas")
        self.setMouseTracking(True)

        # マウス移動で出る予測線とクリックして出る本線を描画するときに区別する
        self.isLinePrediction = False

        self.roundedPolygon = RoundedPolygon(10000)

        self.existingPaths = []
        self.clickedPoints = []

        self.show()

    def mousePressEvent(self, event: QMouseEvent):

        # 制御点の追加
        if event.button() == Qt.LeftButton:
            print("Clicked")
            self.clickedPoints.append(event.pos())
            # print(self.clickedPoints)

        # 直前の制御点の消去
        if event.button() == Qt.RightButton:
            self.clickedPoints.pop()
        self.update()


    def mouseMoveEvent(self, event: QMouseEvent):
        self.clickedPoints.append(event.pos())
        self.isLinePrediction = True
        self.update()


    def fixPath(self):
        # パスを確定
        if self.isLinePrediction:
            self.clickedPoints.pop()
        # クリックした点まで線を伸ばすため、終点をリストに入れている
        if len(self.clickedPoints) > 0:
            self.clickedPoints.append(self.clickedPoints[len(self.clickedPoints) - 1])
            painterPath = self.roundedPolygon.getPath(self.clickedPoints)
            self.existingPaths.append(painterPath)
            self.clickedPoints = []
            self.update()

    def deleteLastPath(self):
        if len(self.existingPaths) > 0:
            self.existingPaths.pop()
            self.update()

    def setPictureFileName(self, pictureFileName: str):
        self.isPictureCanvas = True
        self.pictureFileName = pictureFileName
        self.update()


    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)

        if self.isPictureCanvas:
            self.setAutoFillBackground(False)
            image = QPixmap(self.pictureFileName)
            size  = image.size()
            offsetX = 0
            offsetY = 0

            if size.width() < 300:
                offsetX = size.width() / 2

            if size.height() < 300:
                offsetY = size.height() / 2

            self.setWindowFlags(Qt.Window)
            label = QLabel(self)
            label.setPixmap(image)
            label.show()


        else:
            painter.setPen(Qt.black)
            # すでに確定されているパスの描画
            if len(self.existingPaths) > 0:
                for path in self.existingPaths:
                    painter.drawPath(path)


            #　現在描いているパスの描画
            if len(self.clickedPoints) > 3:
                # print(self.clickedPoints)
                # クリックした点まで線を伸ばすため、終点を一時的にリストに入れている
                self.clickedPoints.append(self.clickedPoints[len(self.clickedPoints) - 1])
                painterPath = self.roundedPolygon.getPath(self.clickedPoints)

                for i in range(len(self.clickedPoints)):
                    painter.drawEllipse(self.clickedPoints[i], 1, 1)

                if self.isLinePrediction:
                    self.clickedPoints.pop()
                    self.isLinePrediction = False
                painter.drawPath(painterPath)
                self.clickedPoints.pop()

            else:
                if self.isLinePrediction:
                    painter.setPen(Qt.red)
                    for i in range(len(self.clickedPoints)):
                        painter.drawEllipse(self.clickedPoints[i], 1, 1)
                    self.clickedPoints.pop()
                    self.isLinePrediction = False

                else:
                    for i in range(len(self.clickedPoints)):
                        painter.drawEllipse(self.clickedPoints[i], 1, 1)

class TimerThread(QThread):
    updateSignal = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        usbSerialCommunication = serial.Serial('/dev/cu.usbmodem141201', 460800)
        self.kneePosition = KneePosition(usbSerialCommunication)  # 膝の座標を取得するためのクラス
        print("Success Establish Connection.")

        self.calibrateKneePosition()

    def run(self):

        while True:
            x, y = self.kneePosition.getPosition()
            # x: 2  <-> 6
            # y: 46 <-> 48 <-> 53
            x, y = self.kneePosition.getMappedPositions8bit(x, y)
            print("x: {}, y: {} .".format(x, y))
            self.updateSignal.emit(x, y)
            self.msleep(10)

        # スレッドが終了してから
        # self.timer.stop()

    def calibrateKneePosition(self):
        print("Start Calibration")
        frames = 20

        calibrationX = np.zeros(frames, dtype=np.float)
        calibrationY = np.zeros(frames, dtype=np.float)

        for i in range(frames):
            print("frames: {}".format(i))
            x, y = self.kneePosition.getPosition()
            calibrationX[i] = x
            calibrationY[i] = y

        calibrateValueX = np.average(calibrationX)
        calibrateValueY = np.average(calibrationY)

        print("Success Calibration with x: {}, y: {} .".format(calibrateValueX, calibrateValueY))
        self.kneePosition.setCalibrateValues(calibrateValueX, calibrateValueY)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi()
        self.show()

        self.activeCanvas = 0                # 操作レイヤの制御
        self.isEnabledKneeControl = False
        self.penColor = QColorDialog()
        # self.timerThread = QThread()

        try:
            self.timerThread = TimerThread()
            self.timerThread.updateSignal.connect(self.controlParamsWithKnee)
            self.timerThread.start()
            self.isEnabledKneeControl = True

        except serial.serialutil.SerialException as e:
            self.statusbar.showMessage("膝操作が無効：シリアル通信が確保できていません。原因：" + str(e))

    def setupUi(self):
        self.setObjectName("self")
        self.resize(900, 650)
        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName("centralwidget")

        self.verticalLayoutWidget = QWidget(self.centralwidget)
        self.verticalLayoutWidget.setGeometry(QRect(600, 410, 290, 100))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")

        self.horizontalSlider = QSlider(self.verticalLayoutWidget)
        self.horizontalSlider.setEnabled(True)
        self.horizontalSlider.setMaximumSize(QSize(256, 22))
        self.horizontalSlider.setOrientation(Qt.Horizontal)
        self.horizontalSlider.setObjectName("horizontalSlider")
        self.verticalLayout.addWidget(self.horizontalSlider)

        self.horizontalSlider_2 = QSlider(self.verticalLayoutWidget)
        self.horizontalSlider_2.setEnabled(True)
        self.horizontalSlider_2.setMaximumSize(QSize(256, 22))
        self.horizontalSlider_2.setOrientation(Qt.Horizontal)
        self.horizontalSlider_2.setObjectName("horizontalSlider_2")
        self.verticalLayout.addWidget(self.horizontalSlider_2)

        self.horizontalSlider_3 = QSlider(self.verticalLayoutWidget)
        self.horizontalSlider_3.setEnabled(True)
        self.horizontalSlider_3.setMaximumSize(QSize(256, 22))
        self.horizontalSlider_3.setOrientation(Qt.Horizontal)
        self.horizontalSlider_3.setObjectName("horizontalSlider_3")
        self.verticalLayout.addWidget(self.horizontalSlider_3)

        self.canvasTableView = QTableView(self.centralwidget)
        self.canvasTableView.setGeometry(QRect(600, 170, 290, 150))
        self.canvasTableView.setObjectName("canvasTableView")
        self.canvasTableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.canvasTableView.horizontalHeader().setDefaultSectionSize(290)
        self.canvasTableView.clicked.connect(self.switchCanvas)


        self.addCanvasButton = QPushButton(self.centralwidget)
        self.addCanvasButton.setGeometry(QRect(760, 330, 120, 25))
        self.addCanvasButton.setObjectName("addCanvasButton")
        self.addCanvasButton.clicked.connect(self.addCanvas)

        self.deleteCanvasButton = QPushButton(self.centralwidget)
        self.deleteCanvasButton.setGeometry(QRect(760, 360, 120, 25))
        self.deleteCanvasButton.setObjectName("deleteCanvasButton")
        self.deleteCanvasButton.clicked.connect(self.deleteCanvas)

        self.addCanvasNameTextEdit = QTextEdit(self.centralwidget)
        self.addCanvasNameTextEdit.setGeometry(QRect(610, 345, 140, 25))
        self.addCanvasNameTextEdit.setObjectName("addCanvasNameTextEdit")

        self.savePictureButton = QPushButton(self.centralwidget)
        self.savePictureButton.setGeometry(QRect(740, 80, 140, 35))
        self.savePictureButton.setObjectName("savePictureButton")
        self.savePictureButton.clicked.connect(self.savePicture)

        self.colorPickerToolButton = QToolButton(self.centralwidget)
        self.colorPickerToolButton.setGeometry(QRect(810, 530, 71, 22))
        self.colorPickerToolButton.setObjectName("colorPickerToolButton")
        self.colorPickerToolButton.clicked.connect(self.pickColor)

        # self.fileReadButton = QPushButton(self.centralwidget)
        # self.fileReadButton.setGeometry(QRect(740, 50, 140, 35))
        # self.fileReadButton.setObjectName("fileReadButton")
        # self.fileReadButton.clicked.connect(self.fileRead)


        # self.widget = QWidget(self.centralwidget)
        # self.widget.setGeometry(QRect(0, 0, 601, 511))
        # self.widget.setObjectName("widget")

        self.canvas = []
        self.canvas.append(Canvas(self.centralwidget))
        self.canvas[0].setGeometry(QRect(0, 0, 600, 600))
        self.canvas[0].setObjectName("canvas0")
        palette = self.canvas[0].palette()
        palette.setColor(QPalette.Background, QColor(255,255,255,255))
        self.canvas[0].setPalette(palette)
        self.canvas[0].setAutoFillBackground(True)
        self.activeCanvas = 0

        self.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(self)
        self.menubar.setGeometry(QRect(0, 0, 889, 22))
        self.menubar.setObjectName("menubar")
        self.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        self.canvasNameTableModel = CanvasNameTableModel()
        self.canvasTableView.setModel(self.canvasNameTableModel)
        self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.activeCanvas, 0))

        self.canvasNameTableModel.layoutChanged.emit()

        _translate = QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.addCanvasButton.setText(_translate("MainWindow", "レイヤを追加"))
        self.deleteCanvasButton.setText(_translate("MainWindow", "レイヤを削除"))
        self.savePictureButton.setText(_translate("MainWindow", "内容を保存(SS)"))
        # self.fileReadButton.setText(_translate("MainWindow", "ファイルを読込む"))
        QMetaObject.connectSlotsByName(self)

    def addCanvas(self):
        newCanvas = Canvas(self.centralwidget)
        newCanvas.setGeometry(QRect(0, 0, 600, 600))
        newCanvas.setObjectName("canvas")
        palette = newCanvas.palette()
        palette.setColor(QPalette.Background, QColor(255,255,255,0))
        newCanvas.setPalette(palette)
        newCanvas.setAutoFillBackground(True)

        self.canvas.append(newCanvas)
        self.activeCanvas = len(self.canvas) - 1


        canvasName = self.addCanvasNameTextEdit.toPlainText()
        if canvasName == "":
            canvasName = 'canvas[' +  str(self.activeCanvas) + ']'
        self.canvasNameTableModel.addCanvas(canvasName)
        self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.activeCanvas, 0))
        self.canvasNameTableModel.layoutChanged.emit()


        # 使用するレイヤだけ使用可能にする
        for canvas in self.canvas:
            canvas.setEnabled(False)
        self.canvas[self.activeCanvas].setEnabled(True)

    def deleteCanvas(self):
        if len(self.canvas) > 1:
            if self.activeCanvas == len(self.canvas) - 1:
                self.activeCanvas -= 1

            deletedCanvas = self.canvas.pop()
            self.canvasNameTableModel.deleteLastCanvas()
            self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.activeCanvas, 0))
            self.canvasNameTableModel.layoutChanged.emit()

            for i in range(len(deletedCanvas.existingPaths)):
                deletedCanvas.existingPaths.pop()

            deletedCanvas.hide()
            # 使用するレイヤだけ使用可能にする
            for canvas in self.canvas:
                canvas.setEnabled(False)
            self.canvas[self.activeCanvas].setEnabled(True)

    def switchCanvas(self, indexClicked: QModelIndex):
        self.activeCanvas = indexClicked.row()

        self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.activeCanvas, 0))
        # 使用するレイヤだけ使用可能にする
        for canvas in self.canvas:
            canvas.setEnabled(False)
        self.canvas[self.activeCanvas].setEnabled(True)

        #選択したレイヤと下のレイヤは見えるようにする
        for i in range(0, self.activeCanvas+1):
            self.canvas[i].setVisible(True)

        # 選択したレイヤより上のレイヤは見えないようにする
        for i in range(self.activeCanvas+1, len(self.canvas)):
            self.canvas[i].setVisible(False)

        self.statusbar.showMessage("レイヤ「" + str(self.canvasNameTableModel.canvasName[self.activeCanvas]) + "」へ切り替わりました")

    def savePicture(self):
        picture = QPixmap()
        picture = self.centralwidget.grab(QRect(0,0,600,600))
        picture.save("test.png")

    def fileRead(self):
        fileName, _ = QFileDialog.getOpenFileNames(self, "open file", "~/sampleImages", "Images (*.jpg *.jpeg *.png *.bmp)")
        fileName = str(fileName)
        print(fileName)

        if fileName:
            self.canvas[self.activeCanvas].setPictureFileName(fileName)
        else:
            self.statusbar.showMessage("画像の読み込みに失敗しました")

    def pickColor(self):
        pickedColor = self.penColor.getColor(Qt.black)
        self.statusbar.showMessage(str(pickedColor))

    def keyPressEvent(self, keyEvent):
        # print(keyEvent.key())
        if keyEvent.key() == Qt.Key_Return:
            self.canvas[self.activeCanvas].fixPath()

        if keyEvent.key() == Qt.Key_Backspace:
            self.canvas[self.activeCanvas].deleteLastPath()

    def getKneePosition(self):
        x, y = self.kneePosition.getPosition()
        # x: 2  <-> 6
        # y: 46 <-> 48 <-> 53
        x, y = self.kneePosition.getMappedPositions8bit(x, y)
        self.controlParamsWithKnee(x, y)


    def calibrateKneePosition(self):
        print("Start Calibration")
        frames = 20

        calibrationX = np.zeros(frames, dtype=np.float)
        calibrationY = np.zeros(frames, dtype=np.float)

        for i in range(frames):
            print("frames: {}".format(i))
            x, y = self.kneePosition.getPosition()
            calibrationX[i] = x
            calibrationY[i] = y

        calibrateValueX = np.average(calibrationX)
        calibrateValueY = np.average(calibrationY)

        print("Success Calibration with x: {}, y: {} .".format(calibrateValueX, calibrateValueY))
        self.kneePosition.setCalibrateValues(calibrateValueX, calibrateValueY)

    def controlParamsWithKnee(self, x, y):
        statusStr = "x: " + str(x) + "y: " + str(y)
        self.statusbar.showMessage(statusStr)
        self.penColor.setCurrentColor(QColor(x, y ,0))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())
