import sys, math, serial
from PyQt5.QtCore import Qt, QPoint, QPointF, QRect, QSize, QMetaObject, QCoreApplication, QAbstractTableModel, \
    QModelIndex, QTimer, QThread, QObject, pyqtSignal
from PyQt5.QtGui import QPainter, QPainterPath, QPolygon, QMouseEvent, QImage, qRgb, QPalette, QColor, QPaintEvent, \
    QPixmap, QDragLeaveEvent, QDragMoveEvent
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QSlider, QTableView, QMenuBar, QStatusBar, \
    QPushButton, QTextEdit, QAbstractItemView, QFileDialog, QLabel, QToolButton, QColorDialog
import PyQt5.sip
import numpy as np
from enum import Enum

NUM_OF_SENSORS = 10
WAITING_FRAMES = 100
ALPHA_EMA = 0.7


class OperationMode(Enum):
    NONE           = 0
    DRAWING_POINTS = 1
    MOVING_POINTS  = 2
    COLOR_PICKER   = 3


class KneePosition(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.distance_sensor_array_communication = serial.Serial('/dev/cu.usbmodem141201', 460800)
        for i in range(10):
            self.distance_sensor_array_communication.readline()  # 読み飛ばし(欠けたデータが読み込まれるのを避ける)

        # （仮の）膝の座標値
        self.old_x = 0
        self.old_y = 0

        # キャリブレーションの記録
        self.knee_pos_x_minimum = 2
        self.knee_pos_x_center  = 4
        self.knee_pos_x_maximum = 6
        self.knee_pos_y_minimum = 46
        self.knee_pos_y_center  = 48
        self.knee_pos_y_maximum = 53

        # 膝検出・位置計算用
        self.sensor_val = np.zeros(NUM_OF_SENSORS, dtype=np.float)
        self.weight = ([1.00] * NUM_OF_SENSORS)
        self.val = np.zeros((WAITING_FRAMES, NUM_OF_SENSORS), dtype=np.float)
        self.leg_flag = False
        self.sensor_flt = np.zeros((WAITING_FRAMES, NUM_OF_SENSORS), dtype=np.float)

    def calibrate_knee_position(self):
        print("Set up EMA...")
        for i in range(30):
            x, y = self.get_position()
            print("frames: {}, x: {}, y: {}".format(i, x, y))

        calibration_frames = 20

        calibration_x = np.zeros(calibration_frames, dtype=np.float)
        calibration_y = np.zeros(calibration_frames, dtype=np.float)

        print("Start Calibration")

        for i in range(calibration_frames):
            x, y = self.get_position()
            print("frames: {}, x: {}, y: {}".format(i, x, y))
            calibration_x[i] = x
            calibration_y[i] = y

        calibrate_value_x = np.average(calibration_x)
        calibrate_value_y = np.average(calibration_y)

        print("Success Calibration with x: {}, y: {} .".format(calibrate_value_x, calibrate_value_y))

        self.knee_pos_x_center = calibrate_value_x
        self.knee_pos_x_maximum = calibrate_value_x + 0.5
        self.knee_pos_x_minimum = calibrate_value_x - 0.5

        self.knee_pos_y_center = calibrate_value_y
        self.knee_pos_y_maximum = calibrate_value_y + 2
        self.knee_pos_y_minimum = calibrate_value_y - 1

    def get_distance(self):
        distances = float(0)
        while self.distance_sensor_array_communication.in_waiting > 1 or distances == float(0):
            distances = self.distance_sensor_array_communication.readline().strip().decode("utf-8").split(',')

        return distances

    def get_mapped_value(self, val, in_min, in_max, out_min, out_max):
        return (val - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def get_mapped_positions(self, x, y, lower_limit, upper_limit):
        x = self.get_mapped_value(x, self.knee_pos_x_minimum, self.knee_pos_x_maximum, lower_limit, upper_limit)
        if x > upper_limit:
            x = upper_limit
        elif x < lower_limit:
            x = lower_limit

        center = (upper_limit - lower_limit + 1) / 2 - 1

        if y < self.knee_pos_y_center:
            y = self.get_mapped_value(y, self.knee_pos_y_minimum, self.knee_pos_y_center, lower_limit, center)
        else:
            y = self.get_mapped_value(y, self.knee_pos_y_center, self.knee_pos_y_maximum, center, upper_limit)

        if y > upper_limit:
            y = upper_limit
        elif y < lower_limit:
            y = lower_limit

        return x, y

    def get_position(self):
        weight = ([1.00] * NUM_OF_SENSORS)

        sensor_values = self.get_distance()
        sensor_values = [64 - float(v) for v in sensor_values]  # 計算を容易にするため膝との距離を反転（要らないかもしれない）

        max_distance = np.max(sensor_values)

        new_y = max_distance

        for i in range(NUM_OF_SENSORS):
            weight[i] = 1 / (max_distance - sensor_values[i] + 2)
        weight_sum = np.sum(weight)

        new_x = 0

        for i in range(NUM_OF_SENSORS):
            new_x += (i * weight[i] / weight_sum)

        new_x = (new_x - self.old_x) * ALPHA_EMA + self.old_x
        self.old_x = new_x

        new_y = (new_y - self.old_y) * ALPHA_EMA + self.old_y
        self.old_y = new_y

        if new_y > self.knee_pos_y_maximum + 2:
            new_y = 0

        return new_x, new_y


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

    def rowCount(self, parent=None):
        return len(self.canvas_name)

    def columnCount(self, parent=None):
        return 1

    def data(self, index: QModelIndex, role: int):
        if role == Qt.DisplayRole:
            return self.canvas_name[index.row()]

    def headerData(self, section: int, orientation: int, role: int):
        if role == Qt.DisplayRole & orientation == Qt.Horizontal:
            return "CanvasName"
        else:
            return ""

    def add_canvas(self, canvasName: str):
        self.canvas_name.append(canvasName)

    def delete_last_canvas(self):
        self.canvas_name.pop()


class Canvas(QWidget):
    def __init__(self, parent=None):
        super(Canvas, self).__init__(parent)

        self.is_enable_knee_control = False

        # 画像専用のレイヤであるかを制御する
        # 1度Trueになったら2度とFalseにならないことを意図する
        self.is_picture_canvas = False
        self.picture_file_name = ""

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
        self.current_operation_mode = OperationMode.DRAWING_POINTS

        self.nearest_path = QPainterPath()
        self.nearest_distance = 30.0
        self.nearest_index = 0
        self.is_dragging = False

        self.show()

    def mousePressEvent(self, event: QMouseEvent):

        if self.current_operation_mode == OperationMode.DRAWING_POINTS:
            # 制御点の追加
            if event.button() == Qt.LeftButton:
                self.clicked_points.append(event.pos())
                # print(self.clickedPoints)

            # 直前の制御点の消去
            if event.button() == Qt.RightButton:
                self.clicked_points.pop()
            self.update()

        elif self.current_operation_mode == OperationMode.MOVING_POINTS:
            if event.button() == Qt.LeftButton:
                self.is_dragging = True
                if self.is_enable_knee_control:
                    self.recode_knee_and_cursor_position()

                self.cursor_position = event.pos()
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.current_operation_mode == OperationMode.DRAWING_POINTS:
            self.clicked_points.append(event.pos())
            self.is_line_prediction = True
            self.update()

        elif self.current_operation_mode == OperationMode.MOVING_POINTS:
            self.cursor_position = event.pos()
            if self.is_dragging:
                self.move_point()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.current_operation_mode == OperationMode.DRAWING_POINTS:
            pass

        elif self.current_operation_mode == OperationMode.MOVING_POINTS:
            self.is_dragging = False

    def dragMoveEvent(self, event: QDragMoveEvent):
        print("drag moving")

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        print("drag leave")

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)

        if self.is_picture_canvas:
            self.setAutoFillBackground(False)
            image = QPixmap(self.picture_file_name)
            size = image.size()
            offset_x = 0
            offset_y = 0

            if size.width() < 300:
                offset_x = size.width() / 2

            if size.height() < 300:
                offset_y = size.height() / 2

            self.setWindowFlags(Qt.Window)
            label = QLabel(self)
            label.setPixmap(image)
            label.show()

        else:
            painter.setPen(Qt.black)
            # すでに確定されているパスの描画
            if len(self.existing_paths) > 0:
                for path in self.existing_paths:
                    painter.drawPath(path)

            if self.current_operation_mode == OperationMode.DRAWING_POINTS:
                # 　現在描いているパスの描画
                if len(self.clicked_points) > 3:
                    # print(self.clickedPoints)
                    # クリックした点まで線を伸ばすため、終点を一時的にリストに入れている
                    self.clicked_points.append(self.clicked_points[len(self.clicked_points) - 1])
                    painter_path = self.rounded_polygon.get_path(self.clicked_points)

                    for i in range(len(self.clicked_points)):
                        painter.drawEllipse(self.clicked_points[i], 1, 1)

                    if self.is_line_prediction:
                        self.clicked_points.pop()
                        self.is_line_prediction = False
                    painter.drawPath(painter_path)
                    self.clicked_points.pop()

                else:
                    if self.is_line_prediction:
                        painter.setPen(Qt.red)
                        for i in range(len(self.clicked_points)):
                            painter.drawEllipse(self.clicked_points[i], 1, 1)
                        self.clicked_points.pop()
                        self.is_line_prediction = False

                    else:
                        for i in range(len(self.clicked_points)):
                            painter.drawEllipse(self.clicked_points[i], 1, 1)

            elif self.current_operation_mode == OperationMode.MOVING_POINTS:
                # すでに確定されているパスの制御点の描画
                self.nearest_distance = 50.0
                for path in self.existing_paths:
                    for i in range(path.elementCount()):
                        control_point = QPointF(path.elementAt(i).x, path.elementAt(i).y)
                        painter.drawEllipse(control_point, 3, 3)

                        # 現在のカーソル位置から最も近い点と、その点が属するpathを記録、更新
                        if not self.is_dragging:
                            distance = math.sqrt((control_point.x() - self.cursor_position.x()) ** 2 + (
                                        control_point.y() - self.cursor_position.y()) ** 2)
                            if distance < self.nearest_distance:
                                self.nearest_distance = distance
                                self.nearest_path = path
                                self.nearest_index = i

                # 最も近い点を赤く描画
                if self.nearest_distance < 30:
                    painter.setPen(Qt.red)
                    nearest_control_point = QPointF(self.nearest_path.elementAt(self.nearest_index).x,
                                                    self.nearest_path.elementAt(self.nearest_index).y)
                    print(nearest_control_point)
                    painter.drawEllipse(nearest_control_point, 3, 3)

    def move_point(self):
        if self.is_enable_knee_control:
            # 選択した制御点の移動量 = カーソルクリック位置 +
            amount_of_change = QPointF(self.cursor_position_mousePressed.x() +
                                       (self.knee_position.x() - self.knee_position_mousePressed.x()),
                                       self.cursor_position_mousePressed.y() -
                                       (self.knee_position.y() - self.knee_position_mousePressed.y()))
            self.nearest_path.setElementPositionAt(self.nearest_index, amount_of_change.x(), amount_of_change.y())
        else:
            self.nearest_path.setElementPositionAt(self.nearest_index, self.cursor_position.x(),
                                                   self.cursor_position.y())

    def set_knee_position(self, x, y):
        self.knee_position.setX(x)
        self.knee_position.setY(y)

        if self.is_dragging:
            if self.current_operation_mode == OperationMode.MOVING_POINTS:
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
            self.existing_paths.append(painter_path)
            self.clicked_points = []
            self.update()

    def delete_last_path(self):
        if len(self.existing_paths) > 0:
            self.existing_paths.pop()
            self.update()

    def operation_mode_changed(self, to: OperationMode):
        self.current_operation_mode = to
        self.fix_path()

    def set_picture_file_name(self, picture_file_name: str):
        self.is_picture_canvas = True
        self.picture_file_name = picture_file_name
        self.update()

    def set_enable_knee_control(self, is_enable_knee_control):
        self.is_enable_knee_control = is_enable_knee_control


class TimerThread(QThread):
    updateSignal = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.kneePosition = KneePosition()  # 膝の座標を取得するためのクラス
        print("Success Establish Connection.")

        self.kneePosition.calibrate_knee_position()

    def run(self):
        while True:
            x, y = self.kneePosition.get_position()
            # x: 2  <-> 6
            # y: 46 <-> 48 <-> 53
            self.updateSignal.emit(x, y)
            self.msleep(10)

        # スレッドが終了してから
        # TODO: スレッド停止後の処理


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi()
        self.show()

        self.active_canvas = 0  # 操作レイヤの制御
        self.is_enabled_knee_control = False
        self.is_mode_switched = False
        self.pen_color = QColorDialog()
        self.current_color_saturation = 127
        self.current_operation_mode = OperationMode.DRAWING_POINTS
        # self.timerThread = QThread()

        try:
            self.timer_thread = TimerThread()
            self.timer_thread.updateSignal.connect(self.control_params_with_knee)
            self.timer_thread.start()
            self.kneePosition = self.timer_thread.kneePosition
            self.is_enabled_knee_control = True

        except serial.serialutil.SerialException as e:
            self.statusbar.showMessage("膝操作が無効：シリアル通信が確保できていません。原因：" + str(e))

        self.canvas[0].set_enable_knee_control(self.is_enabled_knee_control)

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
        self.canvasTableView.clicked.connect(self.switch_canvas)

        self.addCanvasButton = QPushButton(self.centralwidget)
        self.addCanvasButton.setGeometry(QRect(760, 330, 120, 25))
        self.addCanvasButton.setObjectName("addCanvasButton")
        self.addCanvasButton.clicked.connect(self.add_canvas)

        self.deleteCanvasButton = QPushButton(self.centralwidget)
        self.deleteCanvasButton.setGeometry(QRect(760, 360, 120, 25))
        self.deleteCanvasButton.setObjectName("deleteCanvasButton")
        self.deleteCanvasButton.clicked.connect(self.delete_canvas)

        self.addCanvasNameTextEdit = QTextEdit(self.centralwidget)
        self.addCanvasNameTextEdit.setGeometry(QRect(610, 345, 140, 25))
        self.addCanvasNameTextEdit.setObjectName("addCanvasNameTextEdit")

        self.savePictureButton = QPushButton(self.centralwidget)
        self.savePictureButton.setGeometry(QRect(740, 80, 140, 35))
        self.savePictureButton.setObjectName("savePictureButton")
        self.savePictureButton.clicked.connect(self.save_picture)

        self.colorPickerToolButton = QToolButton(self.centralwidget)
        self.colorPickerToolButton.setGeometry(QRect(810, 530, 71, 22))
        self.colorPickerToolButton.setObjectName("colorPickerToolButton")
        self.colorPickerToolButton.clicked.connect(self.pick_color)

        self.selectOperationModeButton = QPushButton(self.centralwidget)
        self.selectOperationModeButton.setGeometry(QRect(610, 80, 71, 31))
        self.selectOperationModeButton.setObjectName("selectOperationModeButton")
        self.selectOperationModeButton.clicked.connect(self.switch_knee_operation_mode)

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
        # self.fileReadButton.setText(_translate("MainWindow", "ファイルを読込む"))
        self.selectOperationModeButton.setText(_translate("MainWindow", "Mode:1"))
        QMetaObject.connectSlotsByName(self)

    def add_canvas(self):
        new_canvas = Canvas(self.centralwidget)
        new_canvas.setGeometry(QRect(0, 0, 600, 600))
        new_canvas.setObjectName("canvas")
        palette = new_canvas.palette()
        palette.setColor(QPalette.Background, QColor(255, 255, 255, 0))
        new_canvas.setPalette(palette)
        new_canvas.setAutoFillBackground(True)
        new_canvas.operation_mode_changed(self.current_operation_mode)
        new_canvas.is_enable_knee_control(self.is_enabled_knee_control)

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

    def switch_canvas(self, index_clicked: QModelIndex):
        self.active_canvas = index_clicked.row()

        self.canvasTableView.setCurrentIndex(self.canvasNameTableModel.index(self.active_canvas, 0))
        # 使用するレイヤだけ使用可能にする
        for canvas in self.canvas:
            canvas.setEnabled(False)
        self.canvas[self.active_canvas].setEnabled(True)
        self.canvas[self.active_canvas].operation_mode_changed(self.current_operation_mode)

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
        file_name, _ = QFileDialog.getOpenFileNames(self, "open file", "~/sampleImages",
                                                    "Images (*.jpg *.jpeg *.png *.bmp)")
        file_name = str(file_name)
        print(file_name)

        if file_name:
            self.canvas[self.active_canvas].set_picture_file_name(file_name)
        else:
            self.statusbar.showMessage("画像の読み込みに失敗しました")

    def pick_color(self):
        picked_color = self.pen_color.getColor(Qt.black)
        # print(pickedColor.hsvSaturation())
        # self.currentColorSaturation = pickedColor.hsvSaturation()
        self.statusbar.showMessage(str(picked_color))

    # TODO: モードと操作の接続
    def switch_knee_operation_mode(self):
        # TODO: NONEは消す（多分）
        if self.current_operation_mode == OperationMode.NONE:
            self.current_operation_mode = OperationMode.DRAWING_POINTS

        elif self.current_operation_mode == OperationMode.DRAWING_POINTS:
            self.current_operation_mode = OperationMode.MOVING_POINTS

        elif self.current_operation_mode == OperationMode.MOVING_POINTS:
            self.current_operation_mode = OperationMode.COLOR_PICKER

        elif self.current_operation_mode == OperationMode.COLOR_PICKER:
            self.current_operation_mode = OperationMode.DRAWING_POINTS

        else:
            self.current_operation_mode = OperationMode.NONE

        self.selectOperationModeButton.setText("Mode:{}".format(self.current_operation_mode.value))
        self.statusbar.showMessage("Mode:{}".format(self.current_operation_mode.value))
        self.canvas[self.active_canvas].operation_mode_changed(self.current_operation_mode)

    def keyPressEvent(self, keyEvent):
        # print(keyEvent.key())
        if keyEvent.key() == Qt.Key_Return:
            self.canvas[self.active_canvas].fix_path()

        if keyEvent.key() == Qt.Key_Backspace:
            self.canvas[self.active_canvas].delete_last_path()

    def control_params_with_knee(self, x, y):
        if y == 0:
            if not self.is_mode_switched:
                self.statusbar.showMessage("switch")
                self.switch_knee_operation_mode()
                self.is_mode_switched = True
        else:
            if self.current_operation_mode == OperationMode.NONE:
                pass

            elif self.current_operation_mode == OperationMode.DRAWING_POINTS:
                pass

            elif self.current_operation_mode == OperationMode.MOVING_POINTS:
                x, y = self.kneePosition.get_mapped_positions(x, y, 0, 200)
                self.canvas[self.active_canvas].set_knee_position(x, y)

            elif self.current_operation_mode == OperationMode.COLOR_PICKER:
                x, _ = self.kneePosition.get_mapped_positions(x, y, 1, 360)
                _, y = self.kneePosition.get_mapped_positions(x, y, 0, 255)
                next_color = QColor()
                next_color.setHsv(x, 255, y, 255)
                self.pen_color.setCurrentColor(next_color)

            else:
                self.current_operation_mode = OperationMode.NONE

            if self.is_mode_switched:
                self.is_mode_switched = False

            status_str = "x: " + str(x) + "y: " + str(y)
            self.statusbar.showMessage(status_str)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())
