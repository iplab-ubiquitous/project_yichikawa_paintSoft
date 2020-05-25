import sys, serial, random

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QPaintEvent, QPainter, QKeyEvent, QKeySequence
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QMenuBar, QStatusBar, QAction

import KneePosition

steps = 20

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi()
        self.show()
        self.current_knee_step = 0
        self.target_step = 5
        self.current_order = 0

        try:
            self.timer_thread = KneePosition.TimerThread()
            self.timer_thread.updateSignal.connect(self.control_params_with_knee)
            self.timer_thread.start()
            self.kneePosition = self.timer_thread.kneePosition

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

        switch_action = QAction("横縦切り替え", self)
        switch_action.setShortcut(QKeySequence("Ctrl+M"))
        switch_action.triggered.connect(self.switch_vertical_and_horizontal)

        operation_menus = self.menubar.addMenu("experiments")
        operation_menus.addAction(switch_action)

    def switch_vertical_and_horizontal(self):
        print("a")

    def setup_rect(self, num_of_rects: int):
        rect_width = 1080 / num_of_rects
        for i in range(num_of_rects):
            self.rectangles.append(QRect(100 + rect_width * i, 260, rect_width, 100))

    def control_params_with_knee(self, x, y):
        x, _ = self.kneePosition.get_mapped_positions(x, y, 1, 359)
        self.current_knee_step = (int)(x / (360 / steps))

        status_str = "x: " + str(x) + "y: " + str(y)
        self.statusbar.showMessage(status_str)
        self.update()

    def keyPressEvent(self, keyevent: QKeyEvent):
        if keyevent.key() == Qt.Key_Return:
            self.current_order = (self.current_order+1) % steps
            self.update()
        if keyevent.key() == Qt.Key_Shift:
            pass

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)

        for rect in self.rectangles:
            painter.drawRect(rect)

        # ターゲットの段階
        painter.setBrush(Qt.green)
        painter.drawRect(self.rectangles[self.rect_orders[self.current_order]])

        # 現在の段階
        painter.setBrush(Qt.blue)
        painter.drawRect(self.rectangles[self.current_knee_step])


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())
