import sys, serial

from PyQt5.QtCore import QRect
from PyQt5.QtGui import QPaintEvent, QPainter
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QMenuBar, QStatusBar

import KneePosition

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi()
        self.show()

        try:
            self.timer_thread = KneePosition.TimerThread()
            self.timer_thread.updateSignal.connect(self.control_params_with_knee)
            self.timer_thread.start()
            self.kneePosition = self.timer_thread.kneePosition

        except serial.serialutil.SerialException as e:
            self.statusbar.showMessage("膝操作が無効：シリアル通信が確保できていません。原因：" + str(e))

        self.rectangles = []
        self.setup_rect(15)

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

    def setup_rect(self, num_of_rects: int):
        rect_width = 1000 / num_of_rects
        for i in range(num_of_rects):
            self.rectangles.append(QRect(140 + rect_width * i, 260, rect_width, 100))

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)

        for rect in self.rectangles:
            painter.drawRect(rect)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())
