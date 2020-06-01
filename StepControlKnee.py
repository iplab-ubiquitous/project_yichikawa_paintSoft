import os
import sys, serial, random, time
import numpy as np

from PyQt5.QtCore import QRect, Qt, QPointF
from PyQt5.QtGui import QPaintEvent, QPainter, QKeyEvent, QKeySequence
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QMenuBar, QStatusBar, QAction

import KneePosition

steps = 5
participant_No = 0


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi()
        self.show()
        self.current_knee_step = 0
        self.target_step = 5
        self.current_order = 0
        self.is_horizontal = False
        self.is_current_step_visible = True
        self.setup_experiment()
        self.calibration_position = QPointF(0, 0)

        try:
            self.timer_thread = KneePosition.TimerThread()
            self.timer_thread.updateSignal.connect(self.control_params_with_knee)
            self.timer_thread.start()
            self.kneePosition = self.timer_thread.kneePosition
            self.calibration_position = QPointF(self.kneePosition.knee_pos_x_center, self.kneePosition.knee_pos_y_center)

        except serial.serialutil.SerialException as e:
            self.statusbar.showMessage("膝操作が無効：シリアル通信が確保できていません。原因：" + str(e))

        self.rectangles = []
        self.rect_orders = random.sample(range(steps), steps)
        self.setup_rect(steps)

    def setupUi(self):
        self.setObjectName("self")
        self.resize(1280, 720)
        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.setCentralWidget(self.centralwidget)

        self.menubar = QMenuBar(self)
        self.menubar.setGeometry(QRect(0, 0, 889, 22))
        self.menubar.setObjectName("menubar")

        self.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        start_experiment_action = QAction("計測開始", self)
        start_experiment_action.setShortcut(QKeySequence("Ctrl+E"))
        start_experiment_action.triggered.connect(self.start_experiment)

        save_records_action = QAction("計測結果を保存", self)
        save_records_action.setShortcut(QKeySequence("Ctrl+S"))
        save_records_action.triggered.connect(self.save_records)

        switch_current_step_visible_action = QAction("現在のステップを表示/非表示切り替え", self)
        switch_current_step_visible_action.setShortcut(QKeySequence("Ctrl+V"))
        switch_current_step_visible_action.triggered.connect(self.switch_current_step_visible)

        operation_menus = self.menubar.addMenu("experiments")
        operation_menus.addAction(start_experiment_action)
        operation_menus.addAction(save_records_action)

    # def switch_vertical_and_horizontal(self):
    #     self.is_horizontal = not self.is_horizontal
    #     self.setup_rect(steps)
    #     self.centralwidget.update()
    #     self.update()

    def setup_rect(self, num_of_rects: int):
        if self.is_horizontal:
            rect_width = 1080 / num_of_rects
            for i in range(num_of_rects):
                self.rectangles.append(QRect(100 + rect_width * i, 260, rect_width, 100))
        else:
            rect_height = 620 / num_of_rects
            for i in range(num_of_rects):
                self.rectangles.append(QRect(540, 50 + rect_height * i, 100, rect_height))

    def setup_experiment(self):
        # 取得する指標
        self.operation_times      = np.empty(steps, dtype=float)
        self.offsets              = np.empty(steps, dtype=int)
        self.current_position     = QPointF(0, 0)

        # タイマー
        self.start_time    = 0
        self.previous_operated_time = 0

        self.is_started_experiment = False

        self.frame_records     = np.empty((0, 3), float) # 操作ごとの記録
        self.operation_records = np.empty((0, 5), float) # フレーム（膝位置が更新される）ごとの記録

    def start_experiment(self):
        self.start_time            = time.time()
        self.is_started_experiment = True

        self.statusbar.showMessage("Experiment started p{}, {}, steps_{}, step_{}"
                                       .format(participant_No,
                                        ("horizontal" if self.is_horizontal
                                        else "vertical"),
                                        steps,
                                        ("visible" if self.is_current_step_visible
                                        else "invisible")
                                        )
                                   )

    def record_frame(self):
        if self.is_started_experiment:
            current_time   = time.time()  - self.start_time
            self.frame_records = np.append(self.frame_records, np.array(
                                                [[self.current_position.x(),
                                                 self.current_position.y(),
                                                 current_time]]
                                          ), axis=0)
            print(current_time)

    def record_operation(self):
        current_time = time.time() - self.start_time

        operation_times = current_time - self.previous_operated_time
        offsets         = self.current_knee_step - self.rect_orders[self.current_order]

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
            print(self.frame_records)
            file_path = "result_preliminary/p{}/{}/steps_{}/step_{}".format(participant_No,
                                                                     ("horizontal" if self.is_horizontal
                                                                                      else "vertical"),
                                                                     steps,
                                                                     ("visible" if self.is_current_step_visible
                                                                                      else "invisible")
                                                                    )
            try:
                os.makedirs(file_path)
            except FileExistsError:
                pass

            np.savetxt(file_path + "test_frameRecords.csv", self.frame_records, delimiter=',',
                       fmt=['%.5f', '%.5f', '%.5f'],
                       header='knee_pos_x, knee_pos_y, time',
                       comments=' ')
            np.savetxt(file_path + "test_operationRecords.csv", self.operation_records, delimiter=',',
                       fmt=['%.5f', '%.5f', '%.5f', '%.0f', '%.0f'],
                       header="knee_pos_x, knee_pos_y, time, selected_No, target_No, calibration x:{} y:{}"
                                .format(self.kneePosition.knee_pos_x_center, self.kneePosition.knee_pos_y_center),
                       comments=' ')
            self.statusbar.showMessage("Saved.")

    def switch_current_step_visible(self):
        if not self.is_started_experiment:
            self.is_current_step_visible = not self.is_current_step_visible

    def control_params_with_knee(self, x, y):
        self.current_position.setX(x)
        self.current_position.setY(y)
        self.record_frame()
        x, y = self.kneePosition.get_mapped_positions(x, y, 1, 359)
        if self.is_horizontal:
            self.current_knee_step = (int)(x / (360 / steps))
        else:
            self.current_knee_step = steps - (int)(y / (360 / steps)) - 1

        # status_str = "x: " + str(x) + "y: " + str(y)
        # self.statusbar.showMessage(status_str)
        self.update()

    def keyPressEvent(self, keyevent: QKeyEvent):
        if keyevent.key() == Qt.Key_Return:
            if self.is_started_experiment:
                self.record_operation()
                self.current_order = self.current_order + 1

                if self.current_order >= steps:
                    self.statusbar.showMessage("End. Save data with Cmd+S.")
                    self.is_started_experiment = False
                    self.current_order = 0


        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)

        for rect in self.rectangles:
            painter.drawRect(rect)

        # ターゲットの段階
        painter.setBrush(Qt.green)
        painter.drawRect(self.rectangles[self.rect_orders[self.current_order % steps]])

        # 現在の段階
        if self.is_current_step_visible:
            painter.setBrush(Qt.blue)
            painter.drawRect(self.rectangles[self.current_knee_step])


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())
