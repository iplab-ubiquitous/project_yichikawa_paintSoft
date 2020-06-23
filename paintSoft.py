import datetime
import os
import sys, math, serial
import time

import KneePosition
from PyQt5.QtCore import Qt, QPoint, QPointF, QRect, QSize, QMetaObject, QCoreApplication, QAbstractTableModel, \
    QModelIndex, QTimer, QThread, QObject, pyqtSignal
from PyQt5.QtGui import QPainter, QPainterPath, QPolygon, QMouseEvent, QImage, qRgb, QPalette, QColor, QPaintEvent, \
    QPixmap, QDragLeaveEvent, QDragMoveEvent
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QSlider, QTableView, QMenuBar, QStatusBar, \
    QPushButton, QTextEdit, QAbstractItemView, QFileDialog, QLabel, QToolButton, QColorDialog, QRadioButton
import PyQt5.sip
import numpy as np
from enum import Enum

participant_No = 0


class OperationMode(Enum):
    NONE           = 0
    DRAWING_POINTS = 1
    MOVING_POINTS  = 2
    SWITCH_LAYER   = 3
    COLOR_PICKER   = 4


# 任意の点を通る曲線を描くためのパスを作る
class RoundedPolygon(QPolygon):
    def __init__(self, i_radius: int, parent=None):
        self.__i_radius = i_radius

    def set_radius(self, i_radius: int):
        self.__i_radius = i_radius

    def get_distance(self, pt1: QPoint, pt2: QPoint) -> float:
        return math.sqrt((pt1.x() - pt2.x()) * (pt1.x() - pt2.x()) +
                         (pt1.y() - pt2.y()) * (pt1.y() - pt2.y()))

    def get_line_start(self, index: int) -> QPointF:
        pt = QPointF()
        pt1 = self.clickedPoints[index]
        pt2 = self.clickedPoints[(index + 1) %
                                 len(self.clickedPoints)]
        if self.get_distance(pt1, pt2) == 0:
            f_rat = 0.5
        else:
            f_rat = float(self.__i_radius) / self.get_distance(pt1, pt2)
            if f_rat > 0.5:
                f_rat = 0.5

        pt.setX((1.0 - f_rat) * pt1.x() + f_rat * pt2.x())
        pt.setY((1.0 - f_rat) * pt1.y() + f_rat * pt2.y())
        return pt

    def get_line_end(self, index: int) -> QPointF:
        pt = QPointF()
        pt1 = self.clickedPoints[index]
        pt2 = self.clickedPoints[(index + 1) %
                                 len(self.clickedPoints)]
        # pt2 = self.clickedPoints[index+1]
        if self.get_distance(pt1, pt2) == 0:
            f_rat = 0.5
        else:
            f_rat = float(self.__i_radius) / self.get_distance(pt1, pt2)
            if f_rat > 0.5:
                f_rat = 0.5

        pt.setX(f_rat * pt1.x() + (1.0 - f_rat) * pt2.x())
        pt.setY(f_rat * pt1.y() + (1.0 - f_rat) * pt2.y())
        return pt

    def get_path(self, clickedPoints) -> QPainterPath:
        m_path = QPainterPath()
        self.clickedPoints = clickedPoints

        if len(self.clickedPoints) < 3:
            print("still have 2 points or less.")
            return m_path

        pt1 = QPointF()
        pt2 = QPointF()

        for i in range(len(self.clickedPoints) - 1):
            pt1 = self.get_line_start(i)

            if i == 0:
                m_path.moveTo(pt1)
            else:
                m_path.quadTo(clickedPoints[i], pt1)

            # pt2 = self.getLineEnd(i)
            # mPath.lineTo(pt2)

        # pt1 = self.getLineStart(0)
        # mPath.quadTo(clickedPoints[0], pt1)

        return m_path


class CanvasNameTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas_name: List[str] = ["canvas[0]"]
        self.is_visible: List[bool] = [True]

    def rowCount(self, parent=None):
        return len(self.canvas_name)

    def columnCount(self, parent=None):
        return 2

    def data(self, index: QModelIndex, role: int):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.canvas_name[index.row()]
            elif index.column() == 1:
                return "🙂" if self.is_visible[index.row()] else "😴"

    def headerData(self, section: int, orientation: int, role: int):
        if role == Qt.DisplayRole & orientation == Qt.Horizontal:
            if section == 0:
                return "CanvasName"
            elif section == 1:
                return "Is Visible Canvas"
        else:
            return ""

    def add_canvas(self, canvasName: str):
        self.canvas_name.append(canvasName)
        self.is_visible.append(True)

    def toggle_canvas_visible(self, index: int):
        self.is_visible[index] = not self.is_visible[index]
        return self.is_visible[index]

    def delete_last_canvas(self):
        self.canvas_name.pop()
        self.is_visible.pop()


class Canvas(QWidget):
    def __init__(self, parent=None):
        super(Canvas, self).__init__(parent)

        self.is_enable_knee_control = False

        # 画像専用のレイヤであるかを制御する
        # 1度Trueになったら2度とFalseにならないことを意図する
        self.is_picture_canvas = False
        self.picture_file_name = ""
        self.image = QImage()

        # マウストラック有効化
        self.setMouseTracking(True)

        # マウス移動で出る予測線とクリックして出る本線を描画するときに区別する
        self.is_line_prediction = False

        self.rounded_polygon = RoundedPolygon(10000)

        self.existing_paths = []
        self.clicked_points = []
        self.cursor_position = QPointF()
        self.cursor_position_mousePressed = QPointF()
        self.knee_position = QPointF()
        self.knee_position_mousePressed = QPointF()
        self.current_drawing_mode = OperationMode.DRAWING_POINTS

        self.line_color = []
        self.current_line_color = QColor()

        self.nearest_path = QPainterPath()
        self.nearest_distance = 50.0
        self.nearest_index = -1
        self.is_dragging = False

        self.show()

    def mousePressEvent(self, event: QMouseEvent):

        if self.current_drawing_mode == OperationMode.DRAWING_POINTS:
            # 制御点の追加
            if event.button() == Qt.LeftButton:
                self.clicked_points.append(event.pos())
                # print(self.clickedPoints)

            # 直前の制御点の消去
            if event.button() == Qt.RightButton:
                if len(self.clicked_points) > 0:
                    self.clicked_points.pop()
                self.update()

        elif self.current_drawing_mode == OperationMode.MOVING_POINTS:
            if event.button() == Qt.LeftButton:
                self.is_dragging = True
                if self.is_enable_knee_control:
                    self.recode_knee_and_cursor_position()

                self.cursor_position = event.pos()
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.current_drawing_mode == OperationMode.DRAWING_POINTS:
            self.clicked_points.append(event.pos())
            self.is_line_prediction = True
            self.update()

        elif self.current_drawing_mode == OperationMode.MOVING_POINTS:
            self.cursor_position = event.pos()
            if self.is_dragging:
                self.move_point()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.is_dragging = False

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)

        if self.is_picture_canvas:
             painter.drawImage(QRect(0, 0, 600, 600),self.image)

        else:
            # すでに確定されているパスの描画
            if len(self.existing_paths) > 0:
                for i in range(len(self.existing_paths)):
                    painter.setPen(self.line_color[i])
                    painter.drawPath(self.existing_paths[i])

            if self.current_drawing_mode == OperationMode.DRAWING_POINTS:
                # 　現在描いているパスの描画
                if len(self.clicked_points) > 3:
                    painter.setPen(self.current_line_color)
                    # print(self.clickedPoints)
                    # クリックした点まで線を伸ばすため、終点を一時的にリストに入れている
                    self.clicked_points.append(self.clicked_points[len(self.clicked_points) - 1])
                    painter_path = self.rounded_polygon.get_path(self.clicked_points)

                    # 設置した点の描画
                    painter.setPen(Qt.black)
                    for i in range(len(self.clicked_points)):
                        painter.drawEllipse(self.clicked_points[i], 2, 2)
                    painter.setPen(self.current_line_color)
                    # 現在のマウス位置での予告線
                    if self.is_line_prediction:
                        self.clicked_points.pop()
                        self.is_line_prediction = False
                    painter.drawPath(painter_path)
                    self.clicked_points.pop()

                # 線が描けない時
                else:
                    # 現在のマウス位置での予告線
                    if self.is_line_prediction:
                        painter.setPen(Qt.red)
                        for i in range(len(self.clicked_points)):
                            painter.drawEllipse(self.clicked_points[i], 2, 2)
                        self.clicked_points.pop()
                        self.is_line_prediction = False

                    # 予告線でもない場合は単に点を書く
                    else:
                        for i in range(len(self.clicked_points)):
                            painter.drawEllipse(self.clicked_points[i], 2, 2)

            # 制御点を移動するとき
            elif self.current_drawing_mode == OperationMode.MOVING_POINTS:
                # すでに確定されているパスの制御点の描画
                self.nearest_distance = 50.0
                painter.setPen(Qt.black)
                for path in self.existing_paths:
                    for i in range(path.elementCount()):
                        control_point = QPointF(path.elementAt(i).x, path.elementAt(i).y)
                        painter.drawEllipse(control_point, 3, 3)

                        # 現在のカーソル位置から最も近い点と、その点が属するpathを記録、更新
                        # if not self.is_dragging & self.is_enable_knee_control:
                        distance = math.sqrt((control_point.x() - self.cursor_position.x()) ** 2 + (
                                    control_point.y() - self.cursor_position.y()) ** 2)
                        if distance < self.nearest_distance:
                            self.nearest_distance = distance
                            self.nearest_path = path
                            self.nearest_index = i

                # 一定の距離未満かつ最も近い点を赤く描画
                if self.nearest_distance < 20:
                    painter.setPen(Qt.red)
                    nearest_control_point = QPointF(self.nearest_path.elementAt(self.nearest_index).x,
                                                    self.nearest_path.elementAt(self.nearest_index).y)
                    painter.drawEllipse(nearest_control_point, 3, 3)
                print("dist:{}".format(self.nearest_distance))

    def move_point(self):
        if self.is_enable_knee_control:
            self.nearest_path.setElementPositionAt(self.nearest_index, self.cursor_position.x(),
                                                   self.cursor_position.y())
        # 選択した制御点の移動量 = カーソルクリック位置 +
        # amount_of_change = QPointF(self.cursor_position_mousePressed.x() +
        #                            (self.knee_position.x() - self.knee_position_mousePressed.x()),
        #                            self.cursor_position_mousePressed.y() -　　
        #                            (self.knee_position.y() - self.knee_position_mousePressed.y()))
            amount_of_change = QPointF(self.cursor_position.x() +
                                       (self.knee_position.x() - self.knee_position_mousePressed.x()),
                                       self.cursor_position.y() -
                                       (self.knee_position.y() - self.knee_position_mousePressed.y()))
            self.nearest_path.setElementPositionAt(self.nearest_index, amount_of_change.x(), amount_of_change.y())

        else:
            if self.nearest_distance < 20:
                self.nearest_path.setElementPositionAt(self.nearest_index, self.cursor_position.x(),
                                                       self.cursor_position.y())

    def set_knee_position(self, x, y):
        self.knee_position.setX(x)
        self.knee_position.setY(y)

        if self.is_dragging:
            if self.current_drawing_mode == OperationMode.MOVING_POINTS:
                self.move_point()
                self.update()

    def recode_knee_and_cursor_position(self):
        self.knee_position_mousePressed.setX(self.knee_position.x())
        self.knee_position_mousePressed.setY(self.knee_position.y())
        self.cursor_position_mousePressed = self.cursor_position

    def fix_path(self):
        # パスを確定
        if self.is_line_prediction:
            self.clicked_points.pop()
        # クリックした点まで線を伸ばすため、終点をリストに入れている
        if len(self.clicked_points) > 0:
            self.clicked_points.append(self.clicked_points[len(self.clicked_points) - 1])
            painter_path = self.rounded_polygon.get_path(self.clicked_points)

            #線と色を記録
            self.existing_paths.append(painter_path)
            self.line_color.append(self.current_line_color)

            #点をリセット
            self.clicked_points = []
            self.update()

    def delete_last_path(self):
        if len(self.existing_paths) > 0:
            self.existing_paths.pop()
            self.line_color.pop()
            self.update()

    def switch_visible(self, is_visible: bool):
        palette = self.palette()
        if is_visible:
            palette.setColor(QPalette.Background, QColor(255, 255, 255, 120))
        else:
            palette.setColor(QPalette.Background, QColor(255, 255, 255, 255))
        self.setPalette(palette)

    def operation_mode_changed(self, to: OperationMode):
        self.current_drawing_mode = to
        self.fix_path()

    def set_picture_file_name(self, picture_file_name: str):
        self.is_picture_canvas = True
        self.picture_file_name = picture_file_name
        self.update()

    def set_enable_knee_control(self, is_enable_knee_control):
        self.is_enable_knee_control = is_enable_knee_control

    def load_picture(self, image: QImage):
        self.image = image
        self.is_picture_canvas = True
        self.update()



class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi()
        self.show()

        self.active_canvas = 0  # 操作レイヤの制御
        self.is_enabled_knee_control = False
        self.is_mode_switched = False
        self.current_drawing_mode = OperationMode.DRAWING_POINTS
        self.pen_color = QColorDialog()
        self.current_color_saturation = 127
        self.current_knee_operation_mode = OperationMode.NONE
        # self.timerThread = QThread()

        try:
            self.timer_thread = KneePosition.TimerThread()
            self.timer_thread.updateSignal.connect(self.control_params_with_knee)
            self.timer_thread.start()
            self.kneePosition = self.timer_thread.kneePosition
            self.is_enabled_knee_control = True
            self.current_knee_operation_mode = OperationMode.DRAWING_POINTS

        except serial.serialutil.SerialException as e:
            self.statusbar.showMessage("膝操作が無効：シリアル通信が確保できていません。原因：" + str(e))

        self.canvas[0].set_enable_knee_control(self.is_enabled_knee_control)
        self.displayKneeOperationModeTextLabel.setText("Knee mode: \n {}".format(self.current_knee_operation_mode))

        self.colorPickerToolButton.setStyleSheet("background-color: black")

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

        self.canvasTableView = QTableView(self.centralwidget)
        self.canvasTableView.setGeometry(QRect(600, 170, 290, 150))
        self.canvasTableView.setObjectName("canvasTableView")
        self.canvasTableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.canvasTableView.horizontalHeader().setDefaultSectionSize(145)
        self.canvasTableView.clicked.connect(self.table_item_clicked)

        self.addCanvasButton = QPushButton(self.centralwidget)
        self.addCanvasButton.setGeometry(QRect(760, 320, 120, 25))
        self.addCanvasButton.setObjectName("addCanvasButton")
        self.addCanvasButton.clicked.connect(self.add_canvas)

        self.deleteCanvasButton = QPushButton(self.centralwidget)
        self.deleteCanvasButton.setGeometry(QRect(760, 350, 120, 25))
        self.deleteCanvasButton.setObjectName("deleteCanvasButton")
        self.deleteCanvasButton.clicked.connect(self.delete_canvas)

        self.addCanvasNameTextEdit = QTextEdit(self.centralwidget)
        self.addCanvasNameTextEdit.setGeometry(QRect(610, 340, 140, 25))
        self.addCanvasNameTextEdit.setObjectName("addCanvasNameTextEdit")

        self.savePictureButton = QPushButton(self.centralwidget)
        self.savePictureButton.setGeometry(QRect(750, 480, 140, 35))
        self.savePictureButton.setObjectName("savePictureButton")
        self.savePictureButton.clicked.connect(self.save_picture)

        self.colorPickerToolButton = QToolButton(self.centralwidget)
        self.colorPickerToolButton.setGeometry(QRect(810, 530, 71, 22))
        self.colorPickerToolButton.setObjectName("colorPickerToolButton")
        self.colorPickerToolButton.clicked.connect(self.pick_color)
        self.colorPickerToolButton.setAutoFillBackground(True)

        self.selectOperationModeButton = QPushButton(self.centralwidget)
        self.selectOperationModeButton.setGeometry(QRect(600, 80, 140, 40))
        self.selectOperationModeButton.setObjectName("selectOperationModeButton")
        self.selectOperationModeButton.clicked.connect(self.switch_drawing_mode)

        self.displayKneeOperationModeTextLabel = QLabel(self.centralwidget)
        self.displayKneeOperationModeTextLabel.setGeometry(QRect(610, 10, 270, 40))
        self.displayKneeOperationModeTextLabel.setObjectName("displayKneeOperationModeTextLabel")

        self.readFileNametextEdit = QTextEdit(self.centralwidget)
        self.readFileNametextEdit.setGeometry(QRect(610, 440, 140, 30))
        self.readFileNametextEdit.setLineWidth(2)
        self.readFileNametextEdit.setObjectName("readFileNametextEdit")

        self.saveFileNametextEdit = QTextEdit(self.centralwidget)
        self.saveFileNametextEdit.setGeometry(QRect(610, 480, 140, 30))
        self.saveFileNametextEdit.setLineWidth(2)
        self.saveFileNametextEdit.setObjectName("saveFileNametextEdit")

        self.fileReadButton = QPushButton(self.centralwidget)
        self.fileReadButton.setGeometry(QRect(750, 440, 140, 35))
        self.fileReadButton.setObjectName("fileReadButton")
        self.fileReadButton.clicked.connect(self.file_read)

        self.IsAllCanvasInvisibleradioButton = QPushButton(self.centralwidget)
        self.IsAllCanvasInvisibleradioButton.setGeometry(QRect(670, 380, 200, 30))
        self.IsAllCanvasInvisibleradioButton.setObjectName("IsAllCanvasInvisibleradioButton")

        # self.widget = QWidget(self.centralwidget)
        # self.widget.setGeometry(QRect(0, 0, 601, 511))
        # self.widget.setObjectName("widget")

        self.canvas = []
        self.canvas.append(Canvas(self.centralwidget))
        self.canvas[0].setGeometry(QRect(0, 0, 600, 600))
        self.canvas[0].setObjectName("canvas0")
        palette = self.canvas[0].palette()
        palette.setColor(QPalette.Background, QColor(255, 255, 255, 255))
        self.canvas[0].setPalette(palette)
        self.canvas[0].setAutoFillBackground(True)
        self.active_canvas = 0

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
        self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.active_canvas, 0))

        self.canvasNameTableModel.layoutChanged.emit()

        _translate = QCoreApplication.translate
        self.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.addCanvasButton.setText(_translate("MainWindow", "レイヤを追加"))
        self.deleteCanvasButton.setText(_translate("MainWindow", "レイヤを削除"))
        self.savePictureButton.setText(_translate("MainWindow", "内容を保存(SS)"))
        self.fileReadButton.setText(_translate("MainWindow", "ファイルを読込む"))
        self.selectOperationModeButton.setText(_translate("MainWindow", "DRAWING_POINTS"))
        self.displayKneeOperationModeTextLabel.setText(_translate("MainWindow", "Knee mode:NONE"))
        self.IsAllCanvasInvisibleradioButton.setText(_translate("MainWindow", "全レイヤを透明/不透明にする"))
        QMetaObject.connectSlotsByName(self)

    def add_canvas(self):
        new_canvas = Canvas(self.centralwidget)
        new_canvas.setGeometry(QRect(0, 0, 600, 600))
        new_canvas.setObjectName("canvas")
        palette = new_canvas.palette()
        palette.setColor(QPalette.Background, QColor(255, 255, 255, 120))
        new_canvas.setPalette(palette)
        new_canvas.setAutoFillBackground(True)
        new_canvas.is_enable_knee_control = self.is_enabled_knee_control
        new_canvas.operation_mode_changed(self.current_drawing_mode)

        self.canvas.append(new_canvas)
        self.active_canvas = len(self.canvas) - 1

        canvas_name = self.addCanvasNameTextEdit.toPlainText()
        if canvas_name == "":
            canvas_name = 'canvas[' + str(self.active_canvas) + ']'
        self.canvasNameTableModel.add_canvas(canvas_name)
        self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.active_canvas, 0))
        self.canvasNameTableModel.layoutChanged.emit()

        # 使用するレイヤだけ使用可能にする
        for canvas in self.canvas:
            canvas.setEnabled(False)
        self.canvas[self.active_canvas].setEnabled(True)

    def delete_canvas(self):
        if len(self.canvas) > 1:
            if self.active_canvas == len(self.canvas) - 1:
                self.active_canvas -= 1

            deleted_canvas = self.canvas.pop()
            self.canvasNameTableModel.delete_last_canvas()
            self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.active_canvas, 0))
            self.canvasNameTableModel.layoutChanged.emit()

            for i in range(len(deleted_canvas.existing_paths)):
                deleted_canvas.existing_paths.pop()

            deleted_canvas.hide()
            # 使用するレイヤだけ使用可能にする
            for canvas in self.canvas:
                canvas.setEnabled(False)
            self.canvas[self.active_canvas].setEnabled(True)

    def table_item_clicked(self, index_clicked: QModelIndex):
        col = index_clicked.column()
        row = index_clicked.row()

        if col == 0:
            self.switch_canvas_from_table(row)
        elif col == 1:
            if row <= self.active_canvas:
                is_visible = self.canvasNameTableModel.toggle_canvas_visible(row)
                # self.canvas[self.active_canvas].switch_visible(is_visible)
                self.canvas[row].setVisible(is_visible)


        self.canvasNameTableModel.layoutChanged.emit()

    def switch_canvas_from_table(self, switch_to: int):
        self.active_canvas = switch_to

        self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.active_canvas, 0))
        # 使用するレイヤだけ使用可能にする
        for canvas in self.canvas:
            canvas.setEnabled(False)
        self.canvas[self.active_canvas].setEnabled(True)
        self.canvas[self.active_canvas].operation_mode_changed(self.current_drawing_mode)

        # 選択したレイヤと下のレイヤは見えるようにする
        for i in range(0, self.active_canvas + 1):
            self.canvas[i].setVisible(True)

        # 選択したレイヤより上のレイヤは見えないようにする
        for i in range(self.active_canvas + 1, len(self.canvas)):
            self.canvas[i].setVisible(False)

        self.statusbar.showMessage(
            "レイヤ「" + str(self.canvasNameTableModel.canvas_name[self.active_canvas]) + "」へ切り替わりました")

    def switch_canvas_from_index(self, index: int):
        self.active_canvas = index

        self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.active_canvas, 0))
        # 使用するレイヤだけ使用可能にする
        for canvas in self.canvas:
            canvas.setEnabled(False)
        self.canvas[self.active_canvas].setEnabled(True)
        self.canvas[self.active_canvas].operation_mode_changed(self.current_knee_operation_mode)

        # 選択したレイヤと下のレイヤは見えるようにする
        for i in range(0, self.active_canvas + 1):
            self.canvas[i].setVisible(True)

        # 選択したレイヤより上のレイヤは見えないようにする
        for i in range(self.active_canvas + 1, len(self.canvas)):
            self.canvas[i].setVisible(False)

        self.statusbar.showMessage(
            "レイヤ「" + str(self.canvasNameTableModel.canvas_name[self.active_canvas]) + "」へ切り替わりました")

    def save_picture(self):
        picture = QPixmap()
        picture = self.centralwidget.grab(QRect(0, 0, 600, 600))
        picture.save("test.png")

    def file_read(self):
        file_name = "test.png"
        if not self.readFileNametextEdit.toPlainText() == "":
            file_name = "sampleImages/" + self.readFileNametextEdit.toPlainText() + ".png"
        image = QImage(file_name)
        self.canvas[self.active_canvas].load_picture(image)
        self.statusbar.showMessage("picture")

    def pick_color(self):
        picked_color = self.pen_color.getColor(self.canvas[self.active_canvas].current_line_color)
        # print(pickedColor.hsvSaturation())
        # self.currentColorSaturation = pickedColor.hsvSaturation()
        self.canvas[self.active_canvas].current_line_color = picked_color

        color_string = "background-color: rgb({},{},{})".format(picked_color.red(),
                                                                picked_color.green(),
                                                                picked_color.blue())
        self.colorPickerToolButton.setStyleSheet(color_string)

    def switch_drawing_mode(self):
        if self.current_drawing_mode == OperationMode.DRAWING_POINTS:
            self.current_drawing_mode = OperationMode.MOVING_POINTS

        elif self.current_drawing_mode == OperationMode.MOVING_POINTS:
            self.current_drawing_mode = OperationMode.DRAWING_POINTS
        else:
            self.current_drawing_mode = OperationMode.NONE

        # 膝操作が有効の時は膝操作のモードも合わせる
        if self.is_enabled_knee_control:
            if self.current_drawing_mode == OperationMode.DRAWING_POINTS:
                self.current_knee_operation_mode = OperationMode.DRAWING_POINTS

            elif self.current_drawing_mode == OperationMode.MOVING_POINTS:
                self.current_knee_operation_mode = OperationMode.MOVING_POINTS
            else:
                self.current_drawing_mode = OperationMode.NONE

        self.canvas[self.active_canvas].operation_mode_changed(self.current_drawing_mode)
        self.selectOperationModeButton.setText("{}".format(self.current_drawing_mode.name))
        self.displayKneeOperationModeTextLabel.setText("Knee mode: \n {}".format(self.current_knee_operation_mode))
        self.statusbar.showMessage("Mode:{}".format(self.current_drawing_mode.name))

    def switch_knee_operation_mode(self):
        if self.current_knee_operation_mode == OperationMode.NONE:
            self.current_knee_operation_mode = OperationMode.DRAWING_POINTS
            self.current_drawing_mode        = OperationMode.DRAWING_POINTS

        elif self.current_knee_operation_mode == OperationMode.DRAWING_POINTS:
            self.current_knee_operation_mode = OperationMode.MOVING_POINTS
            self.current_drawing_mode        = OperationMode.MOVING_POINTS

        elif self.current_knee_operation_mode == OperationMode.MOVING_POINTS:
            self.current_knee_operation_mode = OperationMode.SWITCH_LAYER
            self.current_drawing_mode        = OperationMode.DRAWING_POINTS

        elif self.current_knee_operation_mode == OperationMode.SWITCH_LAYER:
            self.current_knee_operation_mode = OperationMode.COLOR_PICKER
            self.current_drawing_mode        = OperationMode.DRAWING_POINTS

        elif self.current_knee_operation_mode == OperationMode.COLOR_PICKER:
            self.current_knee_operation_mode = OperationMode.DRAWING_POINTS
            self.current_drawing_mode        = OperationMode.DRAWING_POINTS

        else:
            self.current_knee_operation_mode = OperationMode.NONE

        self.canvas[self.active_canvas].operation_mode_changed(self.current_drawing_mode)
        self.selectOperationModeButton.setText("{}".format(self.current_drawing_mode.name))
        self.displayKneeOperationModeTextLabel.setText("Knee mode: \n {}".format(self.current_knee_operation_mode))
        self.statusbar.showMessage("Mode:{}".format(self.current_drawing_mode.name))

    def keyPressEvent(self, keyEvent):
        # print(keyEvent.key())
        if keyEvent.key() == Qt.Key_Return:
            self.canvas[self.active_canvas].fix_path()

        if keyEvent.key() == Qt.Key_Backspace:
            self.canvas[self.active_canvas].delete_last_path()

    def setup_experiment(self):
        # 取得する指標


        # タイマー
        self.start_time = 0
        self.previous_operated_time = 0

        self.is_started_experiment = False

        self.frame_records = np.empty((0, 3), float)  # 操作ごとの記録
        self.operation_records = np.empty((0, 5), float)  # フレーム（膝位置が更新される）ごとの記録

    def start_experiment(self):
        self.start_time = time.time()
        self.is_started_experiment = True

        self.statusbar.showMessage("Experiment started p{}"
                                   .format(participant_No)
                                   )

    def record_frame(self):
        if self.is_started_experiment:
            current_time = time.time() - self.start_time
            self.frame_records = np.append(self.frame_records, np.array(
                [[self.current_position.x(),
                  self.current_position.y(),
                  current_time]]
            ), axis=0)

    def record_operation(self):
        current_time = time.time() - self.start_time

        operation_times = current_time - self.previous_operated_time
        offsets = self.current_knee_step - self.rect_orders[self.current_order]

        self.operation_records = np.append(self.operation_records, np.array(
            [[self.current_position.x(),
              self.current_position.y(),
              operation_times,
              self.current_knee_step,
              self.rect_orders[self.current_order]]]
        ), axis=0)
        self.previous_operated_time = current_time
        self.statusbar.showMessage(str(current_time))

    def save_records(self):
        if not self.is_started_experiment:
            date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = "result_paint_experiment/p{}/data/".format(participant_No)
            try:
                os.makedirs(file_path)
            except FileExistsError:
                pass

            np.savetxt(file_path + "test_frameRecords_{}.csv".format(date), self.frame_records, delimiter=',',
                       fmt=['%.5f', '%.5f', '%.5f'],
                       header='knee_pos_x, knee_pos_y, time',
                       comments=' ')
            np.savetxt(file_path + "test_operationRecords_{}.csv".format(date), self.operation_records, delimiter=',',
                       fmt=['%.5f', '%.5f', '%.5f', '%.0f', '%.0f'],
                       header="knee_pos_x, knee_pos_y, time, selected_No, target_No, calibration x:{} y:{}"
                       .format(self.kneePosition.knee_pos_x_center, self.kneePosition.knee_pos_y_center),
                       comments=' ')
            self.statusbar.showMessage("Saved.")

    def control_params_with_knee(self, x, y):
        if y == 0:
            if not self.is_mode_switched:
                self.statusbar.showMessage("switch")
                self.switch_knee_operation_mode()
                self.is_mode_switched = True
        else:
            if self.current_knee_operation_mode == OperationMode.NONE:
                pass

            elif self.current_knee_operation_mode == OperationMode.DRAWING_POINTS:
                pass

            elif self.current_knee_operation_mode == OperationMode.MOVING_POINTS:
                x, y = self.kneePosition.get_mapped_positions(x, y, 0, 200)
                self.canvas[self.active_canvas].set_knee_position(x, y)

            elif self.current_knee_operation_mode == OperationMode.SWITCH_LAYER:
                x, _ = self.kneePosition.get_mapped_positions(x, y, 1, 359)
                target_number = (int)(x / (360/self.canvasNameTableModel.rowCount()))
                if not self.active_canvas == target_number:
                    self.switch_canvas_from_index(target_number)

            elif self.current_knee_operation_mode == OperationMode.COLOR_PICKER:
                x, _ = self.kneePosition.get_mapped_positions(x, y, 1, 359)
                _, y = self.kneePosition.get_mapped_positions(x, y, 0, 255)
                next_color = QColor()
                next_color.setHsv(x, 255, y, 255)
                self.pen_color.setCurrentColor(next_color)

            else:
                self.current_knee_operation_mode = OperationMode.NONE

            if self.is_mode_switched:
                self.is_mode_switched = False

            status_str = "x: " + str(x) + "y: " + str(y)
            self.statusbar.showMessage(status_str)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())
