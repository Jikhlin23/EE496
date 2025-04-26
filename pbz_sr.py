import numpy as np
import time
import statistics
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import pyqtgraph.exporters
import sys
import csv
import os
from datetime import datetime

class Plotter:
    def __init__(self, pbz, sr, start_Current, End_current, number_of_points, number_of_repeats,
                 sampling_points, time_of_sleep, trace_mode, note_string):

        self.pbz = pbz
        self.sr = sr
        self.start_Current = start_Current
        self.End_current = End_current
        self.number_of_points = number_of_points
        self.number_of_repeats = number_of_repeats
        self.sampling_points = sampling_points
        self.time_of_sleep = time_of_sleep
        self.trace_mode = trace_mode
        self.note_string = note_string

        self.original_currents = np.linspace(start_Current, End_current, number_of_points)
        self.currents = list(self.original_currents)

        self.running = False
        self.index = 0
        self.reverse = False
        self.current_repeat = 0
        self.all_data = []

        self.current_values, self.x_means, self.x_stds, self.y_means, self.y_stds = [], [], [], [], []

        self.app = QtWidgets.QApplication(sys.argv)
        self.setup_ui()
        self.win.show()
        sys.exit(self.app.exec_())

    def setup_ui(self):
        self.win = QtWidgets.QMainWindow()
        self.win.setWindowTitle("Live Measurement Plot")
        central_widget = QtWidgets.QWidget()
        self.win.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        top_info_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(top_info_layout)

        self.info_label = QtWidgets.QLabel(f"Repeat: {self.current_repeat}/{self.number_of_repeats}")
        self.info_label.setStyleSheet("font-weight: bold; font-size: 16px; color: blue;")
        top_info_layout.addWidget(self.info_label)

        top_info_layout.addStretch()

        self.toggle_status_label = QtWidgets.QLabel(f"Toggle is {self.trace_mode}")
        self.toggle_status_label.setStyleSheet("font-weight: bold; font-size: 16px; color: darkred;")
        top_info_layout.addWidget(self.toggle_status_label)

        self.graphics_layout = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics_layout)

        self.plot_x = self.graphics_layout.addPlot(title="X vs Current")
        self.plot_x.showGrid(x=True, y=True)
        self.x_curve = self.plot_x.plot(pen='b', symbol='o')
        self.x_error = pg.ErrorBarItem(pen=pg.mkPen('b'))
        self.plot_x.addItem(self.x_error)
        self.x_vline = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
        self.plot_x.addItem(self.x_vline)

        self.plot_y = self.graphics_layout.addPlot(title="Y vs Current")
        self.plot_y.showGrid(x=True, y=True)
        self.y_curve = self.plot_y.plot(pen='r', symbol='o')
        self.y_error = pg.ErrorBarItem(pen=pg.mkPen('r'))
        self.plot_y.addItem(self.y_error)
        self.y_vline = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
        self.plot_y.addItem(self.y_vline)

        controls = QtWidgets.QHBoxLayout()
        layout.addLayout(controls)

        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.save_btn = QtWidgets.QPushButton("Save")
        self.load_btn = QtWidgets.QPushButton("Load Data")
        self.alert_label = QtWidgets.QLabel("")
        self.alert_label.setStyleSheet("color: green;")

        for w in [self.start_btn, self.stop_btn, self.save_btn, self.load_btn, self.alert_label]:
            controls.addWidget(w)

        self.save_btn.hide()

        self.stats_label = QtWidgets.QLabel("Stats: ")
        self.stats_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.stats_label)

        self.start_btn.clicked.connect(self.start_measurement)
        self.stop_btn.clicked.connect(self.stop_measurement)
        self.save_btn.clicked.connect(lambda: self.save(auto=False))
        self.load_btn.clicked.connect(self.load_data)
        self.win.keyPressEvent = lambda e: self.app.quit() if e.key() == QtCore.Qt.Key_Escape else None

    def mean_and_std(self, data):
        return statistics.mean(data), statistics.stdev(data)

    def update_plot(self):
        x_np = np.array(self.current_values)
        x_mean_np = np.array(self.x_means)
        x_std_np = np.array(self.x_stds)
        y_mean_np = np.array(self.y_means)
        y_std_np = np.array(self.y_stds)

        self.x_curve.setData(x_np, x_mean_np)
        self.x_error.setData(x=x_np, y=x_mean_np, top=x_std_np, bottom=x_std_np)
        self.y_curve.setData(x_np, y_mean_np)
        self.y_error.setData(x=x_np, y=y_mean_np, top=y_std_np, bottom=y_std_np)

    def measure_next_point(self):
        if not self.running:
            return

        if self.index >= len(self.currents):
            self.current_repeat += 1
            if self.current_repeat >= self.number_of_repeats:
                self.running = False
                self.save(auto=True)
                self.app.quit()
                return

            if self.trace_mode:
                self.reverse = not self.reverse
                self.currents = list(reversed(self.currents))
            else:
                self.currents = list(self.original_currents)

            self.index = 0
            self.current_values.clear()
            self.x_means.clear()
            self.x_stds.clear()
            self.y_means.clear()
            self.y_stds.clear()
            self.info_label.setText(f"Repeat: {self.current_repeat}/{self.number_of_repeats}")
            self.update_plot()
            QtCore.QTimer.singleShot(100, self.measure_next_point)
            return

        current = self.currents[self.index]

        self.pbz.set_current(current)
        x_data, y_data = [], []
        for _ in range(self.sampling_points):
            time.sleep(self.time_of_sleep)
            x, y = self.sr.snap('x', 'y')
            x_data.append(x)
            y_data.append(y)

        x_mean, x_std = self.mean_and_std(x_data)
        y_mean, y_std = self.mean_and_std(y_data)

        self.current_values.append(current)
        self.x_means.append(x_mean)
        self.x_stds.append(x_std)
        self.y_means.append(y_mean)
        self.y_stds.append(y_std)

        self.all_data.append((self.current_repeat + 1, current, x_mean, x_std, y_mean, y_std))

        self.update_plot()
        self.stats_label.setText(
            f"Current: {current:.4e} | X: {x_mean:.4e}±{x_std:.1e} | Y: {y_mean:.4e}±{y_std:.1e}"
        )

        self.index += 1
        QtCore.QTimer.singleShot(10, self.measure_next_point)

    def start_measurement(self):
        self.running = True
        self.save_btn.hide()
        self.index = 0
        self.current_repeat = 0
        self.currents[:] = list(self.original_currents)
        self.current_values.clear()
        self.x_means.clear()
        self.x_stds.clear()
        self.y_means.clear()
        self.y_stds.clear()
        self.all_data.clear()
        self.info_label.setText(f"Repeat: {self.current_repeat}/{self.number_of_repeats}")
        self.update_plot()
        self.measure_next_point()

    def stop_measurement(self):
        self.running = not self.running
        self.save_btn.show()

        if not self.running and self.x_means and self.y_means:
            stats = (
                f"Final Stats → X_mean: {statistics.mean(self.x_means):.4e}, "
                f"Y_mean: {statistics.mean(self.y_means):.4e}, "
                f"X_max: {max(self.x_means):.4e}, Y_max: {max(self.y_means):.4e}"
            )
            print(stats)
            self.alert_label.setText(stats)

        self.stop_btn.setText("Resume" if not self.running else "Stop")
        if self.running:
            self.measure_next_point()

    def save(self, auto=False):
        filename_base = f"measurement_{datetime.now().strftime('%Y%m%d')}"
        csv_file = f"{filename_base}.csv"
        txt_file = f"{filename_base}.txt"

        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Repeat", "Current", "X", "X_std", "Y", "Y_std"])
            for entry in self.all_data:
                writer.writerow(entry)

        with open(txt_file, "w") as f:
            f.write(f"# {self.note_string}\n")
            f.write("Repeat\tCurrent\tX\tX_std\tY\tY_std\n")
            for entry in self.all_data:
                f.write(f"{entry[0]}\t{entry[1]:.6e}\t{entry[2]:.6e}\t{entry[3]:.6e}\t{entry[4]:.6e}\t{entry[5]:.6e}\n")

        image_dir = "plots"
        os.makedirs(image_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        pg.exporters.ImageExporter(self.plot_x).export(os.path.join(image_dir, f"plot_x_{timestamp}.png"))
        pg.exporters.ImageExporter(self.plot_y).export(os.path.join(image_dir, f"plot_y_{timestamp}.png"))
        if not auto:
            self.alert_label.setText("✅ Data & Plots Saved!")

    def load_data(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Open Measurement File", "", "*.txt *.csv")
        if filename:
            self.current_values.clear()
            self.x_means.clear()
            self.x_stds.clear()
            self.y_means.clear()
            self.y_stds.clear()
            with open(filename, 'r') as f:
                lines = f.readlines()[1:]
                for line in lines:
                    parts = line.strip().replace(',', ' ').split()
                    if len(parts) >= 6:
                        self.current_values.append(float(parts[1]))
                        self.x_means.append(float(parts[2]))
                        self.x_stds.append(float(parts[3]))
                        self.y_means.append(float(parts[4]))
                        self.y_stds.append(float(parts[5]))
            self.update_plot()
            self.alert_label.setText("✅ Data Loaded")
