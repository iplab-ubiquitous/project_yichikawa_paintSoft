import serial
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

NUM_OF_SENSORS = 10
WAITING_FRAMES = 100
ALPHA_EMA = 0.7

class KneePosition():

    def __init__(self):
        self.distance_sensor_array_communication = serial.Serial('/dev/cu.usbmodem142301', 460800)
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