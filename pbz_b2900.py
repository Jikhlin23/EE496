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
from pbz60 import PBZController
from b2900 import B2900Controller

class MeasurementApp:
    def __init__(self, pbz_resource, b2900_resource, 
                 pbz_start_current, pbz_end_current,
                 steps_per_sweep, number_of_loops,
                 sampling_points, time_of_sleep,
                 keysight_current_values,  # Constant keysight_current_values passed here
                 note_string="", expt_name= ""):
        
        # Configuration parameters
        self.pbz_start_current = pbz_start_current
        self.pbz_end_current = pbz_end_current
        self.steps_per_sweep = steps_per_sweep
        self.number_of_loops = number_of_loops
        self.sampling_points = sampling_points
        self.time_of_sleep = time_of_sleep
        self.note_string = note_string
        self.expt_name = expt_name
        # Constant keysight currents passed to the class
        self.keysight_current_values = keysight_current_values
        
        # Initialize state variables
        self.all_data = []
        self.current_loop_data = []  # Data for the current loop only
        self.current_loop = 0
        self.pbz_currents = np.linspace(pbz_start_current, pbz_end_current, steps_per_sweep)
        self.running = False
        self.index = 0
        self.forward = True  # Direction flag
        
        # Initialize data storage
        self.current_values = []  # PBZ currents
        self.voltage_values = []  # Voltage readings

        # Connect to instruments
        self.connect_instruments(pbz_resource, b2900_resource)
        self.voltage_source = "b2900"  # Fixed to B2900
        # Initialize UI
        self.setup_ui()
        
    def measure_voltage(self):
        """Measure voltage output of the B2900"""
        try:
            voltage = float(self.instr.query("MEAS:VOLT?").strip())
            return voltage
        except Exception as e:
            print(f"Error measuring B2900 voltage: {e}")
            return float('nan')

    def connect_instruments(self, pbz_resource, b2900_resource):
        """Connect to the PBZ60 and B2900 instruments"""
        try:
            self.pbz = PBZController(resource=pbz_resource)
            print(f"PBZ connected: {self.pbz.identify()}")
            
            self.b2900 = B2900Controller(address=b2900_resource)
            print(f"B2900 connected: {self.b2900.get_id()}")
            
            # Initial instrument setup
            self.pbz.reset()
            self.b2900.reset()
            time.sleep(1)
            
            # Set up PBZ
            self.pbz.set_mode("CC")  # Constant Current mode
            self.pbz.set_current(0)  # Start at 0 current
            self.pbz.enable_output()
            
            # Set up B2900 for measurements
            self.b2900.set_source_mode("CURR")  # Set to current source mode
            self.b2900.apply_current(0)  # Start at 0 current
            self.b2900.set_voltage_compliance(10)  # Set voltage compliance
            self.b2900.set_output(True)
            
        except Exception as e:
            print(f"Error connecting to instruments: {e}")
            sys.exit(1)
    
    def setup_ui(self):
        """Set up the UI components"""
        self.app = QtWidgets.QApplication.instance()
        if not self.app:
            self.app = QtWidgets.QApplication(sys.argv)
            
        self.win = QtWidgets.QMainWindow()
        self.win.setWindowTitle("PBZ60 & B2900 Measurement")
        self.win.resize(1000, 700)
        
        central_widget = QtWidgets.QWidget()
        self.win.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Top info layout
        top_info_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(top_info_layout)

        self.info_label = QtWidgets.QLabel(f"Loop: {self.current_loop}/{self.number_of_loops} | Direction: {'Forward' if self.forward else 'Backward'}")
        self.info_label.setStyleSheet("font-weight: bold; font-size: 16px; color: blue;")
        top_info_layout.addWidget(self.info_label)

        top_info_layout.addStretch()

        # Setup plot for PBZ Current vs B2900 Voltage
        graphics_layout = pg.GraphicsLayoutWidget()
        layout.addWidget(graphics_layout)

        # Combined plot for PBZ current vs B2900 Voltage
        self.plot_combined = graphics_layout.addPlot(title="PBZ Current vs B2900 Voltage")
        self.plot_combined.showGrid(x=True, y=True)
        self.plot_combined.setLabel('left', "Voltage (V)")
        self.plot_combined.setLabel('bottom', "PBZ Current (A)")
        self.forward_curve = self.plot_combined.plot(pen='b', symbol='o', name="Forward")
        self.backward_curve = self.plot_combined.plot(pen='r', symbol='x', name="Backward")
        self.plot_combined.addLegend()

        # Controls
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

        # Stats label
        self.stats_label = QtWidgets.QLabel("Stats: ")
        self.stats_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.stats_label)

        # Connect buttons
        self.start_btn.clicked.connect(self.start_measurement)
        self.stop_btn.clicked.connect(self.stop_measurement)
        self.save_btn.clicked.connect(lambda: self.save(auto=False))
        self.load_btn.clicked.connect(self.load_data)

        # Escape key to exit
        self.win.keyPressEvent = lambda e: self.app.quit() if e.key() == QtCore.Qt.Key_Escape else None

    def mean_and_std(self, data):
        """Calculate mean and standard deviation of data"""
        return statistics.mean(data), statistics.stdev(data) if len(data) > 1 else 0

    def update_plot(self):
        """Update the plot with current data"""
        if not self.current_loop_data:
            return
            
        # Separate data by direction for the current loop
        forward_pbz = []
        forward_voltage = []
        backward_pbz = []
        backward_voltage = []
        
        for entry in self.current_loop_data:
            loop, direction, pbz_curr, key_curr = entry[0:4]
            voltage = entry[4]  # b2900_voltage_mean
                
            if direction == "Forward":
                forward_pbz.append(pbz_curr)
                forward_voltage.append(voltage)
            else:
                backward_pbz.append(pbz_curr)
                backward_voltage.append(voltage)
            
        # Update the combined plot (PBZ current vs B2900 voltage)
        self.forward_curve.setData(forward_pbz, forward_voltage)
        self.backward_curve.setData(backward_pbz, backward_voltage)

    def measure_next_point(self):
        """Measure the next data point"""
        if not self.running:
            return

        # Check if we've reached the end of a sweep
        if self.index >= len(self.pbz_currents):
            # Toggle direction
            self.forward = not self.forward
            self.index = 0
            
            # If we've completed a full loop (forward and backward)
            if not self.forward:
                self.info_label.setText(f"Loop: {self.current_loop}/{self.number_of_loops} | Direction: Backward")
            else:
                # Save the current loop's plot before clearing
                self.save_current_loop_plot()
                
                # Increment loop counter if we've completed a forward and backward sweep
                self.current_loop += 1
                
                if self.current_loop > self.number_of_loops:
                    # We've finished all loops, save and stop
                    self.running = False
                    self.save(auto=True)
                    self.alert_label.setText(f"✅ Measurement completed! All {self.number_of_loops} loops saved.")
                    self.stop_btn.setText("Stop")
                    self.save_btn.show()
                    return
                
                # Clear plots for the new loop
                self.clear_plots()
                self.info_label.setText(f"Loop: {self.current_loop}/{self.number_of_loops} | Direction: Forward")
            
            self.update_plot()
            QtCore.QTimer.singleShot(100, self.measure_next_point)
            return

        # Get current values based on index and direction
        if self.forward:
            pbz_current = self.pbz_currents[self.index]
        else:
            # Reverse the array for backward sweep
            pbz_current = self.pbz_currents[-(self.index+1)]
        
        # Set the current on PBZ
        self.pbz.set_current(pbz_current)
        
        # Set the current on B2900 (Keysight)
        keysight_current = self.keysight_current_values[self.index % len(self.keysight_current_values)]
        self.b2900.apply_current(keysight_current)
        
        # Allow settling time
        time.sleep(0.5)
        
        # Take voltage measurements
        b2900_voltage_data = []
        for _ in range(self.sampling_points):
            time.sleep(self.time_of_sleep)
            
            # Measure voltage using B2900
            if self.voltage_source == "b2900":
                b2900_voltage = self.b2900.measure_voltage()
                b2900_voltage_data.append(b2900_voltage)

        # Calculate statistics
        if self.voltage_source == "b2900" and b2900_voltage_data:
            b2900_voltage_mean, b2900_voltage_std = self.mean_and_std(b2900_voltage_data)
        else:
            b2900_voltage_mean, b2900_voltage_std = None, None

        # Store data
        direction = "Forward" if self.forward else "Backward"
        data_entry = (
            self.current_loop, 
            direction, 
            pbz_current, 
            keysight_current, 
            b2900_voltage_mean,
            b2900_voltage_std
        )
        self.all_data.append(data_entry)
        self.current_loop_data.append(data_entry)

        self.update_plot()
        self.stats_label.setText(
            f"PBZ Current: {pbz_current:.4e} | Keysight Current: {keysight_current:.4e} | "
            f"B2900 Voltage: {b2900_voltage_mean:.4e}±{b2900_voltage_std:.1e} | Direction: {direction}"
        )

        self.index += 1
        QtCore.QTimer.singleShot(10, self.measure_next_point)

    def start_measurement(self):
        """Start the measurement sequence"""
        self.running = True
        self.save_btn.hide()
        self.index = 0
        self.current_loop = 1
        self.forward = True
        self.all_data.clear()
        self.current_loop_data.clear()
        self.clear_plots()
        self.info_label.setText(f"Loop: {self.current_loop}/{self.number_of_loops} | Direction: Forward")
        self.alert_label.setText("Measurement in progress...")
        self.stop_btn.setText("Stop")
        self.measure_next_point()

    def stop_measurement(self):
        """Stop or resume the measurement"""
        self.running = not self.running
        self.save_btn.setVisible(not self.running)

        if not self.running and self.all_data:
            stats = f"Paused: Loop {self.current_loop}/{self.number_of_loops}"
            self.alert_label.setText(stats)

        self.stop_btn.setText("Resume" if not self.running else "Stop")
        if self.running:
            self.measure_next_point()

    def save(self, auto=False):
        filename_base = f"{self.expt_name}_measurement_{datetime.now().strftime('%Y%m%d')}_{self.current_loop}"
        csv_file = f"{filename_base}.csv"
        txt_file = f"{filename_base}.txt"

        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Loop", "Direction", "PBZ_Current", "Keysight_Current", 
                "B2900_Voltage", "B2900_Voltage_std", 
            ])
            for entry in self.all_data:
                writer.writerow(entry)

        with open(txt_file, "w") as f:
            f.write(f"# {self.note_string}\n")
            f.write("Loop\tDirection\tPBZ_Current\tKeysight_Current\t"
                    "B2900_Voltage\tB2900_Voltage_std\t"
                    "PBZ_Voltage\tPBZ_Voltage_std\n")
            for entry in self.all_data:
                loop, direction = entry[0:2]
                pbz, key = entry[2:4]
                b2900_v, b2900_v_std = entry[4:6]
                pbz_v, pbz_v_std = entry[6:8]
                
                f.write(f"{loop}\t{direction}\t{pbz:.6e}\t{key:.6e}\t"
                        f"{b2900_v:.6e}\t{b2900_v_std:.6e}\t"
                        f"{pbz_v:.6e}\t{pbz_v_std:.6e}\n")

        # Save current plot if any data exists in current_loop_data
        if self.current_loop_data and not auto:
            self.save_current_loop_plot()
        
        if not auto:
            self.alert_label.setText("✅ Data & Plots Saved!")



    def clear(self):

        self.current_loop_data = []  # Reset the loop data

        # If there's any additional reset required for instruments, it can be added here.
        if self.pbz:
            self.pbz.reset()  # Example method to reset the PBZ instrument
        if self.b2900:
            self.b2900.reset()  # Example method to reset the B2900 instrument


    def load_data(self):
        """Load data from a CSV or TXT file"""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Open Measurement File", "", "*.txt *.csv")
        if filename:
            self.all_data.clear()
            
            with open(filename, 'r') as f:
                lines = f.readlines()
                start_line = 0
                
                # Skip header and comments
                for i, line in enumerate(lines):
                    if line.startswith("#") or "Loop" in line:
                        start_line = i + 1
                        continue
                
                for line in lines[start_line:]:
                    parts = line.strip().replace(',', '\t').split('\t')
                    if len(parts) >= 6:
                        loop = int(parts[0])
                        direction = parts[1]
                        pbz_current = float(parts[2])
                        keysight_current = float(parts[3])
                        voltage = float(parts[4])
                        voltage_std = float(parts[5])
                        
                        self.all_data.append((loop, direction, pbz_current, keysight_current, voltage, voltage_std))
                        
            # Get the latest loop number
            if self.all_data:
                self.current_loop = max(entry[0] for entry in self.all_data)
                # Filter data for current loop only
                self.current_loop_data = [entry for entry in self.all_data if entry[0] == self.current_loop]
                self.update_plot()
                self.alert_label.setText(f"✅ Data Loaded - Showing Loop {self.current_loop}")
            else:
                self.alert_label.setText("No valid data found in file")

    def cleanup(self):
        """Clean up resources before exiting"""
        try:
            print("Closing connections to instruments...")
            self.pbz.set_current(0)
            self.pbz.disable_output()
            self.pbz.close()
            
            self.b2900.apply_current(0)
            self.b2900.set_output(False)
            self.b2900.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def run(self):
        """Run the application"""
        self.win.show()
        result = self.app.exec_()
        self.cleanup()
        return result



